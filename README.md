# Exam Generator Application

A cross-platform application that generates multiple-choice exams from PDF documents using AI.

## Features
- Upload academic PDF syllabus
- Extract text with OCR support
- AI-powered question generation
- Interactive exam interface with instant feedback
- Local storage of exam attempts
- Source citation for each question

## Tech Stack
- **Backend**: Python 3.8+ with Flask
- **PDF Processing**: PyMuPDF (fitz)
- **OCR**: Tesseract + pytesseract
- **Database**: SQLite
- **Frontend**: HTML/CSS/JavaScript
- **Desktop**: Electron (planned)

## Project Structure
```
exam-generator/
├── backend/
│   ├── app.py              # Flask application entry point
│   ├── config.py           # Configuration settings
│   ├── models.py           # Data models
│   ├── pdf_extractor.py    # PDF text extraction with OCR
│   ├── ai_generator.py     # AI question generation
│   ├── database.py         # Database operations
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── index.html          # Main UI
│   ├── styles.css          # Styling
│   ├── app.js              # Frontend logic
│   └── assets/             # Images, icons
├── data/
│   ├── uploads/            # User-uploaded PDFs
│   ├── database.db         # SQLite database
│   └── cache/              # Temporary files
└── README.md
```

## Installation

### Prerequisites
```bash
# Install Tesseract OCR
# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
# macOS: brew install tesseract
# Linux: sudo apt-get install tesseract-ocr
```

### Setup
```bash
# Install Python dependencies
cd backend
pip install -r requirements.txt

# Run the application
python app.py
```

## Usage
1. Launch application
2. Upload PDF document
3. Select number of questions
4. Generate exam
5. Take exam and review results
