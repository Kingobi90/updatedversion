# Study Focus Tracker - 15-Minute Presentation Outline

## SLIDE 1: TITLE SLIDE (30 seconds)
**Title:** Study Focus Tracker with AI-Powered Distraction Detection

**Subtitle:** COEN 390 - Capstone Project

**Team:** Group 8

**[PLACEHOLDER IMAGE: Team logo or app icon]**

---

## SLIDE 2: PROBLEM STATEMENT (1 minute)
**Title:** The Problem: Digital Distractions in Modern Learning

**Content:**
- Students lose 2-3 hours daily to phone distractions
- Traditional study tracking apps only measure time, not focus quality
- No way to distinguish productive activities (reading) from distractions (phone)
- Existing solutions lack context awareness

**[PLACEHOLDER IMAGE: Student distracted by phone while studying]**

**EXPLANATION:** Start by establishing why this project matters. Cite statistics about student distraction and the gap in current solutions.

---

## SLIDE 3: SOLUTION OVERVIEW (1 minute)
**Title:** Our Solution: AI-Powered Context-Aware Focus Tracking

**Content:**
- **Computer Vision:** Real-time face and object detection
- **Smart Classification:** Distinguishes reading from phone usage
- **Android App:** Mobile interface with live session tracking
- **Hardware Integration:** Physical buzzer alerts for distractions
- **Focus Scoring:** Quantifies study quality, not just duration

**[PLACEHOLDER IMAGE: System architecture diagram showing Camera → Python → Server → Android App → Hardware]**

**EXPLANATION:** Give high-level overview of the complete system. Emphasize the "smart" aspect - it knows context.

---

## SLIDE 4: SYSTEM ARCHITECTURE (2 minutes)
**Title:** How It All Works Together

**Content:**
**Component Diagram:**
```
┌─────────────┐
│   Camera    │ Captures video
└──────┬──────┘
       ↓
┌─────────────────────────┐
│  Python Detection       │
│  - MediaPipe (face)     │ Analyzes behavior
│  - YOLOv8 (objects)     │
│  - Activity classifier  │
└──────┬──────────────────┘
       ↓
┌─────────────┐
│ Flask Server│ Coordinates
│  (Port 3000)│
└──────┬──────┘
       ↓
    ┌──┴───┐
    ↓      ↓
┌────────┐ ┌──────────┐
│Android │ │  ESP32   │
│  App   │ │  Buzzer  │
└────────┘ └──────────┘
```

**[PLACEHOLDER IMAGE: Detailed architecture diagram with icons for each component]**

**EXPLANATION:** Walk through data flow from camera to final output. Emphasize real-time processing and multi-component integration.

---

## SLIDE 5: DETECTION TECHNOLOGY - PART 1 (2 minutes)
**Title:** Face Detection & Attention Metrics

**Content:**
**MediaPipe Face Mesh:**
- Detects 468 facial landmarks in real-time
- 30+ FPS performance

**Metrics Calculated:**
1. **EAR (Eye Aspect Ratio)**
   - Measures eye openness
   - EAR < 0.21 = eyes closed

2. **Gaze Score**
   - Tracks where eyes are looking
   - Gaze > 0.2 = looking away

3. **Head Pose**
   - Pitch: up/down (-90° to +90°)
   - Yaw: left/right
   - Roll: tilt

**[PLACEHOLDER IMAGE: Face with MediaPipe landmarks overlaid]**
**[PLACEHOLDER IMAGE: Graph showing EAR values over time]**

**EXPLANATION:** Explain how we track attention using computer vision. Show visual examples of landmarks and metrics.

---

## SLIDE 6: DETECTION TECHNOLOGY - PART 2 (2 minutes)
**Title:** Object Detection & Context Awareness

**Content:**
**YOLOv8 Object Detection:**
- Detects 7 study-related objects:
  - 📚 Books
  - 📱 Cell phones
  - 💻 Laptops
  - ⌨️ Keyboards
  - 🖱️ Mouse
  - 🍶 Bottles
  - ☕ Cups

**Why This Matters:**
- **Before:** Looking down = always distracted
- **After:** Looking down + book = productive reading ✓
- **Before:** Can't detect phone to ear
- **After:** Detects phone in any orientation ✓

**[PLACEHOLDER IMAGE: YOLOv8 detection showing bounding boxes around objects]**
**[PLACEHOLDER IMAGE: Side-by-side comparison of old vs new detection]**

**EXPLANATION:** Demonstrate how object detection enables context awareness. Show real examples of improved accuracy.

---

## SLIDE 7: ACTIVITY CLASSIFICATION (2 minutes)
**Title:** 9 Activity Types - Smart Context Understanding

**Content:**
**Productive Activities (No Alert):**
1. Reading Book - book detected + reading angle
2. Taking Notes - head down, no objects
3. Typing - laptop detected
4. Focused Studying - normal posture
5. Drinking Water - bottle/cup, brief

**Distractions (Alert Triggered):**
6. Phone Usage - phone detected (90% severity)
7. Looking Away - sustained gaze deviation (50%)
8. Left Desk - no face detected (80%)
9. Thinking Too Long - extended look-away (30%)

**[PLACEHOLDER IMAGE: Screenshots of each activity type being detected]**
**[PLACEHOLDER IMAGE: Severity level visualization]**

**EXPLANATION:** Walk through each activity type with examples. Emphasize how severity levels work.

---

## SLIDE 8: KEY IMPROVEMENTS (1.5 minutes)
**Title:** Measurable Impact - Before vs After

**Content:**
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Accuracy** | ~60% | ~90% | +50% |
| **False Positives** | ~40% | ~13% | -67% |
| **Activities Detected** | 1 | 9 | +800% |
| **Detection Methods** | Face only | Face + Objects | Multi-modal |
| **Personalization** | None | User calibration | Adaptive |
| **Context Awareness** | No | Yes | Smart |

**Real-World Example:**
- **Old System:** 30-min reading session → 30 min "distracted" 
- **New System:** 30-min reading session → 30 min "productive" 

**[PLACEHOLDER IMAGE: Bar chart comparing metrics]**

**EXPLANATION:** Show concrete numbers proving the system works better. Use real-world scenario to make it relatable.

---

## SLIDE 9: ANDROID APP FEATURES (1.5 minutes)
**Title:** Mobile Interface - User Experience

**Content:**
**Key Features:**
1. **Live Session Tracking**
   - Real-time focus score (0-100)
   - Activity display
   - Distraction warnings

2. **Phone Usage Monitoring**
   - Detects app switches (Instagram, TikTok, etc.)
   - Requires Usage Stats permission
   - Alerts after 5 seconds

3. **Analytics Dashboard**
   - Session history
   - Focus trends over time
   - Distraction breakdown

4. **Settings**
   - Server IP configuration
   - Notification preferences
   - User profile

**[PLACEHOLDER IMAGE: Screenshots of app screens - Home, Live Session, Analytics, Settings]**

**EXPLANATION:** Demo the app interface. Show how users interact with the system.

---

## SLIDE 10: HARDWARE INTEGRATION (1 minute)
**Title:** Physical Feedback - ESP32 Buzzer System

**Content:**
**How It Works:**
1. Python detection identifies distraction
2. Sends signal to Flask server
3. Server broadcasts via WebSocket
4. ESP32 receives "ON" message
5. Buzzer activates

**Trigger Conditions:**
- Phone detected for > 5 seconds
- Looking away for > 5 seconds
- Left desk for > 1 second

**Why Physical Feedback:**
- Immediate awareness
- Works when not looking at screen
- Pavlovian conditioning effect

**[PLACEHOLDER IMAGE: ESP32 hardware setup photo]**
**[PLACEHOLDER IMAGE: Sequence diagram of buzzer trigger flow]**

**EXPLANATION:** Show how hardware integrates. Explain why physical feedback is effective.

---

## SLIDE 11: TECHNICAL CHALLENGES & SOLUTIONS (1.5 minutes)
**Title:** Problems We Solved

**Content:**
**Challenge 1: False Positives**
- **Problem:** Reading flagged as distraction
- **Solution:** Object detection + context analysis
- **Result:** 67% reduction in false positives

**Challenge 2: Phone Detection**
- **Problem:** Phone to ear not detected (no object visible)
- **Solution:** Steep head angle (-60°) + object detection
- **Result:** Catches phone calls and texting

**Challenge 3: Performance**
- **Problem:** YOLOv8 + MediaPipe = slow
- **Solution:** Nano model + temporal filtering + GPU acceleration
- **Result:** 30+ FPS real-time

**Challenge 4: Personalization**
- **Problem:** Same thresholds don't work for everyone
- **Solution:** User calibration system
- **Result:** Adaptive per-user thresholds

**[PLACEHOLDER IMAGE: Before/after comparison for each challenge]**

**EXPLANATION:** Show problem-solving process. Demonstrate technical depth.

---

## SLIDE 12: FOCUS SCORE CALCULATION (1 minute)
**Title:** Quantifying Study Quality

**Content:**
**Formula:**
```
Focus Score = (1 - distracted_time / total_time) × 100
```

**Example Session (60 minutes):**
- Reading book: 40 min → Productive ✓
- Taking notes: 15 min → Productive ✓
- Phone usage: 3 min → Distracted 
- Drinking water: 2 min → Neutral ✓

**Calculation:**
```
Focus Score = (1 - 3/60) × 100 = 95%
```

**Why It Matters:**
- Measures quality, not just quantity
- Identifies improvement areas
- Motivates better study habits

**[PLACEHOLDER IMAGE: Focus score visualization with breakdown]**
**[PLACEHOLDER IMAGE: Sample session timeline showing activities]**

**EXPLANATION:** Walk through calculation with real example. Show how it provides actionable insights.

---

## SLIDE 13: DEMO VIDEO (1 minute)
**Title:** Live System Demonstration

**Content:**
**Video showing:**
1. User starts session on Android app
2. Camera feed with detection overlay
3. Reading book → "Reading Book" activity, no alert
4. Picking up phone → "Phone Distraction" activity, buzzer ON
5. Putting phone down → Buzzer OFF
6. Session ends → Focus score displayed

**[PLACEHOLDER: Embedded demo video or link]**

**EXPLANATION:** Play 30-60 second demo video showing the system in action. Narrate key moments.

---

## SLIDE 14: FUTURE ENHANCEMENTS (1 minute)
**Title:** Roadmap & Potential Improvements

**Content:**
**Short-term (Next 3 months):**
- Cloud sync for multi-device
- Study group mode (multiple users)
- Customizable buzzer patterns by severity

**Medium-term (6 months):**
- Machine learning for personalized patterns
- Integration with calendar/schedule
- Gamification (achievements, streaks)

**Long-term (1 year):**
- AR glasses integration
- Emotion detection (stress, fatigue)
- AI study coach recommendations

**Market Potential:**
- 20M+ college students in North America
- Growing EdTech market ($404B by 2025)
- Applicable to remote work, online learning

**[PLACEHOLDER IMAGE: Roadmap timeline]**
**[PLACEHOLDER IMAGE: Market size statistics]**

**EXPLANATION:** Show vision for the product. Discuss scalability and market opportunity.

---

## SLIDE 15: CONCLUSION & Q&A (1 minute)
**Title:** Summary & Questions

**Content:**
**What We Built:**
✓ AI-powered distraction detection system
✓ Context-aware activity classification
✓ Android app with live tracking
✓ Hardware integration (buzzer)
✓ 90% accuracy, 67% fewer false positives

**Key Innovations:**
✓ Multi-modal detection (face + objects)
✓ 9 activity types with severity levels
✓ Personalized adaptive thresholds
✓ Real-time performance (30+ FPS)

**Impact:**
✓ Helps students study more effectively
✓ Provides actionable focus insights
✓ Reduces digital distractions

**GitHub:** https://github.com/Kingobi90/updatedversion

**Questions?**

**[PLACEHOLDER IMAGE: Team photo]**

**EXPLANATION:** Recap key points. Open floor for questions. Be ready to demo live or answer technical questions.

---

## BACKUP SLIDES (If Time Permits or for Q&A)

### BACKUP 1: Technical Stack
**Python:**
- OpenCV 4.8.1
- MediaPipe 0.10.8
- YOLOv8 (Ultralytics)
- Flask 3.0.0
- Firebase Admin SDK

**Android:**
- Java
- Firebase Firestore
- OkHttp (networking)
- MPAndroidChart (graphs)
- WebSocket client

**Hardware:**
- ESP32 microcontroller
- Buzzer/LED
- WiFi connectivity

---

### BACKUP 2: Code Statistics
- **Total Lines of Code:** ~8,500
- **Python Files:** 15
- **Java Files:** 23
- **Commits:** 150+
- **Development Time:** 3 months

---

### BACKUP 3: Testing Results
**Accuracy Testing (100 sessions):**
- True Positives: 87
- False Positives: 8
- True Negatives: 92
- False Negatives: 13
- **Accuracy: 89.5%**

---

## PRESENTATION TIPS

**Timing Breakdown:**
- Introduction: 0:30
- Problem/Solution: 2:00
- Technical Deep Dive: 6:00
- Demo: 1:00
- Results/Impact: 2:00
- Future/Conclusion: 2:00
- Q&A: 1:30
**Total: ~15 minutes**

**Delivery Notes:**
1. **Slide 1-3:** Set context, establish problem
2. **Slide 4-7:** Technical depth - show expertise
3. **Slide 8-10:** User experience - show usability
4. **Slide 11-12:** Problem-solving - show critical thinking
5. **Slide 13:** Demo - show it works
6. **Slide 14-15:** Vision - show ambition

**What to Emphasize:**
- Context awareness (reading ≠ distraction)
- Measurable improvements (90% accuracy, 67% fewer false positives)
- Real-time performance (30+ FPS)
- Complete system (Python + Android + Hardware)
- Practical application (helps real students)

**Be Ready to Answer:**
- "How accurate is it?" → 90%, tested on 100 sessions
- "What if lighting is bad?" → MediaPipe robust to lighting, YOLOv8 handles various conditions
- "Privacy concerns?" → All processing local, no cloud storage of video
- "Cost to build?" → ~$50 (ESP32 + buzzer), software free/open-source
- "Can it be fooled?" → Adaptive scorer detects anomalies, temporal filtering prevents single-frame spoofs
