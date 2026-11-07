# StudyWise AI | Google Stitch UI Design Prompts & Specifications
*Production-ready prompt engineering for [stitch.withgoogle.com](https://stitch.withgoogle.com)*
*Based on [StudyWise.md](file:///home/meghapant/Projects/PDF/StudyWise.md)*

---

## 🎨 Global Design System & Style Tokens (DESIGN.md)

Use the following design system prompt or tokens when creating the project on Stitch:

```yaml
---
name: StudyWise AI Assessment Design System
colors:
  primary: '#4F46E5'              # Indigo Accent
  primary-hover: '#4338CA'
  primary-light: '#EEF2FF'
  secondary: '#0F172A'            # Deep Slate Navy
  accent-success: '#10B981'       # Emerald Green for passing and correct answers
  accent-warning: '#F59E0B'       # Amber for timer warning & flagged questions
  accent-danger: '#EF4444'        # Crimson for incorrect answers & urgency
  surface: '#FFFFFF'              # Card Surface
  background: '#F8FAFC'           # Clean Canvas Neutral
  border: '#E2E8F0'               # Subtle Divider
  text-primary: '#0F172A'
  text-muted: '#64748B'
typography:
  fontFamily: 'Inter, sans-serif'
  codeFont: 'JetBrains Mono, monospace'
  headline-xl: { fontSize: '28px', fontWeight: '800', lineHeight: '36px' }
  headline-lg: { fontSize: '22px', fontWeight: '700', lineHeight: '28px' }
  headline-md: { fontSize: '18px', fontWeight: '600', lineHeight: '24px' }
  body-md: { fontSize: '15px', fontWeight: '400', lineHeight: '22px' }
  body-sm: { fontSize: '13px', fontWeight: '400', lineHeight: '18px' }
  badge: { fontSize: '11px', fontWeight: '700', letterSpacing: '0.5px' }
rounded:
  sm: '6px'
  md: '10px'
  lg: '16px'
  full: '9999px'
elevation:
  card: '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)'
  hover: '0 4px 12px rgba(0,0,0,0.08)'
  active: '0 0 0 3px rgba(79, 70, 229, 0.2)'
---
```

---

## Screen 1: Assessment Dashboard & Analytics

### Target Viewport: Desktop (1280px+)

### Stitch Text Prompt:
```text
A modern, high-end SaaS assessment dashboard for "StudyWise AI" (an AI-powered exam generator platform like exam-generator.com).

Layout & Header:
- Top Sticky Navigation Bar (white background, subtle bottom border): Left features an electric lightning bolt logo with "StudyWise" in bold indigo gradient text and "AI Exam Generator" in small slate capital letters. Center has active pill navigation links: "Dashboard" (active, soft indigo background), "Create Exam", "Question Bank", "Take Exam", and "Export Hub". Right side has a green active status pill reading "🟢 Demo Engine" and a gear icon button for Settings.

Hero & Metrics Section:
- Page Header: Title "Assessment Dashboard" with subtitle "Create, manage, grade, and export academic exams powered by AI." and a prominent top-right primary CTA button "➕ Create New Exam" in solid indigo (#4F46E5).
- 4-Column Stat Cards Grid:
  1. Card 1: Light purple icon container with book emoji "📚", metric "12", label "Total Exams Created".
  2. Card 2: Light emerald icon container with question mark "❓", metric "148", label "Questions Generated".
  3. Card 3: Light amber icon container with notepad "📝", metric "34", label "Student Attempts".
  4. Card 4: Light blue icon container with target "🎯", metric "82.4%", label "Average Student Score".

Quick-Start Action Banners:
- 3 interactive horizontal banner cards with hover lift:
  - Banner 1: "📄 From PDF or Document" with caption "Upload syllabus or textbook chapters with intelligent OCR text extraction." and right arrow icon.
  - Banner 2: "💡 From Topic / Curriculum" with caption "Generate assessments directly from a subject prompt without uploading files." and right arrow icon.
  - Banner 3: "📋 From Pasted Notes" with caption "Paste lecture notes, study guides, or summaries to generate customized tests." and right arrow icon.

Recent Exams Management Table:
- White rounded card with header: "Recent Exams" on the left, search input box on the right ("Search exams by title or topic...").
- A clean, modern data table with columns:
  - Exam Title (e.g. "Full Stack Web Development & BCA Midterm", "Operating Systems: Process Scheduling", "Cell Biology & Genetics", "Computer Networks: OSI Model").
  - Difficulty pill badge (e.g., "MEDIUM" in soft blue, "HARD" in soft red, "EASY" in soft green).
  - Question Length ("15 Questions", "10 Questions", "20 Questions").
  - Time Limit ("45 mins", "Untimed", "30 mins").
  - Creation Date ("Nov 7, 2026", "Nov 5, 2026").
  - Action buttons grouped on each row: "🎯 Take", "📝 Edit", "📥 Export", and a red trash icon "🗑️".

Aesthetic:
- Crisp white surfaces (#FFFFFF), soft gray canvas (#F8FAFC), smooth borders (#E2E8F0), Inter typography, high legibility, clean educational SaaS look.
```

---

## Screen 2: Exam Creation Wizard

### Target Viewport: Desktop (1280px+)

### Stitch Text Prompt:
```text
A modern, two-column split Exam Creation Wizard screen for "StudyWise AI" (an assessment generation platform).

Navigation Bar:
- Top navigation bar matching the StudyWise AI brand with active pill highlighting "Create Exam".

Page Header:
- Title: "Create New Exam" with subtitle "Configure your source material and assessment parameters." and a secondary button "← Back to Dashboard".

Two-Column Grid Content:
- Left Card ("1. Source Material"):
  - Top tab switcher with 3 pills: "📄 Upload PDF" (selected), "💡 Topic / Prompt", and "📋 Paste Text".
  - Large drag-and-drop file upload zone with dashed border: Cloud upload icon, bold text "Click to upload or drag & drop", subtext "PDF or TXT documents (Max 50MB)".
  - A green/indigo summary card underneath showing an uploaded file preview:
    - File name: "📄 Operating_Systems_Silberschatz_Ch3.pdf"
    - Badges: "Total Pages: 18 • Words: 5,420 • OCR Used: Scanned Fallback"
    - Excerpt quote box: "Chapter 3: Processes. A process is a program in execution. A process is more than the program code..."

- Right Card ("2. Exam Configuration"):
  - Input field: "Exam Title (Optional)" pre-filled with "Midterm Assessment: Operating Systems Processes".
  - Two-column dropdown row:
    - Dropdown 1: "Difficulty Level" (options: Easy, Medium [selected], Hard, Mixed).
    - Dropdown 2: "Target Education Level" (options: High School, Undergraduate / College [selected], Professional).
  - Question Types & Distribution Stepper Box (soft gray panel):
    - Row 1: "🔘 Multiple Choice (MCQ)" with number input stepper set to 5.
    - Row 2: "⚖️ True / False" with number input stepper set to 3.
    - Row 3: "✏️ Short Answer" with number input stepper set to 2.
    - Row 4: "📑 Essay / Analytical" with number input stepper set to 1.
  - Two-column inputs:
    - Input 1: "Time Limit (Minutes)" set to "30" (caption: "0 for untimed test").
    - Input 2: "Passing Score (%)" set to "75".
  - Big prominent primary action button spanning full width: "✨ Generate Exam with AI" (solid indigo gradient, sparkle icon, hover shadow).

Aesthetic:
- Modern SaaS interface, crisp form inputs, pill badging, accessible contrast, clean Inter typography.
```

---

## Screen 3: Question Bank & Live Editor Studio

### Target Viewport: Desktop (1280px+)

### Stitch Text Prompt:
```text
An interactive Question Bank and Live Question Editor studio screen for "StudyWise AI".

Top Header:
- Top sticky navigation bar.
- Exam Title Header: "Question Bank: Operating Systems Midterm" with subtitle "11 Questions • 18.0 Total Points • MEDIUM • Level: Undergraduate".
- Right Header Buttons: "➕ Add Question" (secondary), "📥 Export Paper" (secondary), and a glowing primary CTA button "🎯 Start Online Exam" (solid indigo).

Main Question Cards Feed (Vertical list of structured interactive question cards):
- Card 1 (Multiple Choice Question):
  - Top bar badges: "Q1 • MULTIPLE CHOICE" in indigo pill, "1.0 pt" in amber pill, "📖 Page 4" in gray pill. Right side shows an editable points input box ("Points: 1.0").
  - Question Prompt: An editable multi-line input reading: "Which component of an operating system kernel is primarily responsible for selecting which process runs on the CPU?"
  - Options list (4 styled choices):
    - Option A: Radio circle (unselected), editable text: "Memory Management Unit"
    - Option B: Radio circle (checked, green tint highlight with "✔ CORRECT" badge), editable text: "CPU Dispatcher / Short-Term Scheduler"
    - Option C: Radio circle (unselected), editable text: "Direct Memory Access Controller"
    - Option D: Radio circle (unselected), editable text: "File System Driver"
  - Rationale Box (light blue callout box with indigo left border): "Pedagogical Explanation: The short-term scheduler or CPU dispatcher allocates the CPU among the processes in the ready queue."
  - Card Action Footer: Right-aligned buttons: "🪄 AI Regenerate" (secondary) and "🗑️ Delete" (subtle red outline).

- Card 2 (True/False Question):
  - Top bar badges: "Q2 • TRUE / FALSE", "1.0 pt", "📖 Page 8".
  - Question Prompt: "True or False: A process control block (PCB) does not store the program counter of the process."
  - Options: "[ ] True", "[✔] False (CORRECT)"
  - Explanation callout: "The PCB stores critical process state information, including the program counter and CPU registers."
  - Action buttons: "🪄 AI Regenerate", "🗑️ Delete".

- Card 3 (Short Answer with Model Rubric):
  - Top bar badges: "Q3 • SHORT ANSWER", "2.0 pts".
  - Prompt: "Explain the difference between preemptive and non-preemptive scheduling."
  - Model Response / Rubric Textarea (light green border): "Expected: Preemptive scheduling allows the OS to interrupt an executing process when a higher-priority process arrives, whereas non-preemptive requires the process to voluntarily yield CPU."
  - Action buttons: "🪄 AI Regenerate", "🗑️ Delete".

Floating Action or Top Toolbar:
- Floating "➕ Add Custom Question" button and sticky indicators.
```

---

## Screen 4: Student Exam Player (Timed Mode with Palette)

### Target Viewport: Desktop (1280px+)

### Stitch Text Prompt:
```text
An online student examination player interface for "StudyWise AI" featuring a timed assessment and question palette navigation.

Sticky Top Header Bar (full width, fixed):
- Left: Exam Title "Operating Systems Midterm Assessment" with an editable candidate name pill: "Candidate: Alex Mercer".
- Center/Right:
  - Real-time countdown timer widget (dark rounded box with clock icon "⏱️"): Displays "24:18" in high-contrast monospaced font.
  - Big prominent green action button: "Submit Exam ✔" (solid emerald #10B981).

Main Exam Layout (Two-Column Grid: 280px sidebar on left, large card area on right):
- Left Sidebar (Question Navigator Palette):
  - Header: "Question Navigator" with counter "4 of 11 Answered".
  - Legend items (horizontal pills):
    - 🟩 Green dot: "Answered"
    - 🟦 Blue dot: "Current"
    - 🟧 Amber dot: "Flagged"
    - ⬜ Gray dot: "Unanswered"
  - 5x3 Grid of numbered circular buttons (1 to 11):
    - Button 1: Green (Answered)
    - Button 2: Green (Answered)
    - Button 3: Amber (Flagged)
    - Button 4: Blue with outer ring (Current active question)
    - Button 5 to 11: Gray (Unanswered)
  - Sidebar Bottom Action: Yellow outline button "🚩 Flag for Review".

- Right Main Area (Active Question Display Card):
  - Card Header: "Question 4 of 11" (indigo bold) and points badge "1.0 Point".
  - Question Prompt: "What transition occurs when a running process requests an I/O operation?" (font-size 20px, bold dark navy).
  - 4 Large interactive radio option cards (touch-friendly, generous padding, hover state):
    - Card A: Radio unchecked, "(A) Running to Ready"
    - Card B: Radio checked (selected state with indigo border, soft indigo background tint), "(B) Running to Waiting / Blocked"
    - Card C: Radio unchecked, "(C) Waiting to Ready"
    - Card D: Radio unchecked, "(D) Ready to Terminated"
  - Bottom Navigation Control Bar:
    - Left: "← Previous" button (secondary).
    - Right: "Next →" button (primary indigo).

Aesthetic:
- Distraction-free, clean testing environment, clear visual hierarchy, accessible contrast.
```

---

## Screen 5: Auto-Graded Results & AI Evaluation Card

### Target Viewport: Desktop (1280px+)

### Stitch Text Prompt:
```text
An automated exam results and pedagogical auto-grading scorecard screen for "StudyWise AI".

Top Header:
- Title "Assessment Results" with subtitle "Automated objective scoring & AI rubric evaluation."
- Right Action Buttons: "🔄 Retake Exam", "📥 Export Results", and "Back to Dashboard".

Hero Results Scorecard Banner:
- Deep indigo gradient container (#1E1B4B to #312E81) with rounded corners and white text:
  - Left: Large circular radial score ring (gauge with emerald green arc showing 85%, large bold center text "85%").
  - Right / Body:
    - Status pill: "PASSED" in bright emerald green badge (#10B981).
    - Headline: "Outstanding Performance! 🌟" (26px, bold white).
    - Subtext: "You scored above the required passing threshold of 75% for this examination."
    - Stat summary bar (3 metrics separated by thin dividers):
      - Metric 1: "Points Earned: 15.3 / 18.0"
      - Metric 2: "Time Taken: 21m 42s"
      - Metric 3: "Passing Mark: 75%"

Detailed Question Review Section (Question-by-Question Breakdown):
- Section Title: "Detailed Question Review & Explanations"
- Review Card 1 (Correct MCQ):
  - Green left border accent, top header: "Question 1 (MCQ) • Score: 1.0 / 1.0 pts • ✔ Correct".
  - Question: "Which component of an operating system kernel is primarily responsible for selecting which process runs on the CPU?"
  - Option breakdown:
    - (A) Memory Management Unit
    - (B) CPU Dispatcher / Short-Term Scheduler [CORRECT ANSWER - SELECTED BY YOU] in soft green highlight.
  - Pedagogical explanation callout: "Explanation: The CPU dispatcher allocates CPU cycles to the selected process."

- Review Card 2 (Incorrect Question):
  - Red left border accent, top header: "Question 2 (TRUE/FALSE) • Score: 0.0 / 1.0 pts • ✖ Incorrect".
  - Candidate chosen answer in red strikethrough, correct answer marked in green.
  - Explanation callout explaining why the choice was wrong.

- Review Card 3 (AI-Graded Short Answer):
  - Amber left border accent, top header: "Question 3 (SHORT ANSWER) • Score: 1.8 / 2.0 pts • ⚡ Partial Credit".
  - Candidate submitted answer box: "Preemptive scheduling interrupts a running task when higher priority tasks arrive. Non-preemptive waits."
  - Expected Model Rubric box (green border).
  - AI Evaluation Bubble (light blue with lightbulb icon): "💡 AI Evaluation: Excellent clarity on preemption; minor omission of I/O voluntary yield mechanisms."
```

---

## Screen 6: Multi-Format Export Hub

### Target Viewport: Desktop (1280px+)

### Stitch Text Prompt:
```text
An Export and Sharing Hub screen for "StudyWise AI" (an assessment generation suite).

Header:
- Navigation bar with active "Export Hub" tab.
- Title: "Export & Sharing Hub" with subtitle: "Exporting: Operating Systems Midterm Assessment (11 Questions • 18.0 pts)".
- Button: "← Back to Question Bank".

Export Cards Grid (7 dedicated cards arranged in a responsive 3-column grid):
- Card 1:
  - Icon: Indigo document icon "📄"
  - Title: "Student Exam Paper (PDF / Print)"
  - Description: "Clean, formal printable test paper with student header, bubble options, and ruled lines. No answers shown."
  - Primary button: "🖨️ View & Print PDF"
- Card 2:
  - Icon: Emerald graduation cap icon "🎓"
  - Title: "Teacher Solution Key (PDF / Print)"
  - Description: "Complete test paper with correct answers highlighted in bold green, full explanations, source citations, and rubrics."
  - Button: "🖨️ View & Print Key"
- Card 3:
  - Icon: Blue Word icon "📝"
  - Title: "Microsoft Word (.docx) - Student"
  - Description: "Editable Microsoft Word document formatted for classroom printing and custom school letterheads."
  - Button: "📥 Download .docx"
- Card 4:
  - Icon: Purple Word icon "📘"
  - Title: "Microsoft Word (.docx) - Solution Key"
  - Description: "Fully editable solution sheet and grading rubrics for Microsoft Word."
  - Button: "📥 Download Key (.docx)"
- Card 5:
  - Icon: Amber spreadsheet icon "📋"
  - Title: "Google Forms Format (CSV)"
  - Description: "Structured CSV file formatted for Google Forms Quiz import scripts and Google Classroom."
  - Button: "📥 Download Forms CSV"
- Card 6:
  - Icon: Teal school icon "🏫"
  - Title: "Moodle LMS Package (GIFT Format)"
  - Description: "Standard GIFT file importable directly into Moodle Question Banks and LMS assessment engines."
  - Button: "📥 Download GIFT File"
- Card 7:
  - Icon: Slate database icon "💾"
  - Title: "Portable JSON Exam Data"
  - Description: "Full structured JSON data of all questions, options, and metadata for developers and backups."
  - Button: "📥 Download JSON"

Aesthetic:
- Crisp white cards with subtle border (#E2E8F0), soft hover shadow, colored icon backgrounds, clean Inter typography.
```
