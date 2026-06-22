import pickle
import pandas as pd
import shap

lr, nn, rf = pickle.load(open("model/autism_model.pkl", "rb"))

feature_cols = [
    'A1_Score','A2_Score','A3_Score','A4_Score','A5_Score',
    'A6_Score','A7_Score','A8_Score','A9_Score','A10_Score',
    'age','gender','jundice','austim'
]

df = pd.DataFrame([[1, 0, 1, 1, 0, 0, 1, 1, 0, 0, 5, 1, 0, 0]], columns=feature_cols)

explainer = shap.TreeExplainer(rf)
# shap_values = explainer.shap_values(df)
expl = explainer(df)

print("Type of expl:", type(expl))
print("Type of expl.values:", type(expl.values))
print("Shape of expl.values:", expl.values.shape)
if len(expl.values.shape) == 3:
    print("Class 1 values:", expl.values[0, :, 1])
else:
    print("Values:", expl.values)
