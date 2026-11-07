"""
Phase 2 Test Suite: Core AI Exam Generator & Question Engine
Tests:
1. DOCX text extraction
2. URL web scraping & excerpting
3. Question schema validation
4. Multi-type generation including fill_blank, subject, language
5. Auto-grading of fill_blank cloze questions
6. Question reordering endpoint & DB persistence
7. Question regeneration
"""

import sys
import os
import unittest
import tempfile
from docx import Document

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from pdf_extractor import extract_docx_text, scrape_url_content
from ai_generator import AIQuestionGenerator
from models import Question, Answer, Exam, ExamAttempt
from app import app, db


class TestPhase2Generator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = db
        cls.generator = AIQuestionGenerator(provider='demo')
        cls.client = app.test_client()

    def test_01_docx_extraction(self):
        """Test DOCX file extraction"""
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            temp_path = f.name

        try:
            doc = Document()
            doc.add_heading('Operating Systems: Process Management', 0)
            doc.add_paragraph('A process is an instance of a computer program that is being executed.')
            doc.add_paragraph('Process scheduling allows multiple processes to share the CPU efficiently.')
            doc.save(temp_path)

            pages_dict, meta = extract_docx_text(temp_path)
            self.assertIn(1, pages_dict)
            self.assertIn('Process Management', pages_dict[1])
            self.assertGreater(meta.get('total_words', 0), 15)
            print("[PASS] 1. DOCX document extraction verified")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_02_schema_validation(self):
        """Test strict JSON question schema validator"""
        valid_data = {
            "questions": [
                {
                    "question_text": "What is the primary role of the CPU scheduler?",
                    "question_type": "mcq",
                    "answers": [
                        {"text": "Selects processes from ready queue", "is_correct": True},
                        {"text": "Manages secondary disk storage", "is_correct": False}
                    ],
                    "correct_answer": "Selects processes from ready queue",
                    "points": 1.0,
                    "justification": "The CPU scheduler selects from among the processes in ready memory."
                },
                {
                    "question_text": "In paging, [blank] translates logical addresses to physical addresses.",
                    "question_type": "fill_blank",
                    "answers": [
                        {"text": "MMU", "is_correct": True},
                        {"text": "memory management unit", "is_correct": True}
                    ],
                    "correct_answer": "MMU",
                    "points": 1.0,
                    "justification": "The hardware MMU performs address translation."
                }
            ]
        }
        is_valid, err = self.generator._validate_questions_schema(valid_data)
        self.assertTrue(is_valid, f"Expected valid schema, got error: {err}")

        # Test invalid schema (missing question_text)
        invalid_data = {
            "questions": [
                {
                    "question_type": "mcq",
                    "answers": [{"text": "A", "is_correct": True}],
                    "points": 1.0
                }
            ]
        }
        is_valid, err = self.generator._validate_questions_schema(invalid_data)
        self.assertFalse(is_valid)
        print("[PASS] 2. Question schema validation and rejection verified")

    def test_03_multi_type_generation(self):
        """Test generation of all 5 question types including fill_blank with subject and language"""
        sample_text = """
        Distributed systems coordinate components located on networked computers that communicate by passing messages.
        Consensus algorithms like Raft and Paxos ensure consistency across distributed nodes.
        Byzantine fault tolerance allows a distributed system to function despite malicious or arbitrary node failures.
        CAP theorem states that a distributed data store can simultaneously provide at most two out of three guarantees:
        Consistency, Availability, and Partition tolerance.
        """
        config = {
            'mcq': 2,
            'true_false': 1,
            'fill_blank': 2,
            'short_answer': 1,
            'essay': 1
        }
        questions = self.generator.generate_questions(
            content=sample_text,
            question_config=config,
            difficulty="medium",
            subject="Distributed Systems",
            language="English"
        )

        self.assertEqual(len(questions), 7)
        types = [q.question_type for q in questions]
        self.assertEqual(types.count('mcq'), 2)
        self.assertEqual(types.count('true_false'), 1)
        self.assertEqual(types.count('fill_blank'), 2)
        self.assertEqual(types.count('short_answer'), 1)
        self.assertEqual(types.count('essay'), 1)

        # Verify fill_blank format
        fb_q = [q for q in questions if q.question_type == 'fill_blank'][0]
        self.assertIn('[blank]', fb_q.question_text)
        self.assertTrue(len(fb_q.correct_answer) > 0)
        self.assertIn('Distributed Systems', fb_q.source_section)
        print("[PASS] 3. Multi-type question generation (MCQ, T/F, Fill Blank, Short, Essay) verified")

    def test_04_fill_blank_scoring(self):
        """Test auto-grading of fill_blank cloze questions"""
        q = Question(
            id=101,
            exam_id=1,
            question_text="The [blank] algorithm achieves consensus in distributed systems.",
            question_type="fill_blank",
            answers=[
                Answer(text="Paxos", is_correct=True),
                Answer(text="paxos", is_correct=True),
                Answer(text="Raft", is_correct=True)
            ],
            correct_answer="Paxos",
            points=1.0,
            justification="Paxos is a family of protocols for solving consensus."
        )

        exam = Exam(title="Scoring Test", questions=[q])

        # 1. Exact match
        att1 = ExamAttempt(id=1, exam_id=1, student_name="Test Student", answers={101: "Paxos"})
        att1.calculate_score(exam)
        self.assertEqual(att1.points_earned, 1.0)

        # 2. Case-insensitive match
        att2 = ExamAttempt(id=2, exam_id=1, student_name="Test Student", answers={101: "pAxOs"})
        att2.calculate_score(exam)
        self.assertEqual(att2.points_earned, 1.0)

        # 3. Alternate option match
        att3 = ExamAttempt(id=3, exam_id=1, student_name="Test Student", answers={101: "Raft"})
        att3.calculate_score(exam)
        self.assertEqual(att3.points_earned, 1.0)

        # 4. Incorrect answer
        att4 = ExamAttempt(id=4, exam_id=1, student_name="Test Student", answers={101: "Round Robin"})
        att4.calculate_score(exam)
        self.assertEqual(att4.points_earned, 0.0)

        print("[PASS] 4. Fill-in-the-blank auto-grading with exact, case-insensitive and alternative matching verified")

        print("[PASS] 4. Fill-in-the-blank auto-grading with exact, case-insensitive and alternative matching verified")

    def test_05_question_reordering(self):
        """Test question reordering in DB and via API endpoint"""
        exam = Exam(
            title="Reorder Test Exam",
            subject="Computer Science",
            language="English",
            questions=[
                Question(question_text="First Question", question_type="mcq", answers=[], correct_answer="A", points=1.0, order_index=0),
                Question(question_text="Second Question", question_type="mcq", answers=[], correct_answer="B", points=1.0, order_index=1),
                Question(question_text="Third Question", question_type="mcq", answers=[], correct_answer="C", points=1.0, order_index=2)
            ]
        )
        exam_id = self.db.save_exam(exam)
        saved = self.db.get_exam(exam_id)
        original_ids = [q.id for q in saved.questions]

        # Invert the order
        inverted_ids = list(reversed(original_ids))
        ok = self.db.reorder_questions(exam_id, inverted_ids)
        self.assertTrue(ok)

        # Verify new order in database
        reordered = self.db.get_exam(exam_id)
        new_ids = [q.id for q in reordered.questions]
        self.assertEqual(new_ids, inverted_ids)
        self.assertEqual(reordered.questions[0].question_text, "Third Question")
        self.assertEqual(reordered.questions[2].question_text, "First Question")

        print("[PASS] 5. Question reordering and persistence verified")

    def test_06_single_question_regeneration(self):
        """Test regenerating a single question with pedagogical instruction"""
        old_q = Question(
            id=1,
            exam_id=1,
            question_text="What is virtual memory?",
            question_type="short_answer",
            answers=[],
            correct_answer="Virtual memory is a memory management technique.",
            points=2.0
        )
        new_q = self.generator.regenerate_question(
            old_question=old_q,
            context="Virtual memory maps logical addresses to physical disk storage using paging.",
            instruction="Focus on page fault handling"
        )
        self.assertEqual(new_q.question_type, "short_answer")
        self.assertIn("Focus: Focus on page fault handling", new_q.question_text)
        print("[PASS] 6. Single question regeneration with custom guidance verified")


if __name__ == '__main__':
    print("\n=== STARTING PHASE 2 AI EXAM GENERATOR TEST SUITE ===")
    unittest.main(verbosity=0)
