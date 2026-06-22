# AutiScan Games Section Viva Prep Guide

This document covers all details regarding the **Digital Therapy Games** implemented in AutiScan. It breaks down the therapeutic purpose, technical implementation, and sample Viva questions for the games section.

---

## 1. Summary of the Games & Therapy Targets

AutiScan includes 6 targeted digital therapy games designed to address specific developmental areas affected by Autism Spectrum Disorder (ASD):

| Game Name | Endpoint | Therapeutic Target | Mechanics & Core Concept |
| :--- | :--- | :--- | :--- |
| **Eye Contact & Focus** | `/game/eye` | Visual tracking, sustained attention, and gaze control. | A moving target dot jumps to random coordinates. The child must track and click it. Speed adapts in real-time. |
| **Speech & Sound Therapy** | `/game/speech` | Phonetics, vocabulary articulation, and verbal communication. | Displays objects (e.g. apple, car) and plays audio. Child uses the microphone to read the word, verified via speech-to-text. |
| **Emotion Recognition** | `/game/emotion` | Emotional literacy, facial expression mapping, and affective empathy. | Displays AI-generated images of children expressing 10 distinct emotions. Child identifies the correct emotion. |
| **Social Scenarios** | `/game/social` | Social stories, situational safety, and relational consequences. | 10 interactive scenarios (e.g., hospital visit, sharing at the park). Presents safe/social vs. unsafe/anti-social choices. |
| **Transition Timer** | `/game/flex` | Cognitive flexibility, routine transitions, and impulse control. | A fast-paced game where rules change dynamically based on timers, teaching children to adapt to rules. |
| **Memory Match** | `/game/memory` | Working memory, cognitive processing, and visual recall. | Flip cards with friendly sensory symbols to locate pairs, tracking attempts and matches. |

---

## 2. Technical Implementation details

### A. Saving Game Progress (`/api/save_game` Endpoint)
* **Storage Logic**:
  1. In the web interface, the parent selects which child is currently playing from the dashboard. The child's MongoDB `ObjectId` is saved in the browser's `localStorage` as `autiscan_active_child`.
  2. When any game completes, the frontend JavaScript reads this ID from `localStorage`:
     ```javascript
     let childId = localStorage.getItem('autiscan_active_child');
     ```
  3. If a valid `childId` is present, the script makes an asynchronous `fetch()` API POST request to the Flask backend:
     ```javascript
     fetch('/api/save_game', {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify({
         child_id: childId,
         game_name: "Eye Contact & Focus",
         score: score + " / " + appearances
       })
     });
     ```
  4. Flask's `/api/save_game` endpoint validates the user's login session and inserts the document into the MongoDB `games` collection, linked via `child_id`.
  5. The parent or doctor dashboard retrieves these records to display progress charts (using libraries like Chart.js or raw metrics).

### B. Speech Recognition Engine (Speech Therapy Game)
* **Client-Side Processing**: 
  Instead of utilizing expensive or latency-prone server-side cloud APIs, the game uses the browser's native **Web Speech API** via JavaScript:
  ```javascript
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = new SpeechRecognition();
  recognition.lang = 'en-US';
  ```
* **Pros**: Completely free, low latency (runs locally in browser), and respects user privacy by not transmitting raw audio files to a third-party server.

### C. Adaptive Game Speed (Eye Contact Game)
* **Feedback Loop**:
  The Eye Contact game adjusts its interval speed ($I$) dynamically based on user response:
  * When a dot is clicked, the reaction time ($T_{\text{react}} = \text{Time}_{\text{click}} - \text{Time}_{\text{appearance}}$) is calculated.
  * If $T_{\text{react}} < 1.2\text{s}$ (Fast): $I = \max(400\text{ms}, I - 400\text{ms})$ $\rightarrow$ The dot speeds up to challenge the child.
  * If the dot jumps before the child clicks it (Missed): $I = \min(3.5\text{s}, I + 300\text{ms})$ $\rightarrow$ The dot slows down to help the child re-focus without causing frustration.

---

## 3. Likely Examiner Questions & Answers

### Q1: What is the scientific basis for using digital games in autism therapy?
* **Answer**: Children with autism often respond well to predictable, structured visual interfaces. Digital therapies (gamification) provide a safe, low-pressure environment to practice eye contact, emotional recognition, and social situations. The gamified loop of immediate positive reinforcement (stars, confetti, sound feedback) maintains engagement, which is essential for repetitive therapeutic practice.

### Q2: How did you implement voice recognition in the Speech Therapy game? Did you use a paid API?
* **Answer**: No, I did not use a paid server API. I used the native browser-based **Web Speech API** (`window.SpeechRecognition` / `window.webkitSpeechRecognition`). When the user speaks, the browser's built-in engine performs local speech-to-text processing, returning the transcribed text string to our JavaScript code, where we verify if it matches the target word.

### Q3: How are child profile scores tracked?
* **Answer**: We link game sessions to children using MongoDB's document relationships. When a parent registers a child, MongoDB assigns a unique `_id` (ObjectId). When a child plays a game, the frontend retrieves that child's ID from local storage and posts it to our backend. The backend stores it in a `games` collection with fields: `{ child_id, game_name, score, date }`. We can then query this collection for a specific `child_id` to render progress graphs.

### Q4: Explain what is meant by "Adaptive Gameplay" in the Eye Contact game.
* **Answer**: Children with autism have varying levels of motor control and processing speed. If a game is too fast, they get discouraged; if it is too slow, they lose interest. The game monitors their clicking speed. If they click quickly, the game speeds up. If they miss a target, the game automatically slows down to give them more time, stabilizing at a pace that keeps them engaged.

### Q5: How are social skills taught in the Social Scenarios game?
* **Answer**: The game uses "Social Stories" (a validated clinical method developed by Carol Gray). It presents scenarios like "Visiting a Doctor" or "Sharing at the Playground". For each scenario, it displays a positive choice and a negative choice. When selected, the game doesn't just say "correct" or "incorrect"—it explains the relational consequence (e.g., "Doctors are our friends! Running away makes it hard for them to help us keep you safe"), reinforcing why the positive choice is beneficial.
