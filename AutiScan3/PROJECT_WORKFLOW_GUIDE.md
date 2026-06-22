# AutiScan End-to-End Project Workflow

This document explains the complete workflow of **AutiScan** in an easy, logical, step-by-step way. Use this to explain to the examiner how different parts of the project (Flask, Google Auth, ML model, MongoDB, RAG, and Hugging Face deployment) connect and work together.

---

## Step 1: User Landing & Authentication (Google OAuth)

```
[User Browser] (HTTPS)
   │
   ▼
[Hugging Face Space] ──► Breaks out of iframe (target="_top")
   │
   ▼
[Google Consent Screen] (User logs in & approves)
   │
   ▼
[Flask Backend (/authorize/google)] ──► ProxyFix forces HTTPS redirect verification
   │
   ▼
[MongoDB Atlas] ──► Checks if user exists. If new, redirects to complete profile (Select Parent/Doctor)
```

1. **Accessing the App**: The user visits `https://shreyaviku-autiscan.hf.space`. 
2. **Iframe Breakout**: Because Hugging Face hosts the app inside an iframe, and Google blocks sign-ins inside iframes (for security), the login button uses `target="_top"` to open Google in the main browser window.
3. **Redirect to Google**: Clicking "Continue with Google" redirects the user to Google’s secure login page.
4. **ProxyFix Check**: After the user signs in, Google sends them back to our callback endpoint `/authorize/google`. Flask uses **ProxyFix** middleware to read Hugging Face's reverse proxy headers, ensuring the redirect URL matches the secure `https` protocol.
5. **Database Entry**: Flask extracts the user's name and email. It queries **MongoDB Atlas** (`users_collection`):
   * If the user already exists, it starts their session and loads their dashboard.
   * If they are new, it registers them, starts a session, and redirects them to `/complete_profile` to select their role (**Parent** or **Doctor**).

---

## Step 2: Child Registration & Screening (ML Inference)

```
[Parent Dashboard] ──► Registers child (Name, Age, Gender) ──► Saved in MongoDB
   │
   ▼
[Screening Form] ──► Parent answers 10 questions + additional metrics
   │
   ▼
[Flask Backend (/predict)]
   │
   ├─► 1. Runs Ensemble Model (Logistic Regression + Neural Network + Random Forest)
   ├─► 2. Runs SHAP Explainer on Random Forest (calculates risk/protective factors)
   └─► 3. Maps score to Risk Spectrum (e.g., "High Risk")
   │
   ▼
[MongoDB / Result Screen] ──► Saves result to database & displays report with personalized games
```

1. **Child Registration**: Parents add their children. Flask saves the details (Name, Age, Gender, Parent ID) in MongoDB’s `children` collection.
2. **Taking the Test**: The parent opens the screening form and answers 10 behavioral questions (Q-CHAT-10 questionnaire).
3. **Running the ML Models**: Submitting the form posts the data to `/predict`. The Flask backend:
   * Formats the answers, age, gender, history of jaundice, and family history into a Pandas DataFrame.
   * Passes the data to the **Ensemble Model** loaded from `autism_model.pkl`.
   * Calculates the average probability of autism across three classifiers: **Logistic Regression**, **Multi-layer Perceptron (Neural Network)**, and **Random Forest**.
   * Applies calibration to scale the final risk percentage.
4. **Generating Explanations (SHAP)**: It uses `shap.TreeExplainer` on the Random Forest model to calculate Shapley values. This extracts the **Top 3 Risk Factors** (answers that raised the risk percentage) and **Top 2 Protective Factors** (answers/attributes that kept the risk lower).
5. **Database Storage**: The screening results (Risk Percentage, Risk Spectrum, SHAP impacts, Date) are saved in MongoDB’s `assessments` collection, linked by the child's `_id`.
6. **Output**: The user is shown the risk spectrum report and a list of **Personalized Game Recommendations** based on their answers.

---

## Step 3: Therapeutic Gameplay (Data Logging)

```
[Games Hub] ──► Parent selects active child (Saved in browser's LocalStorage)
   │
   ▼
[Child plays Game] ──► e.g., Eye Contact Game (speeds up/slows down dynamically)
   │                  e.g., Speech Game (uses browser's native Web Speech API)
   ▼
[Game Over] ──► JavaScript fetches active child ID from LocalStorage
   │
   ▼
[API POST (/api/save_game)] ──► Saves game name, score, and date in MongoDB games_collection
   │
   ▼
[Dashboard Progress Charts] ──► Parent/Doctor views logs & progress over time
```

1. **Selecting Active Child**: In the Games Hub, the parent selects which child is playing. The child's MongoDB ID is stored in the browser's `localStorage` as `autiscan_active_child`.
2. **Gameplay**:
   * In the **Eye Contact** game, the speed adapts to the child's clicking speed in real-time (adaptive difficulty loop).
   * In the **Speech Therapy** game, the browser’s built-in **Web Speech API** runs local speech-to-text to verify if the child said the target word correctly.
3. **Saving Score**: Once the game ends, the frontend JavaScript sends a `POST` request to Flask's `/api/save_game` endpoint containing the child's ID, game name, and score.
4. **MongoDB Update**: Flask inserts the score log into the `games` collection.
5. **Analytics**: The parent or doctor dashboards query the `games` collection to plot progress charts using CSS or JavaScript.

---

## Step 4: The Aura Chatbot (Vector Search & Generative AI)

```
[Offline Build Step] ──► build_rag_index.py parses HTML, embeds text via Gemini, saves to rag_index.json
   │
   ▼
[Flask Server Start] ──► Loads rag_index.json & converts vectors to a normalized NumPy array
   │
   ▼
[User asks Aura] ──► "What is autism?"
   │
   ▼
[Gemini API] ──► Embeds user query into a 3072-dimensional vector
   │
   ▼
[Vector Search] ──► Computes similarity via NumPy Matrix Dot Product (in < 1 millisecond)
   │
   ▼
[Context Assembly] ──► Injects top 3 relevant text chunks + child data (if doctor is asking) into system prompt
   │
   ▼
[Gemini LLM] ──► Generates friendly, factual natural-language answer
   │
   ▼
[User Screen] ──► Response displayed in chatbot window
```

1. **Pre-building the Index**: Before deploying, we run `build_rag_index.py`. It extracts text from local informational pages, embeds the text using `models/gemini-embedding-2` via the Gemini API, and saves the vectors in `rag_index.json`.
2. **Startup Loading**: When Flask starts up on Hugging Face, it loads `rag_index.json` and builds a normalized 2D NumPy array of the vectors.
3. **Chat Query**: A user types a question to Aura.
4. **Semantic Retrieval (RAG)**:
   * The query is embedded via the Gemini API.
   * We calculate the cosine similarity between the query vector and all document vectors in memory using a fast **NumPy dot product**:
     $$\text{Similarities} = \text{Matrix}_{\text{docs}} \cdot \vec{Q}_{\text{query}}$$
   * The top 3 matching text chunks (with scores $>0.35$) are retrieved.
5. **Context Generation**: The text chunks, along with session details (such as child profiles if a doctor is asking about a patient), are injected into the LLM system prompt.
6. **Inference**: The `gemini-flash-lite-latest` model generates a natural language response based on the retrieved context and sends it to the user.

---

## Step 5: Hosting & Deployment (Hugging Face Spaces)

```
[Local Code Commit] ──► Git pushes updates to Hugging Face Repository
   │
   ▼
[Hugging Face Build] ──► Reads Dockerfile, installs requirements.txt, exposes Port 7860
   │
   ▼
[Inject Secrets] ──► Space settings inject MONGO_URI, GEMINI_API_KEY, and Google OAuth credentials
   │
   ▼
[Gunicorn Server] ──► Starts app:app to serve requests live
```

1. **Deployment**: When we run `git push hf main`, it triggers Hugging Face Spaces to read our `Dockerfile`.
2. **Dockerization**: The container is built based on `python:3.12-slim`:
   * Installs system dependencies.
   * Copies the requirements file and installs Python packages.
   * Exposes port `7860` (the standard port Hugging Face listens to).
3. **Environment Injection**: Hugging Face injects our database credentials (`MONGO_URI`), Gemini API keys (`GEMINI_API_KEY`), and Google credentials (`GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`) from the Space Settings secure vault.
4. **Live Execution**: Gunicorn starts the Flask application, and the app goes live for users globally.
