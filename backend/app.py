"""
Flask REST API for Exam Generator Platform (StudyWise AI / exam-generator.com)
Provides REST endpoints for:
- Document upload and OCR text extraction
- Multi-source AI exam generation (PDF, raw text, topics)
- Full Exam and Question Bank CRUD (add, edit, delete, reorder, regenerate)
- Timed exam taking and AI auto-grading with rubric evaluations
- Multi-format exports (Student & Teacher PDF/HTML, Word .docx, Moodle GIFT, Google Forms CSV, JSON)
- Dashboard analytics and settings
"""
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename
from pathlib import Path
import uuid
from datetime import datetime
import logging
import os
import io
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from config import (
    FLASK_HOST, FLASK_PORT, DEBUG, UPLOAD_DIR, MAX_FILE_SIZE,
    ALLOWED_EXTENSIONS, DEFAULT_NUM_QUESTIONS, MIN_QUESTIONS, MAX_QUESTIONS,
    AI_GEMINI_KEY, AI_OPENAI_KEY, DEFAULT_AI_PROVIDER
)
from pdf_extractor import extract_pdf_text, PDFExtractor
from ai_generator import AIQuestionGenerator
from database import Database
from models import PDFDocument, Exam, Question, Answer, ExamAttempt
from export_service import ExportService

# Initialize Flask app
app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
db = Database()
export_service = ExportService()

# Global storage for extracted PDF content (in-memory cache)
pdf_content_cache = {}

# User sessions & authentication store
active_users = {
    "default_educator": {
        "id": "usr_demo_101",
        "name": "Prof. Alex Morgan",
        "given_name": "Alex",
        "email": "alex.morgan@university.edu",
        "role": "Lead Instructor",
        "picture": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=150&q=80",
        "institution": "Department of Computer Science",
        "plan": "Institutional Pro",
        "authenticated": True,
        "auth_provider": "google"
    }
}
current_session_user = active_users["default_educator"]


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_ai_generator_from_request(req_data: dict = None) -> AIQuestionGenerator:
    """Factory for AIQuestionGenerator with request overrides or server env fallback"""
    data = req_data or {}
    provider = data.get('provider')
    api_key = data.get('api_key')
    model = data.get('model')
    return AIQuestionGenerator(provider=provider, api_key=api_key, model=model)


# Static Routes
@app.route('/')
def index():
    """Serve main Single Page Application"""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/health', methods=['GET'])
@app.route('/api/system/info', methods=['GET'])
def health_check():
    """Health check & system info endpoint"""
    return jsonify({
        'status': 'ok',
        'name': 'StudyWise AI Exam Generator API',
        'version': '2.4.0',
        'message': 'StudyWise Exam Generator API is running',
        'timestamp': datetime.now().isoformat()
    })


# Authentication & User Session Routes
@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    """Get currently authenticated user or guest state"""
    global current_session_user
    if current_session_user:
        return jsonify({
            'success': True,
            'authenticated': True,
            'user': current_session_user
        })
    return jsonify({
        'success': True,
        'authenticated': False,
        'user': None
    })


@app.route('/api/auth/google', methods=['POST'])
def google_auth():
    """Handle Google Login authentication payload"""
    global current_session_user
    try:
        data = request.get_json() or {}
        email = data.get('email', 'educator@example.com').strip()
        name = data.get('name', 'Educator').strip()
        given_name = data.get('given_name') or name.split(' ')[0]
        picture = data.get('picture') or "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=150&q=80"
        institution = data.get('institution', 'Academic Department')
        role = data.get('role', 'Instructor')

        user_id = data.get('id') or f"usr_g_{uuid.uuid4().hex[:8]}"

        user = {
            'id': user_id,
            'name': name,
            'given_name': given_name,
            'email': email,
            'role': role,
            'picture': picture,
            'institution': institution,
            'plan': 'Institutional Pro',
            'authenticated': True,
            'auth_provider': 'google',
            'last_login': datetime.now().isoformat()
        }

        active_users[user_id] = user
        current_session_user = user

        return jsonify({
            'success': True,
            'message': f'Welcome back, {name}!',
            'user': user
        })
    except Exception as e:
        logger.error(f"Google auth error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/auth/logout', methods=['POST'])
def logout_user():
    """Sign out current user and reset session"""
    global current_session_user
    current_session_user = None
    return jsonify({
        'success': True,
        'authenticated': False,
        'message': 'Logged out successfully'
    })


# Analytics Route
@app.route('/api/analytics', methods=['GET'])
@app.route('/api/analytics/summary', methods=['GET'])
def get_analytics():
    """Get high level analytics and metrics for dashboard"""
    try:
        summary = db.get_analytics_summary()
        recent_exams = [e.to_dict() for e in db.get_all_exams()[:6]]
        recent_attempts = db.get_recent_attempts(limit=5)
        response_data = {
            'success': True,
            'summary': summary,
            'recent_exams': recent_exams,
            'recent_attempts': recent_attempts,
            **summary
        }
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Failed to retrieve analytics: {e}")
        return jsonify({'error': str(e)}), 500


# PDF and Document Upload
@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload PDF or TXT file and extract text"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
        
        original_name = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{original_name}"
        file_path = UPLOAD_DIR / unique_filename
        file.save(file_path)
        logger.info(f"Saved uploaded file: {unique_filename}")

        ext = original_name.rsplit('.', 1)[1].lower()
        
        if ext == 'pdf':
            text_data, summary = extract_pdf_text(str(file_path))
            ocr_used = summary.get('ocr_used', False)
            total_pages = summary.get('total_pages', 1)
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            text_data = {1: content}
            summary = {
                'total_pages': 1,
                'pages_with_text': 1,
                'total_characters': len(content),
                'total_words': len(content.split()),
                'ocr_used': False,
                'avg_words_per_page': len(content.split())
            }
            ocr_used = False
            total_pages = 1

        pdf_content_cache[unique_filename] = text_data
        
        pdf_doc = PDFDocument(
            filename=unique_filename,
            original_name=original_name,
            upload_date=datetime.now().isoformat(),
            total_pages=total_pages,
            text_extracted=True,
            ocr_used=ocr_used
        )
        pdf_id = db.save_pdf(pdf_doc)
        pdf_doc.id = pdf_id

        # Text snippet for preview
        preview_text = text_data[1][:600] if 1 in text_data else ""
        
        return jsonify({
            'success': True,
            'pdf': pdf_doc.to_dict(),
            'summary': summary,
            'preview_text': preview_text
        })
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Exam Generation
@app.route('/api/generate-exam', methods=['POST'])
@app.route('/api/generate', methods=['POST'])
def generate_exam():
    """
    Generate exam from:
    1. Uploaded PDF (via pdf_id)
    2. Direct text / notes (via raw_text or text)
    3. Topic / prompt (via topic)
    """
    try:
        data = request.get_json() or {}
        
        source_type = data.get('source_type', 'pdf')
        title = data.get('title', '').strip()
        difficulty = data.get('difficulty', 'medium')
        target_audience = data.get('target_audience', 'General')
        time_limit = int(data.get('time_limit', 0))
        passing_score = float(data.get('passing_score', 70.0))
        
        # Question type breakdown
        q_config = data.get('question_config') or data.get('question_counts')
        if not q_config:
            num_q = int(data.get('num_questions', DEFAULT_NUM_QUESTIONS))
            q_config = {'mcq': num_q}

        content_for_ai = ""
        source_ref = ""
        pdf_id = None
        
        if source_type == 'pdf':
            pdf_id = data.get('pdf_id')
            if not pdf_id:
                return jsonify({'error': 'pdf_id is required for PDF source'}), 400
            pdf_doc = db.get_pdf(pdf_id)
            if not pdf_doc:
                return jsonify({'error': 'PDF document not found'}), 404
            
            source_ref = pdf_doc.original_name
            if not title:
                title = f"Exam: {pdf_doc.original_name.rsplit('.', 1)[0]}"
                
            if pdf_doc.filename not in pdf_content_cache:
                file_path = UPLOAD_DIR / pdf_doc.filename
                text_data, _ = extract_pdf_text(str(file_path))
                pdf_content_cache[pdf_doc.filename] = text_data
            content_for_ai = pdf_content_cache[pdf_doc.filename]
            
        elif source_type == 'text':
            raw_text = (data.get('raw_text') or data.get('text') or '').strip()
            if not raw_text:
                return jsonify({'error': 'raw_text or text is required for Text source'}), 400
            content_for_ai = raw_text
            source_ref = "Pasted Study Notes"
            if not title:
                title = "Exam from Study Notes"
                
        elif source_type == 'topic':
            topic = data.get('topic', '').strip()
            if not topic:
                return jsonify({'error': 'topic is required for Topic source'}), 400
            prompt_context = data.get('prompt', '').strip()
            content_for_ai = f"Curriculum Subject / Topic: {topic}. {prompt_context} Generate comprehensive questions covering core principles, mechanisms, applications, and problem-solving scenarios for {topic}."
            source_ref = topic
            if not title:
                title = f"Assessment: {topic}"
        else:
            return jsonify({'error': f'Unsupported source_type: {source_type}'}), 400

        # Instantiate generator
        ai_generator = get_ai_generator_from_request(data)
        questions = ai_generator.generate_questions(
            content=content_for_ai,
            question_config=q_config,
            difficulty=difficulty,
            target_audience=target_audience,
            source_type=source_type
        )
        
        if not questions:
            return jsonify({'error': 'Failed to generate questions'}), 500

        # Construct and persist Exam
        exam = Exam(
            pdf_id=pdf_id,
            title=title,
            description=f"Generated from {source_ref} ({difficulty.capitalize()} level)",
            source_type=source_type,
            source_ref=source_ref,
            difficulty=difficulty,
            target_audience=target_audience,
            time_limit=time_limit,
            passing_score=passing_score,
            questions=questions
        )
        
        exam_id = db.save_exam(exam)
        saved_exam = db.get_exam(exam_id)
        exam_dict = saved_exam.to_dict()
        
        return jsonify({
            'success': True,
            'exam': exam_dict,
            **exam_dict
        }), 201
        
    except Exception as e:
        logger.error(f"Exam generation failed: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Exam Management Routes (CRUD)
@app.route('/api/exams', methods=['GET'])
def get_all_exams():
    """Get all exams"""
    try:
        exams = db.get_all_exams()
        exam_dicts = [exam.to_dict() for exam in exams]
        return jsonify({
            'success': True,
            'exams': exam_dicts
        })
    except Exception as e:
        logger.error(f"Failed to retrieve exams: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/exam/<int:exam_id>', methods=['GET'])
@app.route('/api/exams/<int:exam_id>', methods=['GET'])
def get_exam(exam_id):
    """Get single exam by ID"""
    try:
        exam = db.get_exam(exam_id)
        if not exam:
            return jsonify({'error': 'Exam not found'}), 404
        exam_dict = exam.to_dict()
        return jsonify({
            'success': True,
            'exam': exam_dict,
            **exam_dict
        })
    except Exception as e:
        logger.error(f"Failed to get exam {exam_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/exam/<int:exam_id>', methods=['PUT'])
@app.route('/api/exams/<int:exam_id>', methods=['PUT'])
def update_exam(exam_id):
    """Update exam metadata"""
    try:
        data = request.get_json() or {}
        updated = db.update_exam(exam_id, data)
        if not updated:
            return jsonify({'error': 'Exam not found or no valid fields to update'}), 404
        exam_dict = db.get_exam(exam_id).to_dict()
        return jsonify({
            'success': True,
            'exam': exam_dict,
            **exam_dict
        })
    except Exception as e:
        logger.error(f"Failed to update exam {exam_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/exam/<int:exam_id>', methods=['DELETE'])
@app.route('/api/exams/<int:exam_id>', methods=['DELETE'])
def delete_exam(exam_id):
    """Delete exam and associated records"""
    try:
        deleted = db.delete_exam(exam_id)
        if not deleted:
            return jsonify({'error': 'Exam not found'}), 404
        return jsonify({
            'success': True,
            'message': f'Exam {exam_id} deleted successfully'
        })
    except Exception as e:
        logger.error(f"Failed to delete exam {exam_id}: {e}")
        return jsonify({'error': str(e)}), 500


# Question Bank & Editor Routes
@app.route('/api/exam/<int:exam_id>/questions', methods=['POST'])
@app.route('/api/exams/<int:exam_id>/questions', methods=['POST'])
def add_question_to_exam(exam_id):
    """Add new question manually to an exam"""
    try:
        data = request.get_json() or {}
        exam = db.get_exam(exam_id)
        if not exam:
            return jsonify({'error': 'Exam not found'}), 404
            
        question = Question.from_dict(data)
        question.exam_id = exam_id
        q_id = db.add_question(exam_id, question)
        new_q = db.get_question(q_id)
        q_dict = new_q.to_dict()
        
        return jsonify({
            'success': True,
            'question': q_dict,
            **q_dict
        }), 201
    except Exception as e:
        logger.error(f"Failed to add question to exam {exam_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/questions/<int:question_id>', methods=['GET'])
def get_question(question_id):
    """Get single question"""
    try:
        q = db.get_question(question_id)
        if not q:
            return jsonify({'error': 'Question not found'}), 404
        return jsonify({'success': True, 'question': q.to_dict()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/questions/<int:question_id>', methods=['PUT'])
def update_question(question_id):
    """Update question content, choices, or points"""
    try:
        data = request.get_json() or {}
        updated = db.update_question(question_id, data)
        if not updated:
            return jsonify({'error': 'Question not found or update failed'}), 404
        return jsonify({
            'success': True,
            'question': db.get_question(question_id).to_dict()
        })
    except Exception as e:
        logger.error(f"Failed to update question {question_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/questions/<int:question_id>', methods=['DELETE'])
def delete_question(question_id):
    """Delete question by ID"""
    try:
        deleted = db.delete_question(question_id)
        if not deleted:
            return jsonify({'error': 'Question not found'}), 404
        return jsonify({
            'success': True,
            'message': f'Question {question_id} deleted successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/questions/<int:question_id>/regenerate', methods=['POST'])
def regenerate_question(question_id):
    """Regenerate a single question with optional AI prompt/feedback"""
    try:
        data = request.get_json() or {}
        instruction = data.get('instruction', '')
        
        old_q = db.get_question(question_id)
        if not old_q:
            return jsonify({'error': 'Question not found'}), 404
            
        exam = db.get_exam(old_q.exam_id)
        context = exam.description if exam else old_q.question_text
        if exam and exam.pdf_id:
            pdf = db.get_pdf(exam.pdf_id)
            if pdf and pdf.filename in pdf_content_cache:
                context = pdf_content_cache[pdf.filename]

        ai_generator = get_ai_generator_from_request(data)
        new_q = ai_generator.regenerate_question(old_q, context, instruction)
        
        # Update question in database
        db.update_question(question_id, new_q.to_dict())
        updated_q = db.get_question(question_id)
        q_dict = updated_q.to_dict()
        
        return jsonify({
            'success': True,
            'question': q_dict,
            **q_dict
        })
    except Exception as e:
        logger.error(f"Failed to regenerate question {question_id}: {e}")
        return jsonify({'error': str(e)}), 500


# Exam Taking & Auto-Grading Routes
@app.route('/api/submit-attempt', methods=['POST'])
@app.route('/api/exams/<int:exam_id>/submit', methods=['POST'])
def submit_attempt(exam_id=None):
    """
    Submit exam attempt:
    - Auto-grades objective questions (MCQ, True/False)
    - AI auto-grades subjective questions (Short Answer, Essay) against rubrics
    - Records attempt to database and returns detailed results
    """
    try:
        data = request.get_json() or {}
        if not exam_id:
            exam_id = data.get('exam_id')
        student_name = data.get('student_name', 'Student').strip() or 'Student'
        answers = data.get('answers', {})
        time_taken = int(data.get('time_taken', 0))
        
        if not exam_id:
            return jsonify({'error': 'exam_id is required'}), 400
            
        exam = db.get_exam(exam_id)
        if not exam:
            return jsonify({'error': 'Exam not found'}), 404

        # Convert string question keys
        normalized_answers = {}
        for k, v in answers.items():
            try:
                normalized_answers[int(k)] = v
            except ValueError:
                normalized_answers[k] = v

        # AI evaluation for subjective questions
        ai_generator = get_ai_generator_from_request(data)
        feedback = ai_generator.grade_subjective_answers(
            exam_id=exam_id,
            questions=exam.questions,
            user_answers=normalized_answers
        )

        attempt = ExamAttempt(
            exam_id=exam_id,
            student_name=student_name,
            answers=normalized_answers,
            feedback=feedback,
            time_taken=time_taken
        )
        
        # Calculate full score and points
        attempt.calculate_score(exam)
        
        attempt_id = db.save_attempt(attempt)
        attempt.id = attempt_id
        
        logger.info(f"Recorded attempt {attempt_id} for exam {exam_id}. Score: {attempt.score:.1f}%")
        
        return jsonify({
            'success': True,
            'attempt': attempt.to_dict(),
            'score': attempt.score,
            'points_earned': attempt.points_earned,
            'total_points': attempt.total_points,
            'passed': attempt.passed,
            'feedback': feedback
        })
    except Exception as e:
        logger.error(f"Failed to submit attempt: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/attempts/<int:exam_id>', methods=['GET'])
def get_exam_attempts(exam_id):
    """Get all past attempts for an exam"""
    try:
        attempts = db.get_attempts_by_exam(exam_id)
        return jsonify({
            'success': True,
            'attempts': [att.to_dict() for att in attempts]
        })
    except Exception as e:
        logger.error(f"Failed to retrieve attempts: {e}")
        return jsonify({'error': str(e)}), 500


# Export & Sharing Routes
@app.route('/api/export/<int:exam_id>/<format_type>', methods=['GET'])
def export_exam(exam_id, format_type):
    """
    Export exam in specified format:
    - pdf, solution-pdf, html (Print-ready HTML/PDF)
    - docx, solution-docx (Word documents)
    - gift (Moodle LMS GIFT format)
    - csv, google-forms (Google Forms quiz import)
    - json (Full structured JSON backup)
    """
    try:
        exam = db.get_exam(exam_id)
        if not exam:
            return jsonify({'error': 'Exam not found'}), 404
            
        export_mode = request.args.get('type', 'student').lower()
        safe_title = secure_filename(exam.title.replace(' ', '_')) or f"exam_{exam_id}"
        format_lower = format_type.lower()

        # HTML / PDF Printable views
        if format_lower in ('pdf', 'html', 'print'):
            export_type = "teacher" if export_mode == "teacher" else "student"
            html_content = export_service.generate_html(exam, export_type)
            return Response(html_content, mimetype='text/html')
            
        elif format_lower in ('solution-pdf', 'solution-html', 'solution_pdf'):
            html_content = export_service.generate_html(exam, "teacher")
            return Response(html_content, mimetype='text/html')

        elif format_lower == 'docx':
            export_type = "teacher" if export_mode == "teacher" else "student"
            docx_bytes = export_service.generate_docx(exam, export_type)
            filename = f"{safe_title}_{export_type}.docx"
            return Response(
                docx_bytes,
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )
            
        elif format_lower in ('solution-docx', 'solution_docx'):
            docx_bytes = export_service.generate_docx(exam, "teacher")
            filename = f"{safe_title}_solution_key.docx"
            return Response(
                docx_bytes,
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )
            
        elif format_lower in ('gift', 'moodle'):
            gift_content = export_service.generate_gift(exam)
            filename = f"{safe_title}_moodle.gift.txt"
            return Response(
                gift_content,
                mimetype='text/plain',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )
            
        elif format_lower in ('csv', 'google-forms', 'google_forms'):
            csv_content = export_service.generate_google_forms_csv(exam)
            filename = f"{safe_title}_google_forms.csv"
            return Response(
                csv_content,
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )
            
        elif format_lower == 'json':
            json_str = json.dumps(exam.to_dict(), indent=2)
            filename = f"{safe_title}.json"
            return Response(
                json_str,
                mimetype='application/json',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'}
            )
            
        else:
            return jsonify({'error': f'Unsupported export format: {format_type}'}), 400

    except Exception as e:
        logger.error(f"Export error for exam {exam_id} ({format_type}): {e}")
        return jsonify({'error': str(e)}), 500


# Settings & Providers Route
@app.route('/api/settings', methods=['GET', 'POST'])
def manage_settings():
    """Get status of configured AI providers and test connections"""
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'providers': {
                'demo': {'available': True, 'default': True, 'label': 'Demo / Offline Engine (Zero Setup)'},
                'gemini': {
                    'available': bool(os.getenv('GEMINI_API_KEY') or AI_GEMINI_KEY),
                    'default_model': 'gemini-1.5-flash',
                    'label': 'Google Gemini AI'
                },
                'openai': {
                    'available': bool(os.getenv('OPENAI_API_KEY') or AI_OPENAI_KEY),
                    'default_model': 'gpt-4o-mini',
                    'label': 'OpenAI'
                }
            }
        })
    else:
        # Test connection
        data = request.get_json() or {}
        provider = data.get('provider', 'demo')
        api_key = data.get('api_key')
        try:
            gen = AIQuestionGenerator(provider=provider, api_key=api_key)
            test_q = gen.generate_questions("Biology: Cells are the basic unit of life.", {'mcq': 1})
            return jsonify({
                'success': True,
                'message': f'Connection test to {provider.upper()} successful! Generated sample question.'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Connection test failed: {str(e)}'
            }), 400


# Error Handlers
@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': f'File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.0f}MB'}), 413


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    logger.info(f"Starting Exam Generator Platform on {FLASK_HOST}:{FLASK_PORT}")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=DEBUG)
