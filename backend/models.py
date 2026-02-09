"""
Data models for exam generator
Defines the structure for PDFs, questions, exams, and attempts
"""
from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime
import json


@dataclass
class PDFDocument:
    """Represents an uploaded PDF document"""
    id: Optional[int] = None
    filename: str = ""
    original_name: str = ""
    upload_date: str = ""
    total_pages: int = 0
    text_extracted: bool = False
    ocr_used: bool = False
    
    def to_dict(self):
        return asdict(self)


@dataclass
class Answer:
    """Represents a single answer option"""
    text: str
    is_correct: bool
    
    def to_dict(self):
        return asdict(self)


@dataclass
class Question:
    """Represents a single exam question"""
    id: Optional[int] = None
    exam_id: Optional[int] = None
    question_text: str = ""
    answers: List[Answer] = None  # Always 4 answers
    justification: str = ""
    source_page: int = 0
    source_section: str = ""
    
    def __post_init__(self):
        if self.answers is None:
            self.answers = []
    
    def to_dict(self):
        return {
            'id': self.id,
            'exam_id': self.exam_id,
            'question_text': self.question_text,
            'answers': [ans.to_dict() if isinstance(ans, Answer) else ans for ans in self.answers],
            'justification': self.justification,
            'source_page': self.source_page,
            'source_section': self.source_section
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create Question from dictionary"""
        answers_data = data.get('answers', [])
        answers = [
            Answer(**ans) if isinstance(ans, dict) else ans 
            for ans in answers_data
        ]
        return cls(
            id=data.get('id'),
            exam_id=data.get('exam_id'),
            question_text=data.get('question_text', ''),
            answers=answers,
            justification=data.get('justification', ''),
            source_page=data.get('source_page', 0),
            source_section=data.get('source_section', '')
        )


@dataclass
class Exam:
    """Represents a generated exam"""
    id: Optional[int] = None
    pdf_id: int = 0
    title: str = ""
    created_date: str = ""
    num_questions: int = 0
    questions: List[Question] = None
    
    def __post_init__(self):
        if self.questions is None:
            self.questions = []
        if not self.created_date:
            self.created_date = datetime.now().isoformat()
    
    def to_dict(self):
        return {
            'id': self.id,
            'pdf_id': self.pdf_id,
            'title': self.title,
            'created_date': self.created_date,
            'num_questions': self.num_questions,
            'questions': [q.to_dict() if isinstance(q, Question) else q for q in self.questions]
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create Exam from dictionary"""
        questions_data = data.get('questions', [])
        questions = [
            Question.from_dict(q) if isinstance(q, dict) else q 
            for q in questions_data
        ]
        return cls(
            id=data.get('id'),
            pdf_id=data.get('pdf_id', 0),
            title=data.get('title', ''),
            created_date=data.get('created_date', ''),
            num_questions=data.get('num_questions', 0),
            questions=questions
        )


@dataclass
class ExamAttempt:
    """Represents a user's attempt at an exam"""
    id: Optional[int] = None
    exam_id: int = 0
    attempt_date: str = ""
    answers: dict = None  # {question_id: selected_answer_index}
    score: float = 0.0
    time_taken: int = 0  # seconds
    
    def __post_init__(self):
        if self.answers is None:
            self.answers = {}
        if not self.attempt_date:
            self.attempt_date = datetime.now().isoformat()
    
    def to_dict(self):
        return {
            'id': self.id,
            'exam_id': self.exam_id,
            'attempt_date': self.attempt_date,
            'answers': self.answers,
            'score': self.score,
            'time_taken': self.time_taken
        }
    
    def calculate_score(self, exam: Exam) -> float:
        """Calculate percentage score based on correct answers"""
        if not exam.questions:
            return 0.0
        
        correct = 0
        for question in exam.questions:
            if question.id in self.answers:
                selected_index = self.answers[question.id]
                if 0 <= selected_index < len(question.answers):
                    if question.answers[selected_index].is_correct:
                        correct += 1
        
        self.score = (correct / len(exam.questions)) * 100
        return self.score
