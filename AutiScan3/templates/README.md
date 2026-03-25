# AutiScan — Early Autism Screening Platform

A complete multi-page website for autism awareness, education, and early screening.

---

## 📁 Project Structure

```
autiscan/
├── index.html              # Homepage with spectrum visualizer
├── about.html              # About Autism knowledge hub
├── screening.html          # Interactive screening quiz tool
├── awareness.html          # Autism awareness page
├── style.css               # Global stylesheet (all pages)
├── images/                 # Add your own images here
│   ├── homepage.jpeg       # Homepage hero image (optional)
│   └── asd.jpeg            # About page image (optional)
└── autism/                 # Informational sub-pages
    ├── what-is-autism.html
    ├── autism-screening.html
    ├── autism-diagnosis.html
    ├── causes-of-autism.html
    ├── signs-and-symptoms.html
    └── vaccines-and-autism.html
```

---

## 🚀 How to Run

### Option 1 — Open directly in browser (simplest)
Just open `index.html` in any modern browser. All pages and navigation work locally.

### Option 2 — Local dev server (recommended for best experience)

**Using Python (built-in):**
```bash
cd autiscan
python3 -m http.server 8080
# Visit: http://localhost:8080
```

**Using Node.js / npx:**
```bash
cd autiscan
npx serve .
# Visit the URL shown in your terminal
```

**Using VS Code:**
Install the "Live Server" extension → right-click `index.html` → Open with Live Server.

---

## 🖼️ Adding Images (Optional)

To replace the placeholder icons with real photos:
1. Add `homepage.jpeg` and `asd.jpeg` to the `/images/` folder
2. In `index.html`, replace the `.image-placeholder` div with:
   ```html
   <img src="images/homepage.jpeg" alt="Family Support Image">
   ```
3. In `about.html`, replace similarly with `images/asd.jpeg`

---

## 📄 Pages Overview

| Page | Description |
|------|-------------|
| `index.html` | Homepage with hero, spectrum visualizer, how it works |
| `about.html` | Autism knowledge hub with myths vs facts |
| `screening.html` | Full interactive quiz: parent or self-assessment |
| `awareness.html` | Autism awareness & advocacy information |
| `autism/what-is-autism.html` | What is ASD — overview |
| `autism/autism-screening.html` | Why early screening matters |
| `autism/autism-diagnosis.html` | Diagnostic process explained |
| `autism/causes-of-autism.html` | Genetics & environmental factors |
| `autism/signs-and-symptoms.html` | Early warning signs |
| `autism/vaccines-and-autism.html` | Vaccine myth debunked |

---

## ⚠️ Disclaimer

This tool provides informational insights only. It is **not a medical diagnosis**. Always consult a qualified healthcare professional for a comprehensive evaluation.

© 2025 AutiScan
