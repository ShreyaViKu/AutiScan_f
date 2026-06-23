# AutiScan Comprehensive Viva Question Bank

This document contains a comprehensive bank of technical questions that an examiner might ask during your Viva, grouped by category. Each question is explained with an easy-to-understand answer followed by the technical reasoning.

---

## Category 1: Project Concept & Purpose

### Q1: What is the main purpose of AutiScan?
* **Easy Answer**: AutiScan is a digital platform designed for early autism screening in children and providing interactive therapeutic games. It also features a smart AI chatbot named Aura to guide parents and doctors.
* **Technical Explanation**: It is a clinical decision support system. It uses machine learning classification algorithms to predict the risk of Autism Spectrum Disorder (ASD) based on behavioral inputs, provides Explainable AI (XAI) reports using SHAP, offers personalized digital therapies (serious games) based on the screening answers, and uses Retrieval-Augmented Generation (RAG) to serve factual information via an LLM.

---

## Category 2: Machine Learning & Explainable AI (XAI)

### Q2: What is an "Ensemble Model" and why did you use it?
* **Easy Answer**: Instead of relying on just one AI model which might make mistakes, we combine three different models. We average their predictions to get a balanced, more accurate result.
* **Technical Explanation**: An ensemble combines multiple classifiers to improve robustness and reduce prediction variance. AutiScan uses a **soft voting ensemble** containing:
  1. **Logistic Regression**: A linear classifier that uses a logistic function to model binary outcomes.
  2. **Multi-layer Perceptron (MLP)**: A feedforward neural network with two hidden layers (size 32 and 16) using ReLU activation.
  3. **Random Forest**: An ensemble of 100 decision trees.
  The final probability is the arithmetic mean of the probabilities predicted by the three models.

### Q3: What is "Feature Scaling" and why did you use `StandardScaler`?
* **Easy Answer**: Different inputs have different ranges (e.g., age is 1–18 years, while scores are 0 or 1). Feature scaling normalizes these inputs so the neural network doesn't give extra importance to larger numbers.
* **Technical Explanation**: Algorithms like Gradient Descent in MLP and regularization in Logistic Regression are sensitive to feature scales. `StandardScaler` standardizes features by removing the mean and scaling to unit variance ($z = \frac{x - \mu}{\sigma}$), ensuring all features contribute equally. (Decision trees in Random Forest are scale-invariant, but scaling is vital for the other two models in our ensemble).

### Q4: What is SHAP and why is it important in medical/clinical screening?
* **Easy Answer**: Standard machine learning models are "black boxes"—they give a score but don't explain *why*. SHAP tells the parent exactly which answers increased the risk score and which ones kept it low.
* **Technical Explanation**: **SHAP (SHapley Additive exPlanations)** is an explainability framework based on cooperative game theory. It calculates the *Shapley values* for each feature of a specific input. The value represents the change in expected model prediction when that feature is present versus absent. This turns our predictive model into an **Explainable AI (XAI)** tool, which is critical in healthcare settings for transparency and clinical trust.

---

## Category 3: RAG (Retrieval-Augmented Generation) & Chatbot

### Q5: What is RAG and why is it better than fine-tuning a model?
* **Easy Answer**: Fine-tuning means retraining an AI on new documents, which is expensive and makes the AI "hallucinate" (make up facts). RAG is like giving the AI an open book: we search our local database for the right paragraphs, paste them into the prompt, and ask the AI to answer using *only* that text.
* **Technical Explanation**: RAG stands for **Retrieval-Augmented Generation**. 
  1. It decouples knowledge storage from model parameters.
  2. It avoids computational training costs.
  3. It prevents hallucinations by grounding the LLM's responses in verified source documents.
  4. It allows updating the system's knowledge base instantly by just updating a JSON file, without retraining.

### Q6: How does the Vector Search work in your RAG pipeline?
* **Easy Answer**: 
  1. We parse our FAQ pages and break them into paragraphs.
  2. We turn these paragraphs into lists of numbers (called vector embeddings) using Google's embedding model.
  3. When a user asks a question, we turn their question into a list of numbers too.
  4. We compare the user's list against all our paragraphs using vector math (Cosine Similarity) in a fraction of a millisecond to find the best match.
* **Technical Explanation**:
  * **Offline Step**: `build_rag_index.py` chunks HTML files and uses `models/gemini-embedding-2` to generate 3072-dimensional vectors. It saves them to `rag_index.json`.
  * **Online Step**: When Flask starts, it loads the vectors and pre-normalizes them. When a user queries, the query vector is normalized.
  * **Similarity Math**: The dot product of the pre-normalized document matrix and the normalized query vector yields the **Cosine Similarity**:
    $$\text{Similarity} = \text{Matrix}_{\text{docs}} \cdot \vec{Q}_{\text{normalized}}$$
  * We sort the scores, filter by a similarity threshold ($>0.35$), and append the top 3 matches to the system prompt of `gemini-flash-lite-latest`.

---

## Category 4: Database & Backend Architecture

### Q7: Why did you use MongoDB (NoSQL) instead of SQL (like MySQL)?
* **Easy Answer**: SQL databases force you to use rigid tables with fixed columns. In AutiScan, children's profiles, game scores, and assessment results have dynamic fields (different games track different score formats). MongoDB stores data as flexible, JSON-like documents, making it much easier to store and query variable data.
* **Technical Explanation**: NoSQL document stores provide horizontal scalability and a schema-less structure. Since our clinical assessment records, game sessions (different games write different metrics), and user roles vary in structure, MongoDB is ideal. It eliminates the need for expensive multi-table joins and schema migrations.

### Q8: What is the database schema? How are collections linked?
* **Easy Answer**: We have collections for `users`, `children`, `assessments`, and `games`. We link them using ID references. For example, every child document stores their parent's user ID (`parent_id`), and every game score document stores the child's ID (`child_id`).
* **Technical Explanation**: It is a **Referenced Data Model**:
  * **`users`**: `{ _id (ObjectId), name, email, role ("parent"/"doctor") }`
  * **`children`**: `{ _id (ObjectId), name, age, gender, parent_id (string reference) }`
  * **`assessments`**: `{ _id, child_id, spectrum, probability, shap_insights, date }`
  * **`games`**: `{ _id, child_id, game_name, score, date }`

---

## Category 5: Deployment, Security & Google OAuth

### Q9: Explain how Google Sign-In (OAuth 2.0) works in your app.
* **Easy Answer**: 
  1. The user clicks "Continue with Google".
  2. The app redirects their browser to Google's server.
  3. Google authenticates the user and sends a temporary code back to our callback page.
  4. Our backend takes that code and sends it back to Google in exchange for a secure token containing the user's name and email.
* **Technical Explanation**: We use the **Authorization Code Flow**:
  * Frontend redirects to Google with requested scopes (`openid email profile`).
  * Google redirects back to `/authorize/google` with an authorization code.
  * Backend uses `Authlib` to request an access token via an HTTP POST request.
  * Backend parses the ID token to extract claims (name, email) and logs the user in.

### Q10: What is `ProxyFix` and why did you have to use it in production?
* **Easy Answer**: Hugging Face Spaces runs our app behind a reverse proxy (a middleman server). Internally, the app runs on plain `http`, but users access it externally via secure `https`. Google OAuth requires redirect URIs to match exactly. `ProxyFix` tells Flask to trust the headers sent by the middleman, so Flask knows it is running on `https`, preventing authentication crashes.
* **Technical Explanation**: A reverse proxy terminates SSL and forwards requests to Flask over HTTP, altering headers. `ProxyFix` middleware intercepts incoming WSGI requests and updates the WSGI environment variables (like `wsgi.url_scheme` and `HTTP_HOST`) using the proxy headers (`X-Forwarded-Proto` and `X-Forwarded-Host`). This ensures that `url_for()` constructs correct external `https` links during OAuth callback validation.

### Q11: Why did you use `target="_top"` on the Google Login button?
* **Easy Answer**: Hugging Face displays our app inside an `iframe` (a website window inside another website). Google blocks sign-ins inside iframes to prevent "clickjacking" (hackers tricking users into clicking buttons). `target="_top"` forces the sign-in page to break out of the iframe and load in the top main window.
* **Technical Explanation**: Google sets the HTTP response header `X-Frame-Options: DENY` on its sign-in pages to prevent clickjacking attacks. Using `target="_top"` on the anchor tag target property forces the browser to load the redirect target in the topmost window context, avoiding iframe policy violations.

---

## Category 6: Interactive Games

### Q12: How does the Voice Recognition work in the Speech Therapy game?
* **Easy Answer**: We do not use any paid cloud services. Instead, we use the browser's built-in voice engine called **Web Speech API** (`window.SpeechRecognition`). It does speech-to-text directly on the child's device, which makes it 100% free, private, and extremely fast.
* **Technical Explanation**: The application uses the HTML5 client-side Web Speech API. We instantiate a browser-native listener that captures microphone audio, runs heuristic phonetic mapping locally on the user's browser engine, and outputs a transcript string. We clean this string and perform a text inclusion check against the target therapeutic word.

### Q13: Explain how "Adaptive Speed" works in the Eye Contact game.
* **Easy Answer**: The game measures how fast the child clicks. If they are quick, the target dot speeds up to challenge them. If they miss a dot, the game automatically slows down to give them more time, ensuring they stay focused and don't get frustrated.
* **Technical Explanation**: It is an adaptive difficulty controller. We track the timestamp of dot rendering versus click trigger. If reaction time is fast ($<1.2\text{s}$), the move interval decreases. If the interval timer expires without a click, it registers a miss and increases the interval (caps set between $400\text{ms}$ and $3.5\text{s}$). This keeps the child within their "Zone of Proximal Development."
