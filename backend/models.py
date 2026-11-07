"""
Data models for exam generator
Defines the structure for PDFs, questions, exams, and attempts
Supports multiple question types: MCQ, True/False, Short Answer, Essay, Fill in the Blank
"""
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import json


@dataclass
class User:
    """Represents an application user with role and plan info"""
    id: Optional[int] = None
    email: str = ""
    password_hash: Optional[str] = None
    name: str = ""
    role: str = "user"  # 'user', 'admin'
    auth_provider: str = "local"  # 'local', 'google'
    google_id: str = ""
    is_verified: bool = False
    verification_token: str = ""
    reset_token: str = ""
    reset_token_expires: str = ""
    plan: str = "free"  # 'free', 'pro', 'institution'
    monthly_exam_count: int = 0
    institution: str = ""
    phone: str = ""
    created_at: str = ""
    last_login: str = ""

    def to_dict(self, include_sensitive: bool = False):
        data = {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'auth_provider': self.auth_provider,
            'is_verified': bool(self.is_verified),
            'plan': self.plan,
            'monthly_exam_count': self.monthly_exam_count,
            'institution': self.institution or '',
            'phone': self.phone or '',
            'created_at': self.created_at,
            'last_login': self.last_login or ''
        }
        if include_sensitive:
            data['password_hash'] = self.password_hash
            data['verification_token'] = self.verification_token
            data['reset_token'] = self.reset_token
            data['reset_token_expires'] = self.reset_token_expires
        return data


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
    """Represents a single answer option for multiple choice questions"""
    text: str
    is_correct: bool = False
    
    def to_dict(self):
        return asdict(self)


@dataclass
class Question:
    """Represents a single exam question of any supported format"""
    id: Optional[int] = None
    exam_id: Optional[int] = None
    question_text: str = ""
    question_type: str = "mcq"  # mcq, true_false, short_answer, essay, fill_blank
    answers: List[Answer] = None  # Choice options for MCQ / True-False
    correct_answer: Optional[str] = ""  # Model answer text or option indicator
    points: float = 1.0  # Marks allocated for this question
    justification: str = ""  # Explanation of why the answer is correct
    rubric: str = ""  # Scoring criteria for short answers / essays
    source_page: int = 0
    source_section: str = ""
    order_index: int = 0
    
    def __post_init__(self):
        if self.answers is None:
            self.answers = []
        if not self.correct_answer and self.answers:
            # Infer correct answer from answers if available
            for idx, ans in enumerate(self.answers):
                if isinstance(ans, Answer) and ans.is_correct:
                    self.correct_answer = ans.text
                elif isinstance(ans, dict) and ans.get('is_correct'):
                    self.correct_answer = ans.get('text', '')
    
    def to_dict(self):
        return {
            'id': self.id,
            'exam_id': self.exam_id,
            'question_text': self.question_text,
            'question_type': self.question_type or 'mcq',
            'answers': [ans.to_dict() if isinstance(ans, Answer) else ans for ans in self.answers],
            'correct_answer': self.correct_answer or '',
            'points': float(self.points or 1.0),
            'justification': self.justification or '',
            'rubric': self.rubric or '',
            'source_page': int(self.source_page or 0),
            'source_section': self.source_section or '',
            'order_index': int(self.order_index or 0)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create Question from dictionary"""
        answers_data = data.get('answers', [])
        answers = [
            Answer(**ans) if isinstance(ans, dict) else ans 
            for ans in answers_data
        ]
        
        q_type = data.get('question_type', 'mcq')
        
        # If true_false, ensure 2 options exist
        if q_type == 'true_false' and not answers:
            corr = str(data.get('correct_answer', 'True')).lower() == 'true'
            answers = [
                Answer(text="True", is_correct=corr),
                Answer(text="False", is_correct=not corr)
            ]

        return cls(
            id=data.get('id'),
            exam_id=data.get('exam_id'),
            question_text=data.get('question_text', ''),
            question_type=q_type,
            answers=answers,
            correct_answer=data.get('correct_answer', ''),
            points=float(data.get('points', 1.0)),
            justification=data.get('justification', ''),
            rubric=data.get('rubric', ''),
            source_page=int(data.get('source_page', 0)),
            source_section=data.get('source_section', ''),
            order_index=int(data.get('order_index', 0))
        )


@dataclass
class Exam:
    """Represents a generated exam"""
    id: Optional[int] = None
    pdf_id: Optional[int] = None
    title: str = ""
    description: str = ""
    source_type: str = "pdf"  # pdf, text, topic, url
    source_ref: str = ""  # Document name, URL, or prompt topic
    difficulty: str = "medium"  # easy, medium, hard, mixed
    target_audience: str = "General"  # High School, College, Professional, etc.
    subject: str = "General"  # Computer Science, Mathematics, Biology, etc.
    language: str = "English"  # English, Hindi, Spanish, etc.
    time_limit: int = 0  # Time limit in minutes (0 = untimed)
    passing_score: float = 70.0  # Passing percentage
    total_points: float = 0.0
    created_date: str = ""
    num_questions: int = 0
    questions: List[Question] = None
    
    def __post_init__(self):
        if self.questions is None:
            self.questions = []
        if not self.created_date:
            self.created_date = datetime.now().isoformat()
        if self.questions:
            self.num_questions = len(self.questions)
            self.total_points = sum(q.points for q in self.questions)
    
    def to_dict(self):
        return {
            'id': self.id,
            'pdf_id': self.pdf_id,
            'title': self.title,
            'description': self.description or '',
            'source_type': self.source_type or 'pdf',
            'source_ref': self.source_ref or '',
            'difficulty': self.difficulty or 'medium',
            'target_audience': self.target_audience or 'General',
            'subject': self.subject or 'General',
            'language': self.language or 'English',
            'time_limit': int(self.time_limit or 0),
            'passing_score': float(self.passing_score or 70.0),
            'total_points': float(self.total_points or (len(self.questions) if self.questions else 0)),
            'created_date': self.created_date,
            'num_questions': len(self.questions) if self.questions else int(self.num_questions or 0),
            'questions': [q.to_dict() if isinstance(q, Question) else q for q in self.questions]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create Exam from dictionary"""
        questions_data = data.get('questions', [])
        questions = [
            Question.from_dict(q) if isinstance(q, dict) else q 
            for q in questions_data
        ]
        return cls(
            id=data.get('id'),
            pdf_id=data.get('pdf_id'),
            title=data.get('title', ''),
            description=data.get('description', ''),
            source_type=data.get('source_type', 'pdf'),
            source_ref=data.get('source_ref', ''),
            difficulty=data.get('difficulty', 'medium'),
            target_audience=data.get('target_audience', 'General'),
            subject=data.get('subject', 'General'),
            language=data.get('language', 'English'),
            time_limit=int(data.get('time_limit', 0)),
            passing_score=float(data.get('passing_score', 70.0)),
            total_points=float(data.get('total_points', 0.0)),
            created_date=data.get('created_date', ''),
            num_questions=len(questions) if questions else int(data.get('num_questions', 0)),
            questions=questions
        )


@dataclass
class ExamAttempt:
    """Represents a student's attempt at an exam with grading results"""
    id: Optional[int] = None
    exam_id: int = 0
    student_name: str = "Student"
    attempt_date: str = ""
    answers: dict = None  # {str(question_id): selected_answer_or_text}
    feedback: dict = None  # {str(question_id): {"score": float, "feedback": str}}
    score: float = 0.0  # Percentage 0-100%
    points_earned: float = 0.0
    total_points: float = 0.0
    passed: bool = False
    time_taken: int = 0  # seconds
    
    def __post_init__(self):
        if self.answers is None:
            self.answers = {}
        if self.feedback is None:
            self.feedback = {}
        if not self.attempt_date:
            self.attempt_date = datetime.now().isoformat()
    
    def to_dict(self):
        return {
            'id': self.id,
            'exam_id': self.exam_id,
            'student_name': self.student_name,
            'attempt_date': self.attempt_date,
            'answers': self.answers,
            'feedback': self.feedback,
            'score': round(self.score, 1),
            'points_earned': round(self.points_earned, 1),
            'total_points': round(self.total_points, 1),
            'passed': self.passed,
            'time_taken': self.time_taken
        }
    
    def calculate_score(self, exam: Exam) -> float:
        """Calculate percentage score and points based on answers"""
        if not exam.questions:
            self.score = 0.0
            self.points_earned = 0.0
            self.total_points = 0.0
            self.passed = False
            return 0.0
        
        total_possible = 0.0
        earned = 0.0
        
        for q in exam.questions:
            q_id_str = str(q.id)
            q_pts = float(q.points or 1.0)
            total_possible += q_pts
            
            # Check if answer provided
            if q.id in self.answers or q_id_str in self.answers:
                user_ans = self.answers.get(q.id, self.answers.get(q_id_str))
                
                # Check feedback if AI scored it
                if q_id_str in self.feedback and 'score' in self.feedback[q_id_str]:
                    earned += float(self.feedback[q_id_str]['score'])
                elif q.question_type in ('mcq', 'true_false'):
                    # Option index or text match
                    is_correct = False
                    if isinstance(user_ans, int) and 0 <= user_ans < len(q.answers):
                        is_correct = q.answers[user_ans].is_correct
                    elif isinstance(user_ans, str):
                        for ans in q.answers:
                            if ans.text.strip().lower() == user_ans.strip().lower() and ans.is_correct:
                                is_correct = True
                                break
                    if is_correct:
                        earned += q_pts
                        self.feedback[q_id_str] = {'score': q_pts, 'feedback': 'Correct!'}
                    else:
                        self.feedback[q_id_str] = {'score': 0.0, 'feedback': 'Incorrect.'}
                elif q.question_type == 'fill_blank':
                    clean_user = str(user_ans).strip().lower()
                    clean_corr = str(q.correct_answer or '').strip().lower()
                    is_correct = (clean_user == clean_corr and clean_user != '')
                    if not is_correct and q.answers:
                        for a in q.answers:
                            ans_txt = (a.text if isinstance(a, Answer) else str(a.get('text', ''))).strip().lower()
                            if clean_user == ans_txt and ans_txt != '':
                                is_correct = True
                                break
                    if is_correct:
                        earned += q_pts
                        self.feedback[q_id_str] = {'score': q_pts, 'feedback': 'Correct fill-in-the-blank answer!'}
                    else:
                        self.feedback[q_id_str] = {'score': 0.0, 'feedback': f"Incorrect. Correct answer: '{q.correct_answer}'"}
                elif q.question_type == 'short_answer':
                    # Basic comparison if model answer exists
                    if q.correct_answer and user_ans and str(user_ans).strip().lower() == str(q.correct_answer).strip().lower():
                        earned += q_pts
                        self.feedback[q_id_str] = {'score': q_pts, 'feedback': 'Exact match!'}
                    elif user_ans and len(str(user_ans).strip()) > 3:
                        # Partial credit pending AI grading
                        earned += q_pts * 0.75
                        self.feedback[q_id_str] = {'score': q_pts * 0.75, 'feedback': 'Good attempt.'}
                    else:
                        self.feedback[q_id_str] = {'score': 0.0, 'feedback': 'No answer or incomplete.'}
                elif q.question_type == 'essay':
                    # Default credit pending AI rubric evaluation
                    if user_ans and len(str(user_ans).strip()) > 20:
                        earned += q_pts * 0.8
                        self.feedback[q_id_str] = {'score': q_pts * 0.8, 'feedback': 'Detailed response.'}
                    else:
                        self.feedback[q_id_str] = {'score': 0.0, 'feedback': 'Response too brief.'}
        
        self.points_earned = earned
        self.total_points = total_possible
        self.score = (earned / total_possible * 100.0) if total_possible > 0 else 0.0
        self.passed = self.score >= (exam.passing_score or 70.0)
        return self.score
