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
from flask import Flask, request, jsonify, send_from_directory, Response, g
from flask_cors import CORS
from werkzeug.utils import secure_filename
from pathlib import Path
import uuid
from datetime import datetime, timedelta
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
from pdf_extractor import extract_pdf_text, extract_docx_text, scrape_url_content, PDFExtractor
from ai_generator import AIQuestionGenerator
from database import Database
from models import PDFDocument, Exam, Question, Answer, ExamAttempt, User
from export_service import ExportService
from auth_service import (
    AuthService, login_required, admin_required, get_token_from_request
)

# Initialize Flask app
app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app, supports_credentials=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
db = Database()
export_service = ExportService()

# Global storage for extracted PDF content (in-memory cache)
pdf_content_cache = {}


def seed_default_accounts():
    """Ensure default educator and admin test accounts exist"""
    try:
        # 1. Admin account
        admin_user = db.get_user_by_email("admin@studygeneratorexam.com")
        if not admin_user:
            admin_hash = AuthService.hash_password("AdminPass123!")
            db.create_user(
                email="admin@studygeneratorexam.com",
                password_hash=admin_hash,
                name="System Administrator",
                role="admin",
                is_verified=True,
                institution="StudyGeneratorExam HQ",
                plan="institution"
            )
            logger.info("Created default admin: admin@studygeneratorexam.com / AdminPass123!")

        # 2. Educator account
        educator_user = db.get_user_by_email("educator@studygeneratorexam.com")
        if not educator_user:
            edu_hash = AuthService.hash_password("EducatorPass123!")
            db.create_user(
                email="educator@studygeneratorexam.com",
                password_hash=edu_hash,
                name="Prof. Alex Morgan",
                role="user",
                is_verified=True,
                institution="Stanford University",
                plan="pro"
            )
            logger.info("Created default educator: educator@studygeneratorexam.com / EducatorPass123!")
    except Exception as e:
        logger.warning(f"Default accounts seed error (non-fatal): {e}")

# Seed default accounts on startup
seed_default_accounts()


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
        'name': 'StudyGeneratorExam API',
        'version': '3.0.0',
        'message': 'StudyGeneratorExam API is operational',
        'timestamp': datetime.now().isoformat()
    })


# =============================================================================
# Authentication & User Session Routes (Full Phase 1 Implementation)
# =============================================================================

@app.route('/api/auth/signup', methods=['POST'])
def auth_signup():
    """Register a new user with email and bcrypt hashed password"""
    if not AuthService.check_rate_limit('signup', max_attempts=15, window_seconds=600):
        return jsonify({'success': False, 'error': 'Too many signup attempts. Please try again later.'}), 429

    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    name = data.get('name', '').strip()
    institution = data.get('institution', '').strip()
    phone = data.get('phone', data.get('mobile', '')).strip()

    # Input validation
    valid, err_msg = AuthService.validate_signup_input(email, password, name)
    if not valid:
        return jsonify({'success': False, 'error': err_msg}), 400

    # Check duplicate email
    existing_user = db.get_user_by_email(email)
    if existing_user:
        return jsonify({'success': False, 'error': 'An account with this email already exists.'}), 409

    try:
        # Hash password and generate verification token
        hashed_password = AuthService.hash_password(password)
        verif_token = AuthService.generate_random_token(32)

        user = db.create_user(
            email=email,
            password_hash=hashed_password,
            name=name,
            role='user',
            auth_provider='local',
            is_verified=False,
            verification_token=verif_token,
            institution=institution,
            phone=phone,
            plan='free'
        )

        # Issue JWT
        token = AuthService.generate_token(user, remember_me=True)
        response = jsonify({
            'success': True,
            'message': 'Account created successfully! Please verify your email.',
            'user': user.to_dict(),
            'token': token,
            'verification_token': verif_token
        })
        response.set_cookie('access_token', token, httponly=True, samesite='Lax', max_age=30*86400)
        return response, 201

    except Exception as e:
        logger.error(f"Signup error: {e}")
        return jsonify({'success': False, 'error': f'Failed to create account: {str(e)}'}), 500


@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    """Authenticate user with email and password, returning JWT and httpOnly cookie"""
    if not AuthService.check_rate_limit('login', max_attempts=12, window_seconds=600):
        return jsonify({'success': False, 'error': 'Too many failed login attempts. Please try again later.'}), 429

    data = request.get_json() or {}
    identifier = data.get('email', data.get('identifier', data.get('mobile', ''))).strip()
    password = data.get('password', '')
    remember_me = bool(data.get('remember_me', False))

    if not identifier or not password:
        return jsonify({'success': False, 'error': 'Email or mobile number, and password are required.'}), 400

    user = db.get_user_by_email_or_phone(identifier)
    if not user:
        return jsonify({'success': False, 'error': 'Invalid email/mobile number or password.'}), 401

    if not user.password_hash:
        return jsonify({
            'success': False,
            'error': 'This account was created via Google Sign-In. Please click Continue with Google.'
        }), 400

    if not AuthService.verify_password(password, user.password_hash):
        return jsonify({'success': False, 'error': 'Invalid email or password.'}), 401

    # Update last login
    db.update_user_last_login(user.id)
    token = AuthService.generate_token(user, remember_me=remember_me)

    response = jsonify({
        'success': True,
        'message': f'Welcome back, {user.name}!',
        'user': user.to_dict(),
        'token': token
    })
    max_age = 30 * 86400 if remember_me else 86400
    response.set_cookie('access_token', token, httponly=True, samesite='Lax', max_age=max_age)
    return response


@app.route('/api/auth/google', methods=['POST'])
def auth_google():
    """Authenticate or provision user via Google identity"""
    if not AuthService.check_rate_limit('google_auth', max_attempts=20, window_seconds=600):
        return jsonify({'success': False, 'error': 'Too many requests. Please wait a moment.'}), 429

    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    name = data.get('name', 'Educator').strip()
    google_id = data.get('id') or data.get('google_id') or ''
    institution = data.get('institution', '').strip()

    if not email:
        return jsonify({'success': False, 'error': 'Google email is required.'}), 400

    user = db.get_user_by_email(email)
    if not user:
        # Auto-provision new user via Google
        user = db.create_user(
            email=email,
            password_hash=None,
            name=name,
            role='user',
            auth_provider='google',
            google_id=google_id,
            is_verified=True,
            institution=institution,
            plan='free'
        )
    else:
        # Update login & verify email if Google authenticated
        db.update_user_last_login(user.id)
        if not user.is_verified:
            with db._get_connection() as conn:
                conn.execute("UPDATE users SET is_verified = 1 WHERE id = ?", (user.id,))
                conn.commit()
            user = db.get_user_by_id(user.id)

    token = AuthService.generate_token(user, remember_me=True)
    response = jsonify({
        'success': True,
        'message': f'Signed in with Google as {user.name}',
        'user': user.to_dict(),
        'token': token
    })
    response.set_cookie('access_token', token, httponly=True, samesite='Lax', max_age=30*86400)
    return response


@app.route('/api/auth/verify-email', methods=['GET', 'POST'])
def auth_verify_email():
    """Confirm user email using verification token"""
    token = request.args.get('token')
    if not token and request.is_json:
        token = request.get_json().get('token')

    if not token:
        return jsonify({'success': False, 'error': 'Verification token is required.'}), 400

    user = db.verify_user_email(token.strip())
    if not user:
        return jsonify({'success': False, 'error': 'Invalid or expired verification token.'}), 400

    return jsonify({
        'success': True,
        'message': 'Your email address has been successfully verified!',
        'user': user.to_dict()
    })


@app.route('/api/auth/forgot-password', methods=['POST'])
def auth_forgot_password():
    """Generate time-limited password reset token for given email"""
    if not AuthService.check_rate_limit('forgot_pwd', max_attempts=5, window_seconds=900):
        return jsonify({'success': False, 'error': 'Too many password reset requests. Please wait 15 minutes.'}), 429

    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'success': False, 'error': 'Email address is required.'}), 400

    user = db.get_user_by_email(email)
    reset_token = None
    if user and user.password_hash:
        reset_token = AuthService.generate_random_token(32)
        expires_iso = (datetime.now() + timedelta(hours=1)).isoformat()
        db.set_reset_token(email, reset_token, expires_iso)
        logger.info(f"Password reset token generated for {email}: {reset_token}")

    return jsonify({
        'success': True,
        'message': 'If an account exists with this email, password reset instructions have been generated.',
        'reset_token': reset_token
    })


@app.route('/api/auth/reset-password', methods=['POST'])
def auth_reset_password():
    """Reset password using valid time-limited reset token"""
    data = request.get_json() or {}
    token = data.get('token', '').strip()
    new_password = data.get('new_password', '')

    if not token or not new_password:
        return jsonify({'success': False, 'error': 'Reset token and new password are required.'}), 400

    if len(new_password) < 8 or not (any(c.isalpha() for c in new_password) and any(c.isdigit() for c in new_password)):
        return jsonify({'success': False, 'error': 'New password must be at least 8 characters with letters and numbers.'}), 400

    user = db.get_user_by_reset_token(token)
    if not user:
        return jsonify({'success': False, 'error': 'Invalid or expired password reset link.'}), 400

    try:
        new_hash = AuthService.hash_password(new_password)
        success = db.reset_password(token, new_hash)
        if success:
            return jsonify({'success': True, 'message': 'Password has been reset successfully. You can now sign in.'})
        return jsonify({'success': False, 'error': 'Failed to reset password.'}), 500
    except Exception as e:
        logger.error(f"Reset password error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auth/me', methods=['GET'])
def auth_me():
    """Return currently authenticated user profile or unauthenticated state"""
    token = get_token_from_request()
    if not token:
        return jsonify({'success': True, 'authenticated': False, 'user': None})

    payload = AuthService.decode_token(token)
    if not payload:
        return jsonify({'success': True, 'authenticated': False, 'user': None})

    user_id = int(payload.get('sub')) if payload.get('sub') else None
    user = db.get_user_by_id(user_id) if user_id else None
    if not user:
        return jsonify({'success': True, 'authenticated': False, 'user': None})

    return jsonify({
        'success': True,
        'authenticated': True,
        'user': user.to_dict()
    })


@app.route('/api/auth/profile', methods=['PUT'])
@login_required
def auth_update_profile():
    """Update current user profile (name, institution)"""
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    institution = data.get('institution', '').strip()
    phone = data.get('phone', data.get('mobile', '')).strip()

    if not name or len(name) < 2:
        return jsonify({'success': False, 'error': 'Full name must be at least 2 characters long.'}), 400

    user_id = g.current_user.id
    updated_user = db.update_user_profile(user_id, name, institution, phone=phone)
    return jsonify({
        'success': True,
        'message': 'Profile updated successfully.',
        'user': updated_user.to_dict()
    })


@app.route('/api/auth/change-password', methods=['PUT'])
@login_required
def auth_change_password():
    """Change current user password after verifying current password"""
    data = request.get_json() or {}
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')

    user = g.current_user
    if not user.password_hash:
        return jsonify({'success': False, 'error': 'This account uses Google Sign-In and does not have a local password.'}), 400

    if not AuthService.verify_password(current_password, user.password_hash):
        return jsonify({'success': False, 'error': 'Current password is incorrect.'}), 400

    if len(new_password) < 8 or not (any(c.isalpha() for c in new_password) and any(c.isdigit() for c in new_password)):
        return jsonify({'success': False, 'error': 'New password must be at least 8 characters with letters and numbers.'}), 400

    new_hash = AuthService.hash_password(new_password)
    db.change_user_password(user.id, new_hash)
    return jsonify({'success': True, 'message': 'Password has been changed successfully.'})


@app.route('/api/auth/account', methods=['DELETE'])
@login_required
def auth_delete_account():
    """Permanently delete user account and invalidate session"""
    data = request.get_json() or {}
    password = data.get('password', '')
    user = g.current_user

    # If local user with password, verify it
    if user.password_hash:
        if not password or not AuthService.verify_password(password, user.password_hash):
            return jsonify({'success': False, 'error': 'Password confirmation required to delete account.'}), 400

    db.delete_user(user.id)
    response = jsonify({'success': True, 'message': 'Account permanently deleted.'})
    response.delete_cookie('access_token')
    return response


@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    """Clear session cookie and log user out"""
    response = jsonify({
        'success': True,
        'authenticated': False,
        'message': 'Logged out successfully.'
    })
    response.delete_cookie('access_token')
    return response


@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_get_users():
    """Admin-only endpoint: list all registered users"""
    users = db.get_all_users()
    return jsonify({
        'success': True,
        'total': len(users),
        'users': [u.to_dict() for u in users]
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
        elif ext == 'docx':
            text_data, summary = extract_docx_text(str(file_path))
            ocr_used = False
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
                'avg_words_per_page': len(content.split()),
                'file_type': 'txt'
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


# Web URL Scraper Endpoint
@app.route('/api/scrape-url', methods=['POST'])
def scrape_url_endpoint():
    """Scrape educational article/web content from a URL"""
    try:
        data = request.get_json() or {}
        url = data.get('url', '').strip()
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        title, text, summary = scrape_url_content(url)
        if not text or len(text.strip()) < 40:
            return jsonify({'error': 'Insufficient textual content could be extracted from this webpage.'}), 400
            
        return jsonify({
            'success': True,
            'title': title,
            'content': text,
            'summary': summary,
            'preview_text': text[:600]
        })
    except Exception as e:
        logger.error(f"URL scraping failed for {url if 'url' in locals() else 'unknown'}: {e}")
        return jsonify({'error': f"Failed to extract webpage content: {str(e)}"}), 500


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
        subject = data.get('subject', 'General')
        language = data.get('language', 'English')
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

        elif source_type == 'url':
            url = (data.get('url') or data.get('source_ref') or '').strip()
            raw_content = (data.get('raw_text') or data.get('content') or '').strip()
            if not raw_content and url:
                _, raw_content, _ = scrape_url_content(url)
            if not raw_content:
                return jsonify({'error': 'Valid content is required for URL source'}), 400
            content_for_ai = raw_content
            source_ref = url or "Web Article"
            if not title:
                title = f"Exam from Web Content"
        else:
            return jsonify({'error': f'Unsupported source_type: {source_type}'}), 400

        # Instantiate generator
        ai_generator = get_ai_generator_from_request(data)
        questions = ai_generator.generate_questions(
            content=content_for_ai,
            question_config=q_config,
            difficulty=difficulty,
            target_audience=target_audience,
            source_type=source_type,
            subject=subject,
            language=language
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
            subject=subject,
            language=language,
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


@app.route('/api/exam/<int:exam_id>/reorder', methods=['PUT'])
@app.route('/api/exams/<int:exam_id>/reorder', methods=['PUT'])
def reorder_exam_questions(exam_id):
    """Reorder question sequence for an exam to persist new ordering"""
    try:
        data = request.get_json() or {}
        question_ids = data.get('question_ids', [])
        if not question_ids:
            return jsonify({'error': 'question_ids array is required'}), 400
        success = db.reorder_questions(exam_id, question_ids)
        return jsonify({
            'success': success,
            'exam_id': exam_id,
            'count': len(question_ids)
        })
    except Exception as e:
        logger.error(f"Failed to reorder questions for exam {exam_id}: {e}")
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
