import pandas as pd
import pickle
import os

from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

# -----------------------------
# 1. Create model folder
# -----------------------------
os.makedirs("model", exist_ok=True)

# -----------------------------
# 2. Load CSV dataset
# -----------------------------
data = pd.read_csv("autism_child_data.csv")



# -----------------------------
# 🔥 3. Encoding categorical features (PASTE HERE)
# -----------------------------
# CLEAN values first
data['gender'] = data['gender'].str.lower().str.strip()
data['jundice'] = data['jundice'].str.lower().str.strip()
data['austim'] = data['austim'].str.lower().str.strip()

# MAP properly
data['gender'] = data['gender'].map({'m':1, 'male':1, 'f':0, 'female':0})
data['jundice'] = data['jundice'].map({'yes':1, 'no':0})
data['austim'] = data['austim'].map({'yes':1, 'no':0})

data = data.dropna()
print(data.isnull().sum())

# -----------------------------
# 4. Preprocessing (UPDATED)
# -----------------------------
X = data[['A1_Score','A2_Score','A3_Score','A4_Score','A5_Score',
          'A6_Score','A7_Score','A8_Score','A9_Score','A10_Score',
          'age','gender','jundice','austim']]

y = data['Class/ASD'].map({'YES':1,'NO':0})

# -----------------------------
# 4. Train-test split
# -----------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# -----------------------------
# 5. Logistic Regression (TUNED)
# -----------------------------
lr_pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("lr", LogisticRegression(max_iter=1000))
])

lr_params = {
    "lr__C": [0.1, 1, 10]
}

lr_grid = GridSearchCV(lr_pipeline, lr_params, cv=5)
lr_grid.fit(X_train, y_train)

best_lr = lr_grid.best_estimator_

# -----------------------------
# 6. Neural Network (MLP)
# -----------------------------
mlp_pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("mlp", MLPClassifier(
        hidden_layer_sizes=(32, 16),
        activation="relu",
        max_iter=1000,
        random_state=42
    ))
])

mlp_pipeline.fit(X_train, y_train)

# -----------------------------
# 7. Random Forest (Extra boost 🔥)
# -----------------------------
rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
rf_model.fit(X_train, y_train)

# -----------------------------
# 8. Evaluation
# -----------------------------
print("LR Accuracy:", accuracy_score(y_test, best_lr.predict(X_test)))
print("MLP Accuracy:", accuracy_score(y_test, mlp_pipeline.predict(X_test)))
print("RF Accuracy:", accuracy_score(y_test, rf_model.predict(X_test)))

# -----------------------------
# 9. Save ALL models (Ensemble)
# -----------------------------
pickle.dump((best_lr, mlp_pipeline, rf_model),
            open("model/autism_model.pkl", "wb"))

print("🔥 Ensemble model saved successfully!")