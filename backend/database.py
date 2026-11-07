"""
Database operations for exam generator
Handles storage and retrieval of PDFs, exams, questions, and attempts using SQLite
Supports schema auto-migration and extended CRUD operations
"""
import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
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
        Initialize database connection and ensure schema is up-to-date
        """
        self.db_path = db_path
        self._init_database()
        self._migrate_schema()
    
    def _get_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(self.db_path, timeout=DB_TIMEOUT)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

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
                    text_extracted BOOLEAN NOT NULL DEFAULT 1,
                    ocr_used BOOLEAN NOT NULL DEFAULT 0
                )
            """)
            
            # Exams table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pdf_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    source_type TEXT DEFAULT 'pdf',
                    source_ref TEXT DEFAULT '',
                    difficulty TEXT DEFAULT 'medium',
                    target_audience TEXT DEFAULT 'General',
                    time_limit INTEGER DEFAULT 0,
                    passing_score REAL DEFAULT 70.0,
                    total_points REAL DEFAULT 0.0,
                    created_date TEXT NOT NULL,
                    num_questions INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (pdf_id) REFERENCES pdfs(id) ON DELETE SET NULL
                )
            """)
            
            # Questions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exam_id INTEGER NOT NULL,
                    question_text TEXT NOT NULL,
                    question_type TEXT DEFAULT 'mcq',
                    answers TEXT NOT NULL DEFAULT '[]',
                    correct_answer TEXT DEFAULT '',
                    points REAL DEFAULT 1.0,
                    justification TEXT NOT NULL DEFAULT '',
                    rubric TEXT DEFAULT '',
                    source_page INTEGER NOT NULL DEFAULT 0,
                    source_section TEXT NOT NULL DEFAULT '',
                    order_index INTEGER DEFAULT 0,
                    FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE
                )
            """)
            
            # Exam attempts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exam_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exam_id INTEGER NOT NULL,
                    student_name TEXT DEFAULT 'Student',
                    attempt_date TEXT NOT NULL,
                    answers TEXT NOT NULL DEFAULT '{}',
                    feedback TEXT DEFAULT '{}',
                    score REAL NOT NULL DEFAULT 0.0,
                    points_earned REAL DEFAULT 0.0,
                    total_points REAL DEFAULT 0.0,
                    passed BOOLEAN DEFAULT 0,
                    time_taken INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE
                )
            """)
            
            conn.commit()
            logger.info("Database base tables initialized successfully")

    def _migrate_schema(self):
        """Dynamically add new columns to existing tables if missing and fix constraints"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if pdf_id has NOT NULL constraint in exams
            cursor.execute("PRAGMA table_info(exams)")
            exam_info = cursor.fetchall()
            pdf_id_info = next((col for col in exam_info if col['name'] == 'pdf_id'), None)
            if pdf_id_info and pdf_id_info['notnull'] == 1:
                logger.info("Migrating exams table to allow NULL pdf_id...")
                cursor.execute("""
                    CREATE TABLE exams_migration_temp (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pdf_id INTEGER,
                        title TEXT NOT NULL,
                        description TEXT DEFAULT '',
                        source_type TEXT DEFAULT 'pdf',
                        source_ref TEXT DEFAULT '',
                        difficulty TEXT DEFAULT 'medium',
                        target_audience TEXT DEFAULT 'General',
                        time_limit INTEGER DEFAULT 0,
                        passing_score REAL DEFAULT 70.0,
                        total_points REAL DEFAULT 0.0,
                        created_date TEXT NOT NULL,
                        num_questions INTEGER NOT NULL DEFAULT 0,
                        FOREIGN KEY (pdf_id) REFERENCES pdfs(id) ON DELETE SET NULL
                    )
                """)
                cursor.execute("""
                    INSERT INTO exams_migration_temp (id, pdf_id, title, description, source_type, 
                                                    source_ref, difficulty, target_audience, 
                                                    time_limit, passing_score, total_points, 
                                                    created_date, num_questions)
                    SELECT id, pdf_id, title, 
                           COALESCE(description, ''), 
                           COALESCE(source_type, 'pdf'), 
                           COALESCE(source_ref, ''), 
                           COALESCE(difficulty, 'medium'), 
                           COALESCE(target_audience, 'General'), 
                           COALESCE(time_limit, 0), 
                           COALESCE(passing_score, 70.0), 
                           COALESCE(total_points, 0.0), 
                           created_date, 
                           num_questions 
                    FROM exams
                """)
                cursor.execute("DROP TABLE exams")
                cursor.execute("ALTER TABLE exams_migration_temp RENAME TO exams")
                conn.commit()

            # Columns to ensure in exams
            exam_columns = {
                'description': 'TEXT DEFAULT ""',
                'source_type': 'TEXT DEFAULT "pdf"',
                'source_ref': 'TEXT DEFAULT ""',
                'difficulty': 'TEXT DEFAULT "medium"',
                'target_audience': 'TEXT DEFAULT "General"',
                'time_limit': 'INTEGER DEFAULT 0',
                'passing_score': 'REAL DEFAULT 70.0',
                'total_points': 'REAL DEFAULT 0.0'
            }
            cursor.execute("PRAGMA table_info(exams)")
            existing_exam_cols = {row['name'] for row in cursor.fetchall()}
            for col, col_type in exam_columns.items():
                if col not in existing_exam_cols:
                    cursor.execute(f"ALTER TABLE exams ADD COLUMN {col} {col_type}")
                    logger.info(f"Added column {col} to exams table")

            # Columns to ensure in questions
            question_columns = {
                'question_type': 'TEXT DEFAULT "mcq"',
                'correct_answer': 'TEXT DEFAULT ""',
                'points': 'REAL DEFAULT 1.0',
                'rubric': 'TEXT DEFAULT ""',
                'order_index': 'INTEGER DEFAULT 0'
            }
            cursor.execute("PRAGMA table_info(questions)")
            existing_q_cols = {row['name'] for row in cursor.fetchall()}
            for col, col_type in question_columns.items():
                if col not in existing_q_cols:
                    cursor.execute(f"ALTER TABLE questions ADD COLUMN {col} {col_type}")
                    logger.info(f"Added column {col} to questions table")

            # Columns to ensure in exam_attempts
            attempt_columns = {
                'student_name': 'TEXT DEFAULT "Student"',
                'feedback': 'TEXT DEFAULT "{}"',
                'points_earned': 'REAL DEFAULT 0.0',
                'total_points': 'REAL DEFAULT 0.0',
                'passed': 'BOOLEAN DEFAULT 0'
            }
            cursor.execute("PRAGMA table_info(exam_attempts)")
            existing_att_cols = {row['name'] for row in cursor.fetchall()}
            for col, col_type in attempt_columns.items():
                if col not in existing_att_cols:
                    cursor.execute(f"ALTER TABLE exam_attempts ADD COLUMN {col} {col_type}")
                    logger.info(f"Added column {col} to exam_attempts table")

            conn.commit()

    # PDF operations
    def save_pdf(self, pdf: PDFDocument) -> int:
        """Save PDF document metadata"""
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
        """Get all uploaded PDFs"""
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

    def delete_pdf(self, pdf_id: int) -> bool:
        """Delete PDF metadata"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM pdfs WHERE id = ?", (pdf_id,))
            conn.commit()
            return cursor.rowcount > 0

    # Exam operations
    def save_exam(self, exam: Exam) -> int:
        """Save exam with all questions"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            total_points = sum(float(q.points or 1.0) for q in exam.questions)
            num_questions = len(exam.questions)
            
            cursor.execute("""
                INSERT INTO exams (pdf_id, title, description, source_type, source_ref,
                                 difficulty, target_audience, time_limit, passing_score,
                                 total_points, created_date, num_questions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                exam.pdf_id,
                exam.title,
                exam.description,
                exam.source_type or 'pdf',
                exam.source_ref or '',
                exam.difficulty or 'medium',
                exam.target_audience or 'General',
                int(exam.time_limit or 0),
                float(exam.passing_score or 70.0),
                float(total_points),
                exam.created_date,
                num_questions
            ))
            exam_id = cursor.lastrowid
            
            # Save questions
            for idx, question in enumerate(exam.questions):
                answers_json = json.dumps([ans.to_dict() if isinstance(ans, Answer) else ans for ans in question.answers])
                cursor.execute("""
                    INSERT INTO questions (exam_id, question_text, question_type, answers, 
                                         correct_answer, points, justification, rubric,
                                         source_page, source_section, order_index)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    exam_id,
                    question.question_text,
                    question.question_type or 'mcq',
                    answers_json,
                    question.correct_answer or '',
                    float(question.points or 1.0),
                    question.justification or '',
                    question.rubric or '',
                    int(question.source_page or 0),
                    question.source_section or '',
                    idx
                ))
            
            conn.commit()
            logger.info(f"Saved exam {exam_id} ({exam.title}) with {num_questions} questions")
            return exam_id

    def get_exam(self, exam_id: int) -> Optional[Exam]:
        """Get exam with all questions"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM exams WHERE id = ?", (exam_id,))
            exam_row = cursor.fetchone()
            
            if not exam_row:
                return None
            
            cursor.execute("SELECT * FROM questions WHERE exam_id = ? ORDER BY order_index ASC, id ASC", (exam_id,))
            question_rows = cursor.fetchall()
            
            questions = []
            for q_row in question_rows:
                answers_data = json.loads(q_row['answers']) if q_row['answers'] else []
                answers = [Answer(**ans) if isinstance(ans, dict) else ans for ans in answers_data]
                
                questions.append(Question(
                    id=q_row['id'],
                    exam_id=q_row['exam_id'],
                    question_text=q_row['question_text'],
                    question_type=q_row['question_type'] or 'mcq',
                    answers=answers,
                    correct_answer=q_row['correct_answer'] or '',
                    points=float(q_row['points'] or 1.0),
                    justification=q_row['justification'] or '',
                    rubric=q_row['rubric'] or '',
                    source_page=int(q_row['source_page'] or 0),
                    source_section=q_row['source_section'] or '',
                    order_index=int(q_row['order_index'] or 0)
                ))
            
            return Exam(
                id=exam_row['id'],
                pdf_id=exam_row['pdf_id'],
                title=exam_row['title'],
                description=exam_row['description'] or '',
                source_type=exam_row['source_type'] or 'pdf',
                source_ref=exam_row['source_ref'] or '',
                difficulty=exam_row['difficulty'] or 'medium',
                target_audience=exam_row['target_audience'] or 'General',
                time_limit=int(exam_row['time_limit'] or 0),
                passing_score=float(exam_row['passing_score'] or 70.0),
                total_points=float(exam_row['total_points'] or 0.0),
                created_date=exam_row['created_date'],
                num_questions=len(questions),
                questions=questions
            )

    def update_exam(self, exam_id: int, data: Dict[str, Any]) -> bool:
        """Update exam metadata"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            fields = []
            values = []
            for key in ('title', 'description', 'difficulty', 'target_audience', 'time_limit', 'passing_score'):
                if key in data:
                    fields.append(f"{key} = ?")
                    values.append(data[key])
            if not fields:
                return False
            values.append(exam_id)
            cursor.execute(f"UPDATE exams SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()
            return cursor.rowcount > 0

    def delete_exam(self, exam_id: int) -> bool:
        """Delete exam and all related questions and attempts"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM questions WHERE exam_id = ?", (exam_id,))
            cursor.execute("DELETE FROM exam_attempts WHERE exam_id = ?", (exam_id,))
            cursor.execute("DELETE FROM exams WHERE id = ?", (exam_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_all_exams(self) -> List[Exam]:
        """Get all exams with question counts"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM exams ORDER BY created_date DESC")
            exam_ids = [row['id'] for row in cursor.fetchall()]
            return [self.get_exam(eid) for eid in exam_ids if eid]

    def get_exams_by_pdf(self, pdf_id: int) -> List[Exam]:
        """Get all exams generated from a specific PDF"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM exams WHERE pdf_id = ? ORDER BY created_date DESC", (pdf_id,))
            exam_ids = [row['id'] for row in cursor.fetchall()]
            return [self.get_exam(eid) for eid in exam_ids if eid]

    # Question operations
    def get_question(self, question_id: int) -> Optional[Question]:
        """Get single question by ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM questions WHERE id = ?", (question_id,))
            row = cursor.fetchone()
            if not row:
                return None
            answers_data = json.loads(row['answers']) if row['answers'] else []
            answers = [Answer(**ans) if isinstance(ans, dict) else ans for ans in answers_data]
            return Question(
                id=row['id'],
                exam_id=row['exam_id'],
                question_text=row['question_text'],
                question_type=row['question_type'] or 'mcq',
                answers=answers,
                correct_answer=row['correct_answer'] or '',
                points=float(row['points'] or 1.0),
                justification=row['justification'] or '',
                rubric=row['rubric'] or '',
                source_page=int(row['source_page'] or 0),
                source_section=row['source_section'] or '',
                order_index=int(row['order_index'] or 0)
            )

    def add_question(self, exam_id: int, question: Question) -> int:
        """Add new question to an exam"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Determine order_index
            cursor.execute("SELECT MAX(order_index) as max_idx FROM questions WHERE exam_id = ?", (exam_id,))
            res = cursor.fetchone()
            next_idx = (res['max_idx'] + 1) if res and res['max_idx'] is not None else 0
            
            answers_json = json.dumps([ans.to_dict() if isinstance(ans, Answer) else ans for ans in question.answers])
            cursor.execute("""
                INSERT INTO questions (exam_id, question_text, question_type, answers, 
                                     correct_answer, points, justification, rubric,
                                     source_page, source_section, order_index)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                exam_id,
                question.question_text,
                question.question_type or 'mcq',
                answers_json,
                question.correct_answer or '',
                float(question.points or 1.0),
                question.justification or '',
                question.rubric or '',
                int(question.source_page or 0),
                question.source_section or '',
                next_idx
            ))
            q_id = cursor.lastrowid
            
            # Update exam counts and points
            self._recalculate_exam_metrics(conn, exam_id)
            conn.commit()
            return q_id

    def update_question(self, question_id: int, data: Dict[str, Any]) -> bool:
        """Update existing question"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT exam_id FROM questions WHERE id = ?", (question_id,))
            q_row = cursor.fetchone()
            if not q_row:
                return False
            exam_id = q_row['exam_id']
            
            fields = []
            values = []
            if 'question_text' in data:
                fields.append("question_text = ?")
                values.append(data['question_text'])
            if 'question_type' in data:
                fields.append("question_type = ?")
                values.append(data['question_type'])
            if 'answers' in data:
                fields.append("answers = ?")
                answers_val = data['answers']
                if isinstance(answers_val, (list, tuple)):
                    values.append(json.dumps([a.to_dict() if hasattr(a, 'to_dict') else a for a in answers_val]))
                else:
                    values.append(str(answers_val))
            if 'correct_answer' in data:
                fields.append("correct_answer = ?")
                values.append(str(data['correct_answer']))
            if 'points' in data:
                fields.append("points = ?")
                values.append(float(data['points']))
            if 'justification' in data:
                fields.append("justification = ?")
                values.append(data['justification'])
            if 'rubric' in data:
                fields.append("rubric = ?")
                values.append(data['rubric'])
            if 'source_page' in data:
                fields.append("source_page = ?")
                values.append(int(data['source_page']))
            if 'source_section' in data:
                fields.append("source_section = ?")
                values.append(data['source_section'])
            if 'order_index' in data:
                fields.append("order_index = ?")
                values.append(int(data['order_index']))
                
            if not fields:
                return False
                
            values.append(question_id)
            cursor.execute(f"UPDATE questions SET {', '.join(fields)} WHERE id = ?", values)
            
            self._recalculate_exam_metrics(conn, exam_id)
            conn.commit()
            return True

    def delete_question(self, question_id: int) -> bool:
        """Delete question by ID and update exam metrics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT exam_id FROM questions WHERE id = ?", (question_id,))
            q_row = cursor.fetchone()
            if not q_row:
                return False
            exam_id = q_row['exam_id']
            cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
            self._recalculate_exam_metrics(conn, exam_id)
            conn.commit()
            return True

    def _recalculate_exam_metrics(self, conn, exam_id: int):
        """Update num_questions and total_points on an exam"""
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as q_count, SUM(points) as total_pts FROM questions WHERE exam_id = ?", (exam_id,))
        res = cursor.fetchone()
        q_count = res['q_count'] or 0
        total_pts = res['total_pts'] or 0.0
        cursor.execute("UPDATE exams SET num_questions = ?, total_points = ? WHERE id = ?", (q_count, total_pts, exam_id))

    # Exam attempt operations
    def save_attempt(self, attempt: ExamAttempt) -> int:
        """Save exam attempt"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            answers_json = json.dumps(attempt.answers)
            feedback_json = json.dumps(attempt.feedback or {})
            
            cursor.execute("""
                INSERT INTO exam_attempts (exam_id, student_name, attempt_date, answers, 
                                         feedback, score, points_earned, total_points, 
                                         passed, time_taken)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                attempt.exam_id,
                attempt.student_name or 'Student',
                attempt.attempt_date,
                answers_json,
                feedback_json,
                float(attempt.score),
                float(attempt.points_earned),
                float(attempt.total_points),
                int(attempt.passed),
                int(attempt.time_taken)
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
                    student_name=row['student_name'] if 'student_name' in row.keys() else 'Student',
                    attempt_date=row['attempt_date'],
                    answers=json.loads(row['answers']) if row['answers'] else {},
                    feedback=json.loads(row['feedback']) if 'feedback' in row.keys() and row['feedback'] else {},
                    score=float(row['score']),
                    points_earned=float(row['points_earned']) if 'points_earned' in row.keys() else 0.0,
                    total_points=float(row['total_points']) if 'total_points' in row.keys() else 0.0,
                    passed=bool(row['passed']) if 'passed' in row.keys() else False,
                    time_taken=int(row['time_taken'])
                )
                for row in rows
            ]

    def get_recent_attempts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent attempts across all exams with exam title"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.*, e.title as exam_title 
                FROM exam_attempts a 
                JOIN exams e ON a.exam_id = e.id 
                ORDER BY a.attempt_date DESC 
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [
                {
                    'id': row['id'],
                    'exam_id': row['exam_id'],
                    'exam_title': row['exam_title'],
                    'student_name': row['student_name'] or 'Student',
                    'attempt_date': row['attempt_date'],
                    'score': float(row['score']),
                    'points_earned': float(row['points_earned']),
                    'total_points': float(row['total_points']),
                    'passed': bool(row['passed']),
                    'time_taken': int(row['time_taken'])
                }
                for row in rows
            ]

    def get_analytics_summary(self) -> Dict[str, Any]:
        """Calculate high-level dashboard metrics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM exams")
            total_exams = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM questions")
            total_questions = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*), AVG(score) FROM exam_attempts")
            res = cursor.fetchone()
            total_attempts = res[0] or 0
            avg_score = round(res[1] or 0.0, 1)
            
            cursor.execute("SELECT COUNT(*) FROM pdfs")
            total_pdfs = cursor.fetchone()[0]
            
            return {
                'total_exams': total_exams,
                'total_questions': total_questions,
                'total_attempts': total_attempts,
                'avg_score': avg_score,
                'total_pdfs': total_pdfs
            }
