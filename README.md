# 🧠 AutiScan – AI-Powered Autism Screening & Support System

AutiScan is an intelligent web-based platform designed to **screen autism spectrum indicators in children** and provide **personalized intervention through interactive therapeutic games**.

It goes beyond prediction by offering **actionable recommendations**, making it a complete **AI-driven early support system**.

---

## 🚀 Features

### 🔍 1. Autism Screening (AI-Based)

* 10 behavioral questions based on developmental traits
* Uses **Machine Learning Ensemble Model**:

  * Logistic Regression
  * Neural Network
  * Random Forest
* Provides:

  * Autism probability (%)
  * Risk spectrum (Low → High)
  * Confidence score

---

### 🎮 2. Personalized Game Recommendations

* Suggests games based on child’s responses
* Each recommendation includes:

  * Game name
  * Description
  * Reason (Explainable AI)

👉 Example:

* Low eye contact → Eye Tracking Game
* Speech delay → Speech Builder Game
* Social difficulty → Social Interaction Game

---

### 🧩 3. Therapy-Based Interactive Games

| Game                    | Purpose                          |
| ----------------------- | -------------------------------- |
| 👁️ Eye Contact Trainer | Improves focus & visual tracking |
| 🧠 Memory Game          | Enhances memory & cognition      |
| 😊 Emotion Recognition  | Builds emotional understanding   |
| 🗣️ Speech Builder      | Improves communication           |
| 🤝 Social Interaction   | Teaches social behavior          |
| 🔄 Flexibility Game     | Improves adaptability            |

---

### 📄 4. PDF Report Generation

* Download detailed screening report
* Includes:

  * Score
  * Risk level
  * Summary
  * Recommendations

---

### 🌐 5. Awareness Platform

* Educational content about autism:

  * Symptoms
  * Causes
  * Diagnosis
  * Therapies

---

## 🧠 How It Works

1. User completes screening questionnaire
2. Data is processed using ML models
3. Autism probability is calculated
4. System analyzes behavioral patterns
5. Personalized game recommendations are generated
6. User can play games and begin early intervention

---

## 🛠️ Tech Stack

### 💻 Frontend

* HTML5
* CSS3
* JavaScript
* Bootstrap

### ⚙️ Backend

* Flask (Python)

### 🤖 Machine Learning

* Scikit-learn
* Ensemble Model (LR + NN + RF)

### 📊 Data Handling

* Pandas
* NumPy

### 📄 PDF Generation

* ReportLab

---

## 📁 Project Structure

```
AutiScan/
│
├── app.py
├── model/
│     └── autism_model.pkl
│
├── static/
│     └── style.css
│
├── templates/
│     ├── index.html
│     ├── screening.html
│     ├── result.html
│     ├── about.html
│     │
│     ├── autism/
│     │     ├── what-is-autism.html
│     │     ├── signs-and-symptoms.html
│     │
│     └── games/
│           ├── eye.html
│           ├── memory.html
│           ├── emotion.html
│           ├── speech.html
│           ├── social.html
│           └── flex.html
```

---

## ▶️ How to Run Locally

### 1. Clone Repository

```
git clone https://github.com/your-username/autiscan.git
cd autiscan
```

### 2. Install Dependencies

```
pip install flask pandas numpy scikit-learn reportlab
```

### 3. Run App

```
python app.py
```

### 4. Open Browser

```
http://127.0.0.1:5000/
```

---

## 🎯 Key Innovation

Unlike traditional systems that only predict, AutiScan:

✅ Provides **personalized intervention**
✅ Uses **explainable recommendations**
✅ Includes **therapy-based games**
✅ Acts as a **complete support system**

---

## 🧪 Future Enhancements

* 📈 Progress tracking dashboard
* 🤖 AI-based adaptive game difficulty
* 📱 Mobile app version
* 🧑‍⚕️ Doctor integration
* 🗄️ Database (MongoDB) for user history

---

## ⚠️ Disclaimer

This tool is intended for **educational and awareness purposes only**.
It is **not a medical diagnosis**. Please consult a healthcare professional for clinical evaluation.


---

## ⭐ Show Your Support

If you like this project, please ⭐ the repository!

---
