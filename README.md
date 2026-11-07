# StudyGenerator Exam | AI Assessment & Examination Platform

A modern, full-featured AI-powered assessment platform designed for educators, institutions, and students. Automatically generate professional examinations from uploaded PDF/Word/Text documents, lecture notes, or direct subject prompts with multi-format questions, live question bank editing, timed testing with palette navigation, AI auto-grading, email & mobile number authentication, and multi-format exports.

---

## Features & Capabilities

### 1. Multi-Source Assessment Generation
- **PDF Documents**: Upload academic syllabi, textbooks, and scanned notes with Tesseract OCR fallback.
- **DOCX / Microsoft Word**: Native parsing of Word documents via `python-docx`.
- **Pasted Study Notes & URLs**: Scrape live web links or paste lecture transcripts directly.
- **Curriculum / Subject Prompt**: Generate complete exams directly from a topic prompt (e.g., *"Operating Systems: CPU Scheduling Algorithms"*).

### 2. Versatile Question Formats
- **Multiple Choice (MCQ)**: 4 options with single-choice selection and pedagogical justifications.
- **True / False**: Assertion-based questions testing conceptual understanding.
- **Fill-in-the-Blank (Cloze)**: Text sentences with `[blank]` placeholders and automated casing-insensitive grading.
- **Short Answer**: Direct questions with expected model responses and scoring rubrics.
- **Essay / Analytical**: In-depth questions with detailed grading criteria.

### 3. Interactive Question Bank & Live Editor
- Inline editing of question text, option choices, points/marks, and explanations.
- Add custom questions manually.
- Delete, reorder (Up/Down syncs to DB), and regenerate individual questions.
- **AI Regenerate**: Refine or replace individual questions with custom natural language prompts (e.g. *"Make this harder"*, *"Focus on practical coding"*).

### 4. Interactive Student Exam Player
- **Timed Assessment**: Real-time countdown timer with visual color warnings.
- **Question Palette Navigator**: Numbered palette (1..N) displaying real-time statuses (Answered, Current, Flagged, Unanswered).
- **Review Confirmation**: Summary prompt before final submission showing answered vs. unanswered and flagged items.

### 5. Smart Auto-Grading & Results
- Instant scoring for objective questions (MCQs, True/False, Fill-in-the-Blank).
- **AI-Assisted Subjective Evaluation**: Evaluates student short answers and essays against rubrics, providing numerical scores and constructive feedback.

### 6. Multi-Format Export Hub
- **Student Exam Paper (PDF / Print)**: Formal test paper with school/candidate header, bubble circles, and ruled lines.
- **Teacher Solution Key (PDF / Print)**: Comprehensive solution sheet with correct answers highlighted, explanations, and rubrics.
- **Microsoft Word (.docx)**: Fully editable Word documents for student papers and teacher keys.
- **Google Forms CSV**: Pre-formatted for Google Forms / Quiz spreadsheet imports.
- **Moodle LMS (GIFT)**: Standard format for direct import into Moodle question banks.
- **Portable JSON**: Complete exam data backup.

### 7. Authentication & User Profiles
- **Email & Mobile Number Login**: Register and log in using either email or mobile phone numbers.
- **Sleek SaaS Modal**: Built with 100% vector Lucide icons, password eye visibility toggles, and Google Sign-In.
- **Dynamic Header & Greeting**: Welcomes logged-in users with `"Welcome back, [Username]"` on the header and dashboard.

---

## Quick Start

### 1. Installation
```bash
# Clone or navigate to the repository
cd PDF

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Run the Platform
You can use the helper script or run Flask directly:

```bash
# Option A: Using the start script (Linux / macOS)
./start.sh

# Option B: Run directly with Python
python3 backend/app.py
```

Then open your browser at:
```
http://127.0.0.1:5000/
```

### 3. Script Commands
```bash
./start.sh            # Starts server (or reports if already running on port 5000)
./start.sh --restart  # Restarts the server
./start.sh --stop     # Stops any running server instances
./start.sh --test     # Runs all automated test suites (Auth & Generator)
```

### 4. Instant Demo Credentials
- **Educator Demo**: `educator@studygeneratorexam.com` / `EducatorPass123!`
- **Admin Demo**: `admin@studygeneratorexam.com` / `AdminPass123!`
- Or register a new account with your **Email & Mobile Number**.

---

## Project Structure

```
PDF/
├── backend/
│   ├── app.py              # Flask application with REST API endpoints
│   ├── config.py           # Application and AI settings
│   ├── models.py           # Dataclass models (Exam, Question, Answer, ExamAttempt)
│   ├── database.py         # SQLite manager with automatic schema migration
│   ├── ai_generator.py     # Multi-provider AI engine (Gemini, OpenAI, Demo)
│   ├── export_service.py   # Multi-format exporter (PDF, Word, GIFT, Forms)
│   ├── pdf_extractor.py    # PyMuPDF text extractor with OCR support
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── index.html          # Modern SaaS Single Page App
│   ├── styles.css          # Design system matching exam-generator.com
│   └── app.js              # Client state, routing, exam player & auto-grading
├── data/
│   ├── uploads/            # Uploaded PDF/TXT files
│   ├── database.db         # SQLite database
│   └── cache/              # Temporary cache
└── README.md
```
