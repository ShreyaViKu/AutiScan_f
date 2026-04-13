from flask import Flask, render_template, request, send_file
import pickle
import os, time
import pandas as pd
import numpy as np
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

# 🔹 Load ensemble models
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
    return render_template("screening.html")

@app.route("/awareness")
def awareness():
    return render_template("awareness.html")

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

# -------- ML PREDICTION --------
@app.route("/predict", methods=["POST"])
def predict():
    import pandas as pd

    # ✅ Feature columns in the same order as training
    feature_cols = [
        'A1_Score','A2_Score','A3_Score','A4_Score','A5_Score',
        'A6_Score','A7_Score','A8_Score','A9_Score','A10_Score',
        'age','gender','jundice','austim'
    ]

    data_list = []

    # 🔹 Collect quiz answers (10 questions)
    for i in range(10):
        val = request.form.get(f"q{i}")
        data_list.append(int(val) if val else 0)

    # 🔹 Collect additional details and map properly
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

    # 🔹 Convert to DataFrame with correct column order
    df_input = pd.DataFrame([data_list], columns=feature_cols)

    # 🔹 Ensemble prediction
    lr_prob = lr_model.predict_proba(df_input)[0][1]
    nn_prob = nn_model.predict_proba(df_input)[0][1]
    rf_prob = rf_model.predict_proba(df_input)[0][1]

    final_prob = (lr_prob + nn_prob + rf_prob) / 3
    final_prob = np.clip(final_prob, 0.05, 0.95)
    # shrink towards 50%
    calibrated_prob = 0.5 + (final_prob - 0.5) * 0.6
    percent = round(calibrated_prob * 100, 2)

    # 🔹 Risk spectrum
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

    confidence = round(abs(final_prob - 0.5) * 200, 2)

    return render_template(
        "result.html",
        percent=percent,
        spectrum=spectrum,
        confidence=confidence,
        age=age,
        gender=gender,
        jundice=jundice,
        austim=austim
    )
    
# -------- PDF DOWNLOAD ROUTE (NEW) --------
@app.route('/download-pdf', methods=['POST'])
def download_pdf():
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    percent = request.form.get("percent")
    spectrum = request.form.get("spectrum")
    confidence = request.form.get("confidence")
    age = request.form.get("age")
    gender = request.form.get("gender")
    jundice = request.form.get("jundice")
    austim = request.form.get("austim")
    name = request.form.get("name", "Unknown")  # 🔹 default if somehow missing

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("AutiScan Screening Report", styles['Title']))
    content.append(Spacer(1, 20))

    content.append(Paragraph(f"Name: {name}", styles['Normal']))  
    content.append(Paragraph(f"Age: {age}", styles['Normal']))
    content.append(Paragraph(f"Gender: {'Male' if gender == 1 else 'Female'}", styles['Normal']))
    content.append(Paragraph(f"Jaundice: {'Yes' if jundice == 1 else 'No'}", styles['Normal']))
    content.append(Paragraph(f"Family History of Autism: {'Yes' if austim == 1 else 'No'}", styles['Normal']))
        

    content.append(Spacer(1, 20))
    content.append(Paragraph(f"Score: {percent}%", styles['Heading2']))
    content.append(Paragraph(f"Risk Level: {spectrum}", styles['Heading2']))
    content.append(Paragraph(f"Confidence: {confidence}%", styles['Normal']))

    content.append(Spacer(1, 20))
    content.append(Paragraph(
        "⚠️ This is not a medical diagnosis. Please consult a healthcare professional.",
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

# 🔹 Print model path info and start server
if __name__ == "__main__":
    model_path = os.path.abspath("model/autism_model.pkl")
    print("MODEL PATH:", model_path)
    print("LAST MODIFIED:", time.ctime(os.path.getmtime(model_path)))
    
    app.run(debug=True)

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/screening")
def screening():
    return render_template("screening.html")