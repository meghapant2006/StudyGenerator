"""
Database operations for exam generator
Handles storage and retrieval of PDFs, exams, questions, and attempts using SQLite
"""
import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
import logging

from config import DATABASE_PATH, DB_TIMEOUT
from models import PDFDocument, Exam, Question, Answer, ExamAttempt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Database:
    """
    Manages SQLite database operations for the exam generator
    """
    
    def __init__(self, db_path: str = str(DATABASE_PATH)):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.connection = None
        self._init_database()
    
    def _init_database(self):
        """Create database tables if they don't exist"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # PDFs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pdfs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    original_name TEXT NOT NULL,
                    upload_date TEXT NOT NULL,
                    total_pages INTEGER NOT NULL,
                    text_extracted BOOLEAN NOT NULL,
                    ocr_used BOOLEAN NOT NULL
                )
            """)
            
            # Exams table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pdf_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    created_date TEXT NOT NULL,
                    num_questions INTEGER NOT NULL,
                    FOREIGN KEY (pdf_id) REFERENCES pdfs(id) ON DELETE CASCADE
                )
            """)
            
            # Questions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exam_id INTEGER NOT NULL,
                    question_text TEXT NOT NULL,
                    answers TEXT NOT NULL,
                    justification TEXT NOT NULL,
                    source_page INTEGER NOT NULL,
                    source_section TEXT NOT NULL,
                    FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE
                )
            """)
            
            # Exam attempts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exam_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exam_id INTEGER NOT NULL,
                    attempt_date TEXT NOT NULL,
                    answers TEXT NOT NULL,
                    score REAL NOT NULL,
                    time_taken INTEGER NOT NULL,
                    FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE
                )
            """)
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    def _get_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(self.db_path, timeout=DB_TIMEOUT)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    
    # PDF operations
    def save_pdf(self, pdf: PDFDocument) -> int:
        """
        Save PDF document metadata
        
        Args:
            pdf: PDFDocument object
            
        Returns:
            ID of saved PDF
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO pdfs (filename, original_name, upload_date, total_pages, 
                                 text_extracted, ocr_used)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                pdf.filename,
                pdf.original_name,
                pdf.upload_date,
                pdf.total_pages,
                pdf.text_extracted,
                pdf.ocr_used
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_pdf(self, pdf_id: int) -> Optional[PDFDocument]:
        """Get PDF by ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pdfs WHERE id = ?", (pdf_id,))
            row = cursor.fetchone()
            
            if row:
                return PDFDocument(
                    id=row['id'],
                    filename=row['filename'],
                    original_name=row['original_name'],
                    upload_date=row['upload_date'],
                    total_pages=row['total_pages'],
                    text_extracted=bool(row['text_extracted']),
                    ocr_used=bool(row['ocr_used'])
                )
            return None
    
    def get_all_pdfs(self) -> List[PDFDocument]:
        """Get all PDFs"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM pdfs ORDER BY upload_date DESC")
            rows = cursor.fetchall()
            
            return [
                PDFDocument(
                    id=row['id'],
                    filename=row['filename'],
                    original_name=row['original_name'],
                    upload_date=row['upload_date'],
                    total_pages=row['total_pages'],
                    text_extracted=bool(row['text_extracted']),
                    ocr_used=bool(row['ocr_used'])
                )
                for row in rows
            ]
    
    # Exam operations
    def save_exam(self, exam: Exam) -> int:
        """
        Save exam with all questions
        
        Args:
            exam: Exam object with questions
            
        Returns:
            ID of saved exam
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Save exam
            cursor.execute("""
                INSERT INTO exams (pdf_id, title, created_date, num_questions)
                VALUES (?, ?, ?, ?)
            """, (
                exam.pdf_id,
                exam.title,
                exam.created_date,
                exam.num_questions
            ))
            exam_id = cursor.lastrowid
            
            # Save questions
            for question in exam.questions:
                # Serialize answers to JSON
                answers_json = json.dumps([ans.to_dict() for ans in question.answers])
                
                cursor.execute("""
                    INSERT INTO questions (exam_id, question_text, answers, 
                                         justification, source_page, source_section)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    exam_id,
                    question.question_text,
                    answers_json,
                    question.justification,
                    question.source_page,
                    question.source_section
                ))
            
            conn.commit()
            logger.info(f"Saved exam {exam_id} with {len(exam.questions)} questions")
            return exam_id
    
    def get_exam(self, exam_id: int) -> Optional[Exam]:
        """Get exam with all questions"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get exam
            cursor.execute("SELECT * FROM exams WHERE id = ?", (exam_id,))
            exam_row = cursor.fetchone()
            
            if not exam_row:
                return None
            
            # Get questions
            cursor.execute("SELECT * FROM questions WHERE exam_id = ?", (exam_id,))
            question_rows = cursor.fetchall()
            
            questions = []
            for q_row in question_rows:
                # Deserialize answers
                answers_data = json.loads(q_row['answers'])
                answers = [Answer(**ans) for ans in answers_data]
                
                questions.append(Question(
                    id=q_row['id'],
                    exam_id=q_row['exam_id'],
                    question_text=q_row['question_text'],
                    answers=answers,
                    justification=q_row['justification'],
                    source_page=q_row['source_page'],
                    source_section=q_row['source_section']
                ))
            
            return Exam(
                id=exam_row['id'],
                pdf_id=exam_row['pdf_id'],
                title=exam_row['title'],
                created_date=exam_row['created_date'],
                num_questions=exam_row['num_questions'],
                questions=questions
            )
    
    def get_exams_by_pdf(self, pdf_id: int) -> List[Exam]:
        """Get all exams for a PDF"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM exams WHERE pdf_id = ? ORDER BY created_date DESC", (pdf_id,))
            exam_ids = [row['id'] for row in cursor.fetchall()]
            
            return [self.get_exam(exam_id) for exam_id in exam_ids]
    
    # Exam attempt operations
    def save_attempt(self, attempt: ExamAttempt) -> int:
        """Save exam attempt"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            answers_json = json.dumps(attempt.answers)
            
            cursor.execute("""
                INSERT INTO exam_attempts (exam_id, attempt_date, answers, score, time_taken)
                VALUES (?, ?, ?, ?, ?)
            """, (
                attempt.exam_id,
                attempt.attempt_date,
                answers_json,
                attempt.score,
                attempt.time_taken
            ))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_attempts_by_exam(self, exam_id: int) -> List[ExamAttempt]:
        """Get all attempts for an exam"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM exam_attempts WHERE exam_id = ? ORDER BY attempt_date DESC",
                (exam_id,)
            )
            rows = cursor.fetchall()
            
            return [
                ExamAttempt(
                    id=row['id'],
                    exam_id=row['exam_id'],
                    attempt_date=row['attempt_date'],
                    answers=json.loads(row['answers']),
                    score=row['score'],
                    time_taken=row['time_taken']
                )
                for row in rows
            ]


# Test database operations
if __name__ == "__main__":
    db = Database()
    
    # Test PDF save/retrieve
    test_pdf = PDFDocument(
        filename="test.pdf",
        original_name="Test Document.pdf",
        upload_date=datetime.now().isoformat(),
        total_pages=10,
        text_extracted=True,
        ocr_used=False
    )
    
    pdf_id = db.save_pdf(test_pdf)
    print(f"Saved PDF with ID: {pdf_id}")
    
    retrieved_pdf = db.get_pdf(pdf_id)
    print(f"Retrieved PDF: {retrieved_pdf.original_name}")
