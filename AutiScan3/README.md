# AutiScan: AI-Powered Autism Screening & Therapeutic Games 🧩

AutiScan is a comprehensive, AI-driven web platform designed to assist parents and doctors in screening children for early signs of autism. It provides machine-learning-backed risk assessments, dynamic **Explainable AI (SHAP)** insights, interactive therapeutic games, and a seamless appointment scheduling system.

## 🌟 Key Features

* **AI Autism Screening Tool:** A robust questionnaire backed by an ensemble machine learning model (Logistic Regression, Neural Network, and Random Forest) to evaluate autism risk levels.
* **Explainable AI (XAI):** Utilizing **SHAP**, the platform provides transparent "AI Insights" that explain exactly which behavioral traits increased or decreased a child's risk score.
* **Therapeutic Game Hub:** A collection of interactive, browser-based games (Emotion Recognition, Eye Contact, Cognitive Flexibility, Speech Therapy) dynamically recommended based on the child's specific screening results.
* **Dual Dashboards:** 
  * **Parents:** Manage multiple child profiles, track screening and game progress over time, and book appointments with specialists.
  * **Doctors:** View assigned patients, manage appointment calendars, and analyze detailed AI-backed assessment histories.
* **AURA Chatbot:** An intelligent, context-aware chatbot powered by **Google Gemini** that provides personalized advice and helps users navigate the platform.
* **Downloadable Reports:** Dynamically generated PDF screening reports using ReportLab.

## 🛠️ Technology Stack

* **Frontend:** HTML5, Vanilla CSS, JavaScript, Bootstrap 5.3, Chart.js
* **Backend:** Python 3.12, Flask, Werkzeug Security
* **Database:** MongoDB Atlas (PyMongo)
* **Machine Learning:** Scikit-Learn, Pandas, NumPy
* **Explainable AI:** SHAP (SHapley Additive exPlanations)
* **Generative AI:** Google Generative AI (Gemini Flash)

## 🚀 Installation & Setup

Follow these steps to run AutiScan locally on your machine.

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/AutiScan.git
cd AutiScan
```

### 2. Set Up a Virtual Environment (Recommended)
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Variables
Create a `.env` file in the root directory and add the following keys:
```env
SECRET_KEY=your_flask_secret_key_here
MONGO_URI=your_mongodb_atlas_connection_string
GEMINI_API_KEY=your_google_gemini_api_key
```

### 5. Run the Application
```bash
python app.py
```
The application will start running at `http://127.0.0.1:5000/`.

## 🧠 Model Training
If you wish to retrain the machine learning model with new data:
1. Ensure `autism_child_data.csv` is in the root directory.
2. Run the training script:
```bash
python train_model.py
```
This will output a newly tuned ensemble model into the `/model` directory.

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
