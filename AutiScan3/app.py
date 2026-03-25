from flask import Flask, render_template, request
import pickle

app = Flask(__name__)

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

# -------- ML PREDICTION --------

@app.route("/predict", methods=["POST"])
def predict():
    data = []

    # collect answers
    for i in range(10):
        val = request.form.get(f"q{i}")

        if val is None or val == "":
            val = 0

        data.append(int(val))

    # 🔥 Ensemble Prediction
    lr_prob = lr_model.predict_proba([data])[0][1]
    nn_prob = nn_model.predict_proba([data])[0][1]
    rf_prob = rf_model.predict_proba([data])[0][1]

    final_prob = (lr_prob + nn_prob + rf_prob) / 3

    percent = round(final_prob * 100, 2)

    # 🎯 Spectrum logic
    if percent < 30:
        spectrum = "Low Risk"
    elif percent < 60:
        spectrum = "Moderate Risk"
    else:
        spectrum = "High Risk"

    confidence = round(abs(final_prob - 0.5) * 200, 2)

    return render_template(
        "result.html",
        percent=percent,
        spectrum=spectrum,
        confidence=confidence
    )

if __name__ == "__main__":
    app.run(debug=True)