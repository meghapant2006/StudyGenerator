# StudyWise AI | Exam Generator & Assessment Platform
*Modeled after [exam-generator.com](https://exam-generator.com/) (StudyWise AI)*

A modern, full-featured AI-powered assessment platform designed for educators, institutions, and students. Automatically generate professional examinations from uploaded PDF/text documents, lecture notes, or direct subject prompts with multi-format questions, live editing, online timed testing with palette navigation, AI auto-grading, and multi-format exports.

---

## ✨ Features & Capabilities

### 1. Multi-Source Assessment Generation
- **PDF Documents**: Upload academic syllabi, textbooks, and scanned notes with Tesseract OCR fallback.
- **Pasted Study Notes**: Paste lecture transcripts, outlines, or article summaries directly.
- **Curriculum / Subject Prompt**: Generate complete exams directly from a topic prompt (e.g., *"Operating Systems: CPU Scheduling Algorithms"*).

### 2. Versatile Question Formats
- **Multiple Choice (MCQ)**: 4 options with single-choice selection and pedagogical justifications.
- **True / False**: Assertion-based questions testing conceptual understanding.
- **Short Answer**: Direct questions with expected model responses and scoring rubrics.
- **Essay / Analytical**: In-depth questions with detailed grading criteria.

### 3. Interactive Question Bank & Live Editor
- Inline editing of question text, option choices, points/marks, and explanations.
- Add custom questions manually.
- Delete or reorder questions.
- **AI Regenerate**: Refine or replace individual questions with custom natural language prompts (e.g. *"Make this harder"*, *"Focus on real-world practical code examples"*).

### 4. Interactive Student Exam Player
- **Timed Assessment**: Real-time countdown timer with visual color warnings (green → yellow → red).
- **Question Palette Navigator**: Numbered palette (1..N) displaying real-time statuses (Answered, Current, Flagged, Unanswered).
- **Review Confirmation**: Summary prompt before final submission showing answered vs. unanswered and flagged items.

### 5. Smart Auto-Grading & Results
- Instant scoring for objective questions (MCQs, True/False).
- **AI-Assisted Subjective Evaluation**: Evaluates student short answers and essays against rubrics, providing numerical scores and constructive feedback.
- Visual score radial gauge, pass/fail status, and source page citations.

### 6. Multi-Format Export Hub
- **Student Exam Paper (PDF / Print)**: Formal test paper with school/candidate header, bubble circles, and ruled lines.
- **Teacher Solution Key (PDF / Print)**: Comprehensive solution sheet with correct answers highlighted, explanations, and rubrics.
- **Microsoft Word (.docx)**: Fully editable Word documents for student papers and teacher keys.
- **Google Forms CSV**: Pre-formatted for Google Forms / Quiz spreadsheet imports.
- **Moodle LMS (GIFT)**: Standard format for direct import into Moodle question banks.
- **Portable JSON**: Complete exam data backup.

### 7. Multi-AI Provider Support
- **Google Gemini AI**: Powered by Gemini 1.5 Flash / Pro.
- **OpenAI**: Compatible with GPT-4o, GPT-4o-mini, and GPT-3.5-turbo.
- **Demo / Offline Engine**: Built-in intelligent rule-based generator that creates genuine exams from documents with zero API keys required.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.8+ with Flask & Flask-CORS
- **PDF & OCR**: PyMuPDF (fitz) + Tesseract OCR
- **Database**: SQLite with dynamic schema migration
- **AI Engine**: Google Gemini API, OpenAI API, and Offline Demo Extractor
- **Exporting**: ReportLab / HTML5 Print Engine, python-docx, GIFT syntax generator
- **Frontend**: Responsive modern SaaS Single Page Application (HTML5, Modern CSS, Vanilla JS)

---

## 🚀 Quick Start

### 1. Installation
```bash
# Clone the repository
cd PDF

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Optional: Configure API Keys
You can run the application immediately in **Demo Engine** mode without any keys.
To use live LLMs, either set environment variables:
```bash
export GEMINI_API_KEY="your-gemini-key"
# or
export OPENAI_API_KEY="your-openai-key"
```
Or simply enter your keys directly in the **Settings** modal inside the web interface!

### 3. Start the Server
```bash
cd backend
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000/
```

---

## 📂 Project Structure

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
