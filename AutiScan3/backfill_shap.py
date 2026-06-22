import pickle
import pandas as pd
import shap
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client.get_database("autiscan_db")
assessments_collection = db["assessments"]

# Load model
lr_model, nn_model, rf_model = pickle.load(open("model/autism_model.pkl", "rb"))

feature_cols = [
    'A1_Score','A2_Score','A3_Score','A4_Score','A5_Score',
    'A6_Score','A7_Score','A8_Score','A9_Score','A10_Score',
    'age','gender','jundice','austim'
]

human_features = [
    "Lack of Eye Contact", "Discomfort playing with others", "Difficulty understanding feelings",
    "Distress with routine changes", "Repetitive movements/behaviors", "Difficulty starting conversations",
    "Slow to respond to name", "Sensitivity to sounds/textures", "Use of unusual gestures",
    "Difficulty in social situations", "Age factor", "Gender factor", "Born with Jaundice", "Family history of autism"
]

explainer = shap.TreeExplainer(rf_model)

assessments = list(assessments_collection.find({"shap_insights": {"$exists": False}}))
print(f"Found {len(assessments)} assessments missing SHAP insights.")

for a in assessments:
    try:
        answers = a.get("answers", [])
        if len(answers) != 10:
            continue
            
        age = int(a.get("age", 5))
        gender_raw = a.get("gender", "Female")
        gender = 1 if gender_raw == "Male" else 0
        jundice_raw = a.get("jaundice", "No")
        jundice = 1 if jundice_raw == "Yes" else 0
        austim_raw = a.get("family_history", "No")
        austim = 1 if austim_raw == "Yes" else 0
        
        data_list = answers + [age, gender, jundice, austim]
        df_input = pd.DataFrame([data_list], columns=feature_cols)
        
        shap_explanation = explainer(df_input)
        
        if len(shap_explanation.values.shape) == 3:
            sv = shap_explanation.values[0, :, 1]
        else:
            sv = shap_explanation.values[0]
            
        feature_impacts = []
        for i, val in enumerate(sv):
            feature_impacts.append({
                "name": human_features[i],
                "impact": float(val)
            })
            
        feature_impacts.sort(key=lambda x: x["impact"], reverse=True)
        top_positive = [f for f in feature_impacts if f["impact"] > 0][:3]
        top_negative = [f for f in feature_impacts if f["impact"] < 0][::-1][:2]
        
        shap_insights = {
            "top_positive": [{"name": f["name"], "impact_percent": round(f["impact"] * 100, 1)} for f in top_positive],
            "top_negative": [{"name": f["name"], "impact_percent": round(abs(f["impact"]) * 100, 1)} for f in top_negative]
        }
        
        assessments_collection.update_one(
            {"_id": a["_id"]},
            {"$set": {"shap_insights": shap_insights}}
        )
        print(f"Updated assessment {a['_id']}")
    except Exception as e:
        print(f"Error on assessment {a['_id']}: {e}")

print("Backfill complete.")
