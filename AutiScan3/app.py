from flask import Flask, render_template, request, send_file, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from pymongo import MongoClient
from dotenv import load_dotenv
import pickle
import os, time
import base64
import pandas as pd
import numpy as np
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import google.generativeai as genai
import shap

from authlib.integrations.flask_client import OAuth
from bson.objectid import ObjectId
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
app.secret_key = os.environ.get("SECRET_KEY", "super_secret_dev_key_123")

# Load RAG Index
import json
RAG_INDEX = []
RAG_EMBEDDINGS = None
RAG_NORMALIZED_EMBEDDINGS = None

try:
    rag_path = os.path.join(os.path.dirname(__file__), "rag_index.json")
    if os.path.exists(rag_path):
        with open(rag_path, "r", encoding="utf-8") as f:
            RAG_INDEX = json.load(f)
        if RAG_INDEX:
            RAG_EMBEDDINGS = np.array([c["embedding"] for c in RAG_INDEX])
            norms = np.linalg.norm(RAG_EMBEDDINGS, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            RAG_NORMALIZED_EMBEDDINGS = RAG_EMBEDDINGS / norms
            print(f"RAG Index loaded successfully: {len(RAG_INDEX)} chunks.")
except Exception as e:
    print("Error loading RAG Index:", e)

# Configure OAuth
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# MongoDB Configuration
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client.get_database("autiscan_db")
    users_collection = db["users"]
    children_collection = db["children"]
    assessments_collection = db["assessments"]
    games_collection = db["games"]
    appointments_collection = db["appointments"]
    print("Connected to MongoDB successfully!")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")
    users_collection = None
    children_collection = None
    assessments_collection = None
    games_collection = None
    appointments_collection = None

# Context Processor for Templates
@app.context_processor
def inject_user():
    return dict(current_user=session.get('user_id'), current_user_name=session.get('name'), current_user_role=session.get('role'))

# Login Required Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login', next=request.url))
        
        # Check if user needs to complete their profile
        if not session.get('role') and request.endpoint != 'complete_profile':
            return redirect(url_for('complete_profile'))
            
        return f(*args, **kwargs)
    return decorated_function

# -------- AUTHENTICATION ROUTES --------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if users_collection is None:
            return "MongoDB setup is incomplete. Check backend connection.", 500
            
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")  # 'parent' or 'doctor'
        
        if users_collection.find_one({"email": email}):
            flash("Email already registered.", "error")
            return redirect(url_for("register"))
            
        user_data = {
            "name": name,
            "email": email,
            "password": generate_password_hash(password),
            "role": role,
            "created_at": time.time()
        }
        
        if role == "doctor":
            user_data["degree"] = request.form.get("degree")
            user_data["phone"] = request.form.get("phone")
            user_data["address"] = request.form.get("address")
            user_data["availability"] = ""  # Doctor adds this later
            
        res = users_collection.insert_one(user_data)
        
        session['user_id'] = str(res.inserted_id)
        session['name'] = name
        session['role'] = role
        
        return redirect(url_for("dashboard"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if users_collection is None:
            return "MongoDB setup is incomplete. Check backend connection.", 500
            
        email = request.form.get("email")
        password = request.form.get("password")
        
        user = users_collection.find_one({"email": email})
        if not user or not check_password_hash(user["password"], password):
            flash("Invalid email or password", "error")
            return redirect(url_for("login"))
            
        session['user_id'] = str(user["_id"])
        session['name'] = user["name"]
        session['role'] = user.get("role", "parent")
        
        next_page = request.args.get("next")
        return redirect(next_page or url_for("dashboard"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route('/login/google')
def login_google():
    if 'localhost' in request.host or '127.0.0.1' in request.host:
        redirect_uri = url_for('authorize_google', _external=True)
    else:
        # Enforce HTTPS and use the public proxy host header for cloud deployments (Hugging Face / Render)
        host = request.headers.get('X-Forwarded-Host') or request.host
        redirect_uri = f"https://{host}/authorize/google"
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize/google')
def authorize_google():
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    
    if not user_info:
        flash("Google login failed.", "error")
        return redirect(url_for("login"))
        
    email = user_info.get("email")
    name = user_info.get("name")
    
    user = users_collection.find_one({"email": email})
    
    if user:
        # Existing user
        session['user_id'] = str(user["_id"])
        session['name'] = user["name"]
        session['role'] = user.get("role", "")
    else:
        # New Google user, role not set yet
        user_data = {
            "name": name,
            "email": email,
            "password": generate_password_hash(os.urandom(24).hex()), # random placeholder
            "role": "", # Empty role forces complete profile
            "created_at": time.time(),
            "auth_provider": "google"
        }
        res = users_collection.insert_one(user_data)
        session['user_id'] = str(res.inserted_id)
        session['name'] = name
        session['role'] = ""
        
    # Redirect to dashboard (login_required will catch empty role)
    return redirect(url_for("dashboard"))

@app.route('/complete_profile', methods=['GET', 'POST'])
def complete_profile():
    if 'user_id' not in session:
        return redirect(url_for("login"))
        
    if session.get('role'):
        return redirect(url_for("dashboard"))
        
    if request.method == "POST":
        role = request.form.get("role")
        
        update_data = {"role": role}
        
        if role == "doctor":
            update_data["degree"] = request.form.get("degree")
            update_data["phone"] = request.form.get("phone")
            update_data["address"] = request.form.get("address")
            update_data["availability"] = ""
            
        users_collection.update_one(
            {"_id": ObjectId(session['user_id'])},
            {"$set": update_data}
        )
        
        session['role'] = role
        flash("Profile completed successfully!", "success")
        return redirect(url_for("dashboard"))
        
    return render_template("complete_profile.html")

# -------- DASHBOARD & CHILD TRACKING --------
import datetime

@app.route("/dashboard")
@login_required
def dashboard():
    role = session.get("role")
    user_id = session.get("user_id")
    
    if role == "parent":
        # Parent sees their children and doctors
        children = list(children_collection.find({"parent_id": user_id}))
        doctors = list(users_collection.find({"role": "doctor"}, {"password": 0}))
        
        # Fetch upcoming appointments
        appointments = list(appointments_collection.find({"parent_id": user_id, "status": "upcoming"}))
        for appt in appointments:
            doc = users_collection.find_one({"_id": ObjectId(appt.get("doctor_id"))})
            child = children_collection.find_one({"_id": ObjectId(appt.get("child_id"))})
            appt["doctor_name"] = doc["name"] if doc else "Unknown"
            appt["doctor_phone"] = doc.get("phone", "No phone") if doc else "No phone"
            appt["child_name"] = child["name"] if child else "Unknown"
            
        return render_template("dashboard_parent.html", children=children, doctors=doctors, appointments=appointments)
    elif role == "doctor":
        doctor_profile = users_collection.find_one({"_id": ObjectId(user_id)})
        
        # Fetch upcoming appointments
        appointments = list(appointments_collection.find({"doctor_id": user_id, "status": "upcoming"}))
        for appt in appointments:
            parent = users_collection.find_one({"_id": ObjectId(appt.get("parent_id"))})
            child = children_collection.find_one({"_id": ObjectId(appt.get("child_id"))})
            appt["parent_name"] = parent["name"] if parent else "Unknown"
            appt["parent_phone"] = parent.get("phone", "No phone") if parent else "No phone"
            appt["child_name"] = child["name"] if child else "Unknown"
            appt["child_id_str"] = str(child["_id"]) if child else ""
            
        # Doctors can see all children for now, or children assigned to them
        # We will show all children to allow easy lookup
        children = list(children_collection.find({}))
        # Fetching parent info for each child
        for child in children:
            parent = users_collection.find_one({"_id": ObjectId(child.get("parent_id"))})
            child["parent_name"] = parent["name"] if parent else "Unknown"
        return render_template("dashboard_doctor.html", children=children, doctor=doctor_profile, appointments=appointments)
    else:
        return redirect(url_for("home"))

@app.route("/add_child", methods=["POST"])
@login_required
def add_child():
    name = request.form.get("name")
    age = request.form.get("age")
    gender = request.form.get("gender")
    
    child_data = {
        "parent_id": session.get("user_id"),
        "name": name,
        "age": int(age) if age else 0,
        "gender": gender,
        "created_at": datetime.datetime.now()
    }
    
    # Handle Photo Upload
    photo = request.files.get("photo")
    if photo and photo.filename:
        photo_b64 = base64.b64encode(photo.read()).decode('utf-8')
        child_data["photo_base64"] = photo_b64
        
    children_collection.insert_one(child_data)
    flash("Child profile added successfully!", "success")
    return redirect(url_for("dashboard"))

@app.route("/edit_doctor_profile", methods=["POST"])
@login_required
def edit_doctor_profile():
    if session.get("role") != "doctor":
        flash("Unauthorized", "error")
        return redirect(url_for("dashboard"))
        
    update_data = {
        "degree": request.form.get("degree"),
        "phone": request.form.get("phone"),
        "address": request.form.get("address")
    }
    
    # Handle Photo Upload
    photo = request.files.get("photo")
    if photo and photo.filename:
        # Store as base64 in MongoDB cloud
        photo_b64 = base64.b64encode(photo.read()).decode('utf-8')
        update_data["photo_base64"] = photo_b64
        
    users_collection.update_one(
        {"_id": ObjectId(session.get("user_id"))},
        {"$set": update_data}
    )
    flash("Profile updated successfully!", "success")
    return redirect(url_for("dashboard"))

@app.route("/api/book_appointment", methods=["POST"])
@login_required
def book_appointment():
    if session.get("role") != "parent":
        return {"error": "Only parents can book appointments"}, 403
        
    data = request.json
    doctor_id = data.get("doctor_id")
    child_id = data.get("child_id")
    date = data.get("date")
    parent_id = session.get("user_id")
    
    if not all([doctor_id, child_id, date]):
        return {"error": "Missing booking details. Make sure you select a child."}, 400
        
    # Validation 1: Doctor max 4 appointments per day
    doc_appts = appointments_collection.count_documents({"doctor_id": doctor_id, "date": date, "status": "upcoming"})
    if doc_appts >= 4:
        return {"error": "This doctor is fully booked for this date (Max 4 slots)."}, 400
        
    # Validation 2: Parent cannot double book on the same date
    parent_appts = appointments_collection.count_documents({"parent_id": parent_id, "date": date, "status": "upcoming"})
    if parent_appts >= 1:
        return {"error": "You already have an appointment scheduled for this date."}, 400
        
    appointment = {
        "doctor_id": doctor_id,
        "parent_id": parent_id,
        "child_id": child_id,
        "date": date,
        "status": "upcoming",
        "created_at": time.time()
    }
    appointments_collection.insert_one(appointment)
    
    return {"message": "Appointment booked successfully!"}

@app.route("/api/complete_appointment/<app_id>", methods=["POST"])
@login_required
def complete_appointment(app_id):
    if session.get("role") != "doctor":
        return {"error": "Unauthorized"}, 403
        
    appointments_collection.update_one(
        {"_id": ObjectId(app_id), "doctor_id": session.get("user_id")},
        {"$set": {"status": "completed"}}
    )
    return {"message": "Appointment marked as completed!"}

@app.route("/api/cancel_appointment/<app_id>", methods=["POST"])
@login_required
def cancel_appointment(app_id):
    if session.get("role") != "parent":
        return {"error": "Unauthorized"}, 403
        
    appointments_collection.delete_one(
        {"_id": ObjectId(app_id), "parent_id": session.get("user_id")}
    )
    return {"message": "Appointment cancelled successfully."}

@app.route("/api/delete_child/<child_id>", methods=["POST"])
@login_required
def delete_child(child_id):
    if session.get("role") != "parent":
        return {"error": "Unauthorized"}, 403
    
    # Ensure parent owns the child
    child = children_collection.find_one({"_id": ObjectId(child_id), "parent_id": session.get("user_id")})
    if not child:
        return {"error": "Child not found or unauthorized"}, 404
        
    # Cascade delete
    assessments_collection.delete_many({"child_id": child_id})
    games_collection.delete_many({"child_id": child_id})
    appointments_collection.delete_many({"child_id": child_id})
    children_collection.delete_one({"_id": ObjectId(child_id)})
    
    flash("Child profile and all associated data deleted successfully.", "success")
    return {"message": "Success"}

@app.route("/api/delete_account", methods=["POST"])
@login_required
def delete_account():
    user_id = session.get("user_id")
    role = session.get("role")
    
    if role == "parent":
        # Cascade delete children and their data
        children = list(children_collection.find({"parent_id": user_id}))
        for child in children:
            c_id = str(child["_id"])
            assessments_collection.delete_many({"child_id": c_id})
            games_collection.delete_many({"child_id": c_id})
            appointments_collection.delete_many({"child_id": c_id})
        children_collection.delete_many({"parent_id": user_id})
        appointments_collection.delete_many({"parent_id": user_id})
    
    elif role == "doctor":
        # Cascade delete doctor appointments
        appointments_collection.delete_many({"doctor_id": user_id})
        
    # Finally delete user
    users_collection.delete_one({"_id": ObjectId(user_id)})
    session.clear()
    return {"message": "Account deleted successfully."}

@app.route("/api/update_calendar", methods=["POST"])
@login_required
def update_calendar():
    if session.get("role") != "doctor":
        return {"error": "Unauthorized"}, 401
    
    data = request.json
    available_dates = data.get("available_dates", [])
    
    users_collection.update_one(
        {"_id": ObjectId(session.get("user_id"))},
        {"$set": {"available_dates": available_dates}}
    )
    return {"message": "Calendar updated successfully!"}

@app.route("/edit_child/<child_id>", methods=["POST"])
@login_required
def edit_child(child_id):
    child = children_collection.find_one({"_id": ObjectId(child_id)})
    if not child:
        flash("Child not found", "error")
        return redirect(url_for("dashboard"))
        
    # Security: only the parent who created the profile or a doctor can edit
    if session.get("role") != "doctor" and child.get("parent_id") != session.get("user_id"):
        flash("Unauthorized action", "error")
        return redirect(url_for("dashboard"))
        
    update_data = {
        "name": request.form.get("name"),
        "age": int(request.form.get("age")) if request.form.get("age") else 0,
        "gender": request.form.get("gender")
    }
    
    # Handle Photo Upload
    photo = request.files.get("photo")
    if photo and photo.filename:
        photo_b64 = base64.b64encode(photo.read()).decode('utf-8')
        update_data["photo_base64"] = photo_b64
        
    children_collection.update_one(
        {"_id": ObjectId(child_id)},
        {"$set": update_data}
    )
    flash("Child profile updated successfully!", "success")
    return redirect(url_for("child_progress", child_id=child_id))


@app.route("/doctor/<doctor_id>")
@login_required
def doctor_profile(doctor_id):
    doctor = users_collection.find_one({"_id": ObjectId(doctor_id), "role": "doctor"})
    if not doctor:
        flash("Doctor not found", "error")
        return redirect(url_for("dashboard"))
        
    children = []
    if session.get("role") == "parent":
        children = list(children_collection.find({"parent_id": session.get("user_id")}))
        
    return render_template("doctor_profile.html", doctor=doctor, children=children)

@app.route("/child/<child_id>")
@login_required
def child_progress(child_id):
    child = children_collection.find_one({"_id": ObjectId(child_id)})
    if not child:
        flash("Child not found", "error")
        return redirect(url_for("dashboard"))
        
    assessments = list(assessments_collection.find({"child_id": child_id}).sort("date", -1))
    games = list(games_collection.find({"child_id": child_id}).sort("date", -1))
    
    # Simple recommendation based on latest assessment
    recommendation = "Complete a screening assessment to get personalized recommendations."
    if assessments:
        latest = assessments[0]
        if latest["percent"] >= 60:
            recommendation = "High risk indicated. Please consult a pediatrician or child psychologist for formal evaluation. Continue focusing on empathy and social scenario games."
        elif latest["percent"] >= 40:
            recommendation = "Moderate risk indicated. Keep monitoring the child's development. Engage consistently with the Emotion and Speech interactive games."
        else:
            recommendation = "Low risk indicated. Continue usual development monitoring and enjoy the interactive learning games!"
            
    return render_template("child_progress.html", child=child, assessments=assessments, games=games, recommendation=recommendation)

@app.route("/api/chat", methods=["POST"])
def chat():
    if not GEMINI_API_KEY:
        return {"response": "AURA is currently unavailable. Please ask the administrator to add a valid GEMINI_API_KEY to the .env file."}, 500
        
    data = request.json
    user_msg = data.get("message", "")
    
    if not user_msg:
        return {"response": "I didn't catch that. Could you repeat?"}, 400
        
    # Build RAG Context based on session
    role = session.get("role", "guest")
    user_id = session.get("user_id")
    context = ""
    
    # 1. Dynamic Platform Data (from MongoDB) - Optimized RAG to prevent Gemini token limit exhaustion
    context_parts = []
    msg_lower = user_msg.lower()
    
    # Check if the user is asking about doctors or booking appointments
    mentions_doctors = any(x in msg_lower for x in ["doctor", "specialist", "pediatrician", "psychologist", "therapist", "appointment", "schedule", "book", "availab"])
    
    if users_collection is not None:
        if mentions_doctors:
            doctors = list(users_collection.find({"role": "doctor"}))
            doc_info = f"The AutiScan platform currently has {len(doctors)} registered doctors available. Here is their data:\n"
            for doc in doctors:
                avail = ", ".join(doc.get("available_dates", [])) if doc.get("available_dates") else "None currently marked"
                doc_info += f"- Dr. {doc.get('name')}, Specialty/Degree: {doc.get('degree', 'Specialist')}, Available Dates: {avail}.\n"
            doc_info += "\nIf a parent asks who is available, list the doctors and their available dates. If the parent asks for a recommendation based on their child's progress, recommend a relevant specialist from this list (e.g., Psychologist for high risk, Pediatrician for moderate risk, Speech Therapist for speech issues)."
            context_parts.append(doc_info)
        else:
            context_parts.append("AutiScan has registered pediatricians, child psychologists, and speech therapists available for consultation.")

    # Retrieve child details if logged in (only fetch what is relevant to the query to save tokens)
    if children_collection is not None:
        if role == "parent":
            children = list(children_collection.find({"parent_id": user_id}))
            has_mention = any(c.get("name", "").lower() in msg_lower for c in children)
            asks_general = any(x in msg_lower for x in ["children", "child", "my kids", "progress", "report"])
            
            parent_context = "User is a logged-in parent. "
            added_child = False
            for child in children:
                child_name = child.get("name", "")
                if (child_name.lower() in msg_lower) or asks_general or (len(children) <= 1) or (not has_mention):
                    added_child = True
                    child_id = str(child['_id'])
                    child_desc = f"Child Name: {child_name} (Age: {child.get('age')}, Gender: {child.get('gender')}). "
                    if assessments_collection is not None:
                        assessments = list(assessments_collection.find({"child_id": child_id}).sort("date", -1).limit(1))
                        if assessments:
                            child_desc += f"Latest Assessment Risk Level: {assessments[0].get('spectrum')}. "
                    if games_collection is not None:
                        games = list(games_collection.find({"child_id": child_id}).sort("date", -1).limit(3))
                        if games:
                            child_desc += "Recent Game Scores: " + ", ".join([f"{g.get('game_name')}: {g.get('score')}" for g in games]) + ". "
                    parent_context += f"\n- {child_desc}"
            if added_child:
                context_parts.append(parent_context)
                
        elif role == "doctor":
            children = list(children_collection.find({}))
            has_mention = any(c.get("name", "").lower() in msg_lower for c in children)
            asks_general = any(x in msg_lower for x in ["children", "patients", "all kids", "progress", "dashboard"])
            
            doctor_context = "User is a logged-in doctor. "
            added_child = False
            for child in children:
                child_name = child.get("name", "")
                if (child_name.lower() in msg_lower) or asks_general:
                    added_child = True
                    child_id = str(child['_id'])
                    child_desc = f"Child Name: {child_name} (Age: {child.get('age')}, Gender: {child.get('gender')}). "
                    if assessments_collection is not None:
                        assessments = list(assessments_collection.find({"child_id": child_id}).sort("date", -1).limit(1))
                        if assessments:
                            child_desc += f"Latest Assessment Risk Level: {assessments[0].get('spectrum')}. "
                    if games_collection is not None:
                        games = list(games_collection.find({"child_id": child_id}).sort("date", -1).limit(3))
                        if games:
                            child_desc += "Recent Game Scores: " + ", ".join([f"{g.get('game_name')}: {g.get('score')}" for g in games]) + ". "
                    doctor_context += f"\n- {child_desc}"
            
            if added_child:
                context_parts.append(doctor_context)
            else:
                context_parts.append("User is a logged-in doctor. If they ask about a specific child (e.g. by name), you can answer if their details are provided. Otherwise, you can check patient progress in the doctor dashboard.")
        else:
            context_parts.append("User is a guest (not logged in). They might need help logging in, registering, or learning about autism. Explain to them that they can log in via the Login button in the top navigation bar to save their screening tests.")
            
    context = "\n\n".join(context_parts)

    # 2. Local Knowledge Retrieval (RAG)
    retrieved_knowledge = ""
    if RAG_NORMALIZED_EMBEDDINGS is not None and len(RAG_INDEX) > 0:
        try:
            # Generate query embedding
            response = genai.embed_content(
                model="models/gemini-embedding-2",
                content=user_msg,
                task_type="retrieval_query"
            )
            query_vector = np.array(response['embedding'])
            query_norm = np.linalg.norm(query_vector)
            if query_norm > 0:
                normalized_query = query_vector / query_norm
                similarities = np.dot(RAG_NORMALIZED_EMBEDDINGS, normalized_query)
                
                # Filter by similarity threshold to avoid irrelevant matches
                top_indices = np.argsort(similarities)[::-1][:3]
                matched_chunks = []
                for idx in top_indices:
                    if similarities[idx] > 0.35:  # Keep only relevant matches
                        chunk = RAG_INDEX[idx]
                        matched_chunks.append(f"Source: {chunk['title']} - {chunk['header']}\nContent: {chunk['content']}")
                
                if matched_chunks:
                    retrieved_knowledge = "\n\nRetrieved Platform Knowledge / FAQ:\n" + "\n\n".join(matched_chunks)
        except Exception as e:
            # Fall back gracefully if embedding service fails
            print("Error retrieving RAG knowledge:", e)
            
    if retrieved_knowledge:
        context += retrieved_knowledge

    system_prompt = f"""
You are AURA, a highly intelligent, versatile, and friendly AI assistant.
While you specialize in helping users navigate the AutiScan platform (an AI-powered web app for autism screening and therapeutic games), you are also capable of answering ANY general knowledge questions like a universal AI assistant. 
Do NOT refuse to answer questions outside of the autism domain; assist the user with whatever they ask.

Use the following platform context and retrieved knowledge to provide accurate, personalized responses when relevant:
[CONTEXT BEGIN]
{context}
[CONTEXT END]

Be concise, helpful, and use markdown for formatting. Do not hallucinate child data or platform details that aren't in the context.

IMPORTANT: At the very end of EVERY response, you MUST provide exactly 2 or 3 short, relevant follow-up questions the user might want to ask next.
Format them exactly like this on a single new line at the very end of your response:
SUGGESTED_QUESTIONS: First question | Second question | Third question
"""

    try:
        model = genai.GenerativeModel('gemini-flash-lite-latest', system_instruction=system_prompt)
        response = model.generate_content(user_msg)
        return {"response": response.text}
    except Exception as e:
        import traceback
        traceback.print_exc()
        err_msg = str(e)
        if "quota" in err_msg.lower() or "limit" in err_msg.lower() or "exhausted" in err_msg.lower() or "429" in err_msg:
            return {"response": "AURA is currently receiving too many requests under the Google Gemini Free Tier. Please wait 15–30 seconds and try again! ⏳"}
        return {"response": f"I'm having a bit of trouble: {err_msg}"}, 500

@app.route("/api/save_game", methods=["POST"])
def save_game():
    if 'user_id' not in session:
        return {"error": "Not logged in"}, 401
    
    data = request.json
    child_id = data.get("child_id")
    game_name = data.get("game_name")
    score = data.get("score", 0)
    
    if not child_id or not game_name:
        return {"error": "Missing data"}, 400
        
    game_data = {
        "child_id": child_id,
        "game_name": game_name,
        "score": score,
        "date": datetime.datetime.now()
    }
    games_collection.insert_one(game_data)
    return {"message": "Game progress saved successfully"}



# Load ensemble models
lr_model, nn_model, rf_model = pickle.load(open("model/autism_model.pkl", "rb"))

# -------- MAIN PAGES --------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/screening")
def screening():
    children = []
    if session.get("user_id"):
        # If logged in, fetch eligible children to associate the assessment with
        if session.get("role") == "parent":
            children = list(children_collection.find({"parent_id": session.get("user_id")}))
        elif session.get("role") == "doctor":
            children = list(children_collection.find({}))
            
    # Convert ObjectIds to string for the template
    for c in children:
        c["_id"] = str(c["_id"])
        
    return render_template("screening.html", children=children)

@app.route("/awareness")
def awareness():
    return render_template("awareness.html")

@app.route("/games")
@login_required
def games_hub():
    children = []
    if session.get("user_id"):
        if session.get("role") == "parent":
            children = list(children_collection.find({"parent_id": session.get("user_id")}))
        elif session.get("role") == "doctor":
            children = list(children_collection.find({}))
            
    for c in children:
        c["_id"] = str(c["_id"])
        
    return render_template("games.html", children=children)

# -------- AUTISM SUBPAGES --------
@app.route("/what-is-autism")
def what_is_autism():
    return render_template("autism/what-is-autism.html")

@app.route("/autism-screening-info")
def autism_screening_info():
    return render_template("autism/autism-screening.html")

@app.route("/autism-diagnosis")
def autism_diagnosis():
    return render_template("autism/autism-diagnosis.html")

@app.route("/causes")
def causes():
    return render_template("autism/causes-of-autism.html")

@app.route("/symptoms")
def symptoms():
    return render_template("autism/signs-and-symptoms.html")

@app.route("/vaccines")
def vaccines():
    return render_template("autism/vaccines-and-autism.html")

@app.route("/therapies")
def therapies():
    return render_template("therapies.html")

@app.route('/game/eye')
@login_required
def game_eye():
    return render_template('games/eye.html')

@app.route('/game/speech')
@login_required
def game_speech():
    return render_template('games/speech.html')

@app.route('/game/emotion')
@login_required
def game_emotion():
    return render_template('games/emotion.html')

@app.route('/game/social')
@login_required
def game_social():
    return render_template('games/social.html')

@app.route('/game/flex')
@login_required
def game_flex():
    return render_template('games/flex.html')

@app.route('/game/memory')
@login_required
def game_memory():
    return render_template('games/memory.html')

@app.route('/nearby-doctors')
def nearby_doctors():
    # Real data for autism specialists in Pune
    doctors = [
        {
            "name": "Dr. Tushar Adkar",
            "type": "Pediatrician & Autism Specialist",
            "address": "Hriday Mother & Child Care Clinic, 1st Floor, Pristine Shatrunjay, Ravet, Pune - 412101",
            "phone": "+91 91378 77430",
            "services": ["Evaluations", "Speech Therapy", "Occupational Therapy"],
            "google_link": "https://www.google.com/search?q=Dr.+Tushar+Adkar+Pediatrician+Pune",
            "image": "https://img.freepik.com/free-photo/portrait-smiling-handsome-male-doctor-man_171337-5055.jpg" # Representative photo
        },
        {
            "name": "Neuro Revolution International",
            "type": "Autism & Child Development Center",
            "address": "1, Laxmi Vilas Rd, Bhosale Nagar, Hadapsar, Pune",
            "phone": "+91 93226 72088",
            "services": ["Sensory Integration", "Behavioral Interventions", "ADHD"],
            "google_link": "https://www.google.com/search?q=Neuro+Revolution+International+Pune",
            "image": "https://img.freepik.com/free-photo/modern-hospital-building_1127-2401.jpg" # Clinic photo
        },
        {
            "name": "Butterfly Learnings Center",
            "type": "Multi-disciplinary Therapy Center",
            "address": "Multiple Centers across Pune (Baner, Wakad, etc.)",
            "phone": "Check Website",
            "services": ["Developmental Therapy", "Applied Behavior Analysis (ABA)"],
            "google_link": "https://www.google.com/search?q=Butterfly+Learnings+Center+Pune",
            "image": "https://img.freepik.com/free-photo/smiling-female-doctor-holding-medical-records_53876-128913.jpg" # Representative photo
        },
        {
            "name": "Laddrs Child Development Center",
            "type": "Comprehensive Therapy Center",
            "address": "Pimple Saudagar, Pune",
            "phone": "+91 90280 20022",
            "services": ["Occupational Therapy", "Speech-Language Therapy", "ABA"],
            "google_link": "https://www.google.com/search?q=Laddrs+Child+Development+Center+Pune",
            "image": "https://img.freepik.com/free-photo/empty-pediatric-clinic-room-with-toys-furniture_1098-19965.jpg" # Clinic photo
        }
    ]
    return render_template('nearby_doctors.html', doctors=doctors)

# -------- ML PREDICTION --------
@app.route("/predict", methods=["POST"])
def predict():
    import pandas as pd

    # Feature columns in the same order as training
    feature_cols = [
        'A1_Score','A2_Score','A3_Score','A4_Score','A5_Score',
        'A6_Score','A7_Score','A8_Score','A9_Score','A10_Score',
        'age','gender','jundice','austim'
    ]

    data_list = []

    # Collect quiz answers (10 questions)
    for i in range(10):
        val = request.form.get(f"q{i}")
        data_list.append(int(val) if val else 0)

    # Collect additional details and map properly
    # Age
    age_raw = request.form.get("age")
    age = int(age_raw) if age_raw else 5
    data_list.append(age)

    # Gender
    gender_raw = request.form.get("gender")  # "m" or "f"
    if gender_raw in ["m", "1", 1]:
        gender = 1
    else:
        gender = 0
    data_list.append(gender)

    # Jaundice
    jundice_raw = request.form.get("jundice")  # "yes"/"no"
    jundice = 1 if jundice_raw in ["yes", "1", 1] else 0
    data_list.append(jundice)

    # Family history
    austim_raw = request.form.get("austim")  # "yes"/"no"
    austim = 1 if austim_raw in ["yes", "1", 1] else 0
    data_list.append(austim)

    print("FINAL INPUT:", data_list)

    # Convert to DataFrame with correct column order
    df_input = pd.DataFrame([data_list], columns=feature_cols)

    # Ensemble prediction
    lr_prob = lr_model.predict_proba(df_input)[0][1]
    nn_prob = nn_model.predict_proba(df_input)[0][1]
    rf_prob = rf_model.predict_proba(df_input)[0][1]

    final_prob = (lr_prob + nn_prob + rf_prob) / 3
    final_prob = np.clip(final_prob, 0.05, 0.95)
    # shrink towards 50%
    calibrated_prob = 0.5 + (final_prob - 0.5) * 0.6
    percent = round(calibrated_prob * 100, 2)

    # Risk spectrum
    if percent < 20:
        spectrum = "Very Low Risk"
    elif percent < 40:
        spectrum = "Low Risk"
    elif percent < 60:
        spectrum = "Moderate Risk"
    elif percent < 80:
        spectrum = "High Risk"
    else:
        spectrum = "Very High Risk"

    # --- SHAP EXPLAINER ---
    try:
        explainer = shap.TreeExplainer(rf_model)
        shap_explanation = explainer(df_input)
        
        # Binary classification random forest usually returns shape (1, n_features, 2)
        if len(shap_explanation.values.shape) == 3:
            sv = shap_explanation.values[0, :, 1]
        else:
            sv = shap_explanation.values[0]
            
        human_features = [
            "Lack of Eye Contact", "Discomfort playing with others", "Difficulty understanding feelings",
            "Distress with routine changes", "Repetitive movements/behaviors", "Difficulty starting conversations",
            "Slow to respond to name", "Sensitivity to sounds/textures", "Use of unusual gestures",
            "Difficulty in social situations", "Age factor", "Gender factor", "Born with Jaundice", "Family history of autism"
        ]
        
        feature_impacts = []
        for i, val in enumerate(sv):
            feature_impacts.append({
                "name": human_features[i],
                "impact": float(val)
            })
            
        feature_impacts.sort(key=lambda x: x["impact"], reverse=True)
        
        # Top positive (increased risk)
        top_positive = [f for f in feature_impacts if f["impact"] > 0][:3]
        # Top negative (decreased risk)
        top_negative = [f for f in feature_impacts if f["impact"] < 0][::-1][:2]
        
        shap_insights = {
            "top_positive": [{"name": f["name"], "impact_percent": round(f["impact"] * 100, 1)} for f in top_positive],
            "top_negative": [{"name": f["name"], "impact_percent": round(abs(f["impact"]) * 100, 1)} for f in top_negative]
        }
    except Exception as e:
        print("SHAP Error:", e)
        shap_insights = {"top_positive": [], "top_negative": []}

    # Dynamic Game Recommendations based on Assessment Answers
    answers = data_list[:10]
    suggested_games = []
    
    if answers[0] == 1: # Q1: Eye Contact
        suggested_games.append({
            "name": "Eye Contact & Focus", 
            "link": "/game/eye",
            "desc": "A tracking game involving a moving star that rewards sustained attention.",
            "reason": "Based on the assessment, there are indications of reduced eye contact. This game gently encourages visual tracking and focus."
        })
        
    if answers[2] == 1: # Q3: Understanding Feelings
        suggested_games.append({
            "name": "Emotion Recognition", 
            "link": "/game/emotion",
            "desc": "A fun game to help identify different facial expressions like happy, sad, or angry.",
            "reason": "The assessment suggested difficulty in understanding feelings. This game teaches how to recognize basic emotions and social cues."
        })
        
    if answers[3] == 1 or answers[4] == 1: # Q4: Routine Change, Q5: Repetitive Behavior
        suggested_games.append({
            "name": "Transition Timer (Flexibility)", 
            "link": "/game/flex",
            "desc": "A fast-paced adapting game where rules change dynamically.",
            "reason": "The results indicated distress with routine changes. This cognitive flexibility game helps practice adapting to new rules in a safe, fun environment."
        })
        
    if answers[5] == 1 or answers[7] == 1: # Q6: Starting Conversations, Q8: Sensitivity
        suggested_games.append({
            "name": "Speech & Sound Therapy", 
            "link": "/game/speech",
            "desc": "An interactive sound and image matching game using the microphone.",
            "reason": "Because starting conversations or sound processing appeared challenging, this game encourages verbalizing distinct sounds."
        })
        
    if answers[1] == 1 or answers[9] == 1: # Q2: Playing with Others, Q10: Social Situations
        suggested_games.append({
            "name": "Social Scenarios", 
            "link": "/game/social",
            "desc": "Interactive everyday stories where you choose the correct social action.",
            "reason": "The assessment highlighted discomfort in social situations. These digital stories provide unpressured practice for real-world interactions."
        })
        
    if not suggested_games:
        suggested_games.append({
            "name": "Pattern Memory", 
            "link": "/game/memory",
            "desc": "A classic card-matching game.",
            "reason": "No specific high-risk social indicators were found, but general cognitive development and working memory practice is actively beneficial."
        })

    # Limit to top 3 uniquely suggested games to avoid overwhelming
    games = suggested_games[:3]
    
    child_id = request.form.get("child_id")
    child_name = ""
    if child_id and child_id != "none":
        from bson.objectid import ObjectId
        if children_collection is not None:
            child = children_collection.find_one({"_id": ObjectId(child_id)})
            if child:
                child_name = child.get("name", "")
                
        assessment_data = {
            "child_id": child_id,
            "date": datetime.datetime.now(),
            "percent": percent,
            "spectrum": spectrum,
            "age": age,
            "gender": "Male" if gender == 1 else "Female",
            "jaundice": "Yes" if jundice == 1 else "No",
            "family_history": "Yes" if austim == 1 else "No",
            "answers": data_list[:10],
            "shap_insights": shap_insights
        }
        if assessments_collection is not None:
             assessments_collection.insert_one(assessment_data)
             
             from bson.objectid import ObjectId
             if children_collection is not None:
                 children_collection.update_one(
                     {"_id": ObjectId(child_id)},
                     {"$set": {
                         "age": age,
                         "gender": "Male" if gender == 1 else "Female"
                     }}
                 )

    return render_template(
        "result.html",
        percent=percent,
        spectrum=spectrum,
        age=age,
        gender=gender,
        jundice=jundice,
        austim=austim,
        games=games,   # Add this
        child_name=child_name,
        shap_insights=shap_insights
    )
    
# -------- PDF DOWNLOAD ROUTE (NEW) --------
@app.route('/download-pdf', methods=['POST'])
def download_pdf():
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    percent = request.form.get("percent")
    spectrum = request.form.get("spectrum")
    age = request.form.get("age")
    gender = int(request.form.get("gender"))
    jundice = int(request.form.get("jundice"))
    austim = int(request.form.get("austim"))
    name = request.form.get("name", "Unknown")  # default if somehow missing
    

    # Convert percent to float for logic
    percent_val = float(percent)

    # Summary
    if percent_val < 20:
        summary = "The screening indicates a very low likelihood of autism traits."
    elif percent_val < 40:
        summary = "The screening indicates a low likelihood of autism traits."
    elif percent_val < 60:
        summary = "The screening indicates a moderate likelihood of autism traits."
    elif percent_val < 80:
        summary = "The screening indicates a high likelihood of autism traits."
    else:
        summary = "The screening indicates a very high likelihood of autism traits."

    # Recommendation
    if percent_val >= 60:
        recommendation = "It is recommended to consult a pediatrician or child psychologist for further evaluation."
    elif percent_val >= 40:
        recommendation = "Consider monitoring the child's development and consult a specialist if concerns persist."
    else:
        recommendation = "No immediate concerns based on screening, but continue observing developmental milestones."

    print("Age:", age)
    print("Gender:", gender)
    print("Jaundice:", jundice)
    print("Family History:", austim)
    print("RAW:", gender, jundice, austim)
    print("TYPE:", type(gender))

    # display date
    from datetime import datetime
    today = datetime.now().strftime("%d %B %Y")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("AutiScan Screening Report", styles['Title']))
    content.append(Spacer(1, 20))
    content.append(Paragraph(f"Report Generated On: {today}", styles['Normal']))
    content.append(Spacer(1, 10))

    '''
    content.append(Paragraph(f"Name: {name}", styles['Normal']))  
    content.append(Paragraph(f"Age: {age}", styles['Normal']))
    content.append(Paragraph(f"Gender: {'Male' if gender == 1 else 'Female'}", styles['Normal']))
    content.append(Paragraph(f"Jaundice: {'Yes' if jundice == 1 else 'No'}", styles['Normal']))
    content.append(Paragraph(f"Family History of Autism: {'Yes' if austim == 1 else 'No'}", styles['Normal']))
'''
    content.append(Paragraph("Details", styles['Heading2']))
    content.append(Spacer(1, 5))

    content.append(Paragraph(f"Name: {name}", styles['Normal']))  
    content.append(Paragraph(f"Age: {age}", styles['Normal']))
    content.append(Paragraph(f"Gender: {'Male' if gender == 1 else 'Female'}", styles['Normal']))
    content.append(Paragraph(f"Jaundice at Birth: {'Yes' if jundice == 1 else 'No'}", styles['Normal']))
    content.append(Paragraph(f"Family History: {'Yes' if austim == 1 else 'No'}", styles['Normal']))

    content.append(Spacer(1, 20))
    content.append(Paragraph("Screening Result", styles['Heading2']))
    content.append(Spacer(1, 5))
    content.append(Paragraph(f"Score: {percent}%", styles['Normal']))
    content.append(Paragraph(f"Risk Level: {spectrum}", styles['Normal']))
    content.append(Spacer(1, 20))
    content.append(Paragraph("Summary", styles['Heading2']))
    content.append(Spacer(1, 5))
    content.append(Paragraph(summary, styles['Normal']))

    content.append(Spacer(1, 20))
    content.append(Paragraph("Recommendations", styles['Heading2']))
    content.append(Spacer(1, 5))
    content.append(Paragraph(recommendation, styles['Normal']))
    content.append(Spacer(1, 20))
    content.append(Paragraph("Disclaimer", styles['Heading2']))
    content.append(Spacer(1, 5))

    content.append(Paragraph(
    "This screening tool is not a medical diagnosis. It is intended for awareness purposes only. "
    "Please consult a qualified healthcare professional for a complete evaluation.",
    styles['Normal']
))


    doc.build(content)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="AutiScan_Report.pdf",
        mimetype='application/pdf'
    )

# Print model path info and start server
if __name__ == "__main__":
    model_path = os.path.abspath("model/autism_model.pkl")
    print("MODEL PATH:", model_path)
    print("LAST MODIFIED:", time.ctime(os.path.getmtime(model_path)))
    
    app.run(debug=True)


    