"""
Flask API for exam generator application
Provides REST endpoints for PDF upload, question generation, and exam taking
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from pathlib import Path
import uuid
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from config import (
    FLASK_HOST, FLASK_PORT, DEBUG, UPLOAD_DIR, MAX_FILE_SIZE,
    ALLOWED_EXTENSIONS, DEFAULT_NUM_QUESTIONS, MIN_QUESTIONS, MAX_QUESTIONS
)
from pdf_extractor import extract_pdf_text, PDFExtractor
from ai_generator import AIQuestionGenerator
from database import Database
from models import PDFDocument, Exam, ExamAttempt

# Initialize Flask app
app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)  # Enable CORS for frontend communication

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
db = Database()

# Global storage for extracted PDF content (in-memory cache)
pdf_content_cache = {}


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_ai_generator():
    """Get AI generator instance (lazy loading)"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return AIQuestionGenerator(api_key)


# API Routes
@app.route('/')
def index():
    """Serve main HTML page"""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'Exam generator API is running'
    })


@app.route('/api/upload', methods=['POST'])
def upload_pdf():
    """
    Upload PDF file and extract text
    
    Returns:
        JSON with PDF metadata and extraction summary
    """
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Only PDF files allowed'}), 400
        
        # Generate unique filename
        original_name = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{original_name}"
        file_path = UPLOAD_DIR / unique_filename
        
        # Save file
        file.save(file_path)
        logger.info(f"Saved uploaded file: {unique_filename}")
        
        # Extract text from PDF
        logger.info("Extracting text from PDF...")
        text_data, summary = extract_pdf_text(str(file_path))
        
        # Cache extracted content
        pdf_content_cache[unique_filename] = text_data
        
        # Save PDF metadata to database
        pdf_doc = PDFDocument(
            filename=unique_filename,
            original_name=original_name,
            upload_date=datetime.now().isoformat(),
            total_pages=summary['total_pages'],
            text_extracted=True,
            ocr_used=summary['ocr_used']
        )
        
        pdf_id = db.save_pdf(pdf_doc)
        pdf_doc.id = pdf_id
        
        logger.info(f"PDF processed successfully. ID: {pdf_id}")
        
        return jsonify({
            'success': True,
            'pdf': pdf_doc.to_dict(),
            'summary': summary
        })
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-exam', methods=['POST'])
def generate_exam():
    """
    Generate exam questions using AI
    
    Expected JSON body:
        {
            "pdf_id": int,
            "num_questions": int,
            "difficulty": "easy|medium|hard"
        }
    
    Returns:
        JSON with generated exam
    """
    try:
        data = request.get_json()
        
        # Validate input
        pdf_id = data.get('pdf_id')
        num_questions = data.get('num_questions', DEFAULT_NUM_QUESTIONS)
        difficulty = data.get('difficulty', 'medium')
        
        if not pdf_id:
            return jsonify({'error': 'pdf_id is required'}), 400
        
        if not MIN_QUESTIONS <= num_questions <= MAX_QUESTIONS:
            return jsonify({
                'error': f'Number of questions must be between {MIN_QUESTIONS} and {MAX_QUESTIONS}'
            }), 400
        
        # Get PDF from database
        pdf_doc = db.get_pdf(pdf_id)
        if not pdf_doc:
            return jsonify({'error': 'PDF not found'}), 404
        
        # Get cached content or reload
        if pdf_doc.filename not in pdf_content_cache:
            file_path = UPLOAD_DIR / pdf_doc.filename
            text_data, _ = extract_pdf_text(str(file_path))
            pdf_content_cache[pdf_doc.filename] = text_data
        
        content = pdf_content_cache[pdf_doc.filename]
        
        # Generate questions using AI
        logger.info(f"Generating {num_questions} questions for PDF {pdf_id}")
        ai_generator = get_ai_generator()
        questions = ai_generator.generate_questions(content, num_questions, difficulty)
        
        if not questions:
            return jsonify({'error': 'Failed to generate questions'}), 500
        
        # Create exam
        exam = Exam(
            pdf_id=pdf_id,
            title=f"Exam from {pdf_doc.original_name}",
            num_questions=len(questions),
            questions=questions
        )
        
        # Save to database
        exam_id = db.save_exam(exam)
        exam.id = exam_id
        
        logger.info(f"Generated exam {exam_id} with {len(questions)} questions")
        
        return jsonify({
            'success': True,
            'exam': exam.to_dict()
        })
        
    except ValueError as e:
        logger.error(f"Configuration error: {str(e)}")
        return jsonify({
            'error': 'AI service not configured. Please set OPENAI_API_KEY environment variable.'
        }), 500
    except Exception as e:
        logger.error(f"Exam generation failed: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/exam/<int:exam_id>', methods=['GET'])
def get_exam(exam_id):
    """Get exam by ID"""
    try:
        exam = db.get_exam(exam_id)
        
        if not exam:
            return jsonify({'error': 'Exam not found'}), 404
        
        return jsonify({
            'success': True,
            'exam': exam.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Failed to retrieve exam: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/submit-attempt', methods=['POST'])
def submit_attempt():
    """
    Submit exam attempt
    
    Expected JSON body:
        {
            "exam_id": int,
            "answers": {question_id: selected_index},
            "time_taken": int (seconds)
        }
    
    Returns:
        JSON with score and detailed results
    """
    try:
        data = request.get_json()
        
        exam_id = data.get('exam_id')
        answers = data.get('answers', {})
        time_taken = data.get('time_taken', 0)
        
        if not exam_id:
            return jsonify({'error': 'exam_id is required'}), 400
        
        # Get exam
        exam = db.get_exam(exam_id)
        if not exam:
            return jsonify({'error': 'Exam not found'}), 404
        
        # Convert string keys to int
        answers = {int(k): v for k, v in answers.items()}
        
        # Create attempt
        attempt = ExamAttempt(
            exam_id=exam_id,
            answers=answers,
            time_taken=time_taken
        )
        
        # Calculate score
        score = attempt.calculate_score(exam)
        
        # Save attempt
        attempt_id = db.save_attempt(attempt)
        attempt.id = attempt_id
        
        logger.info(f"Saved exam attempt {attempt_id}. Score: {score:.1f}%")
        
        return jsonify({
            'success': True,
            'attempt': attempt.to_dict(),
            'score': score
        })
        
    except Exception as e:
        logger.error(f"Failed to submit attempt: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/exams', methods=['GET'])
def get_all_exams():
    """Get all exams"""
    try:
        pdfs = db.get_all_pdfs()
        all_exams = []
        
        for pdf in pdfs:
            exams = db.get_exams_by_pdf(pdf.id)
            all_exams.extend(exams)
        
        return jsonify({
            'success': True,
            'exams': [exam.to_dict() for exam in all_exams]
        })
        
    except Exception as e:
        logger.error(f"Failed to retrieve exams: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/attempts/<int:exam_id>', methods=['GET'])
def get_exam_attempts(exam_id):
    """Get all attempts for an exam"""
    try:
        attempts = db.get_attempts_by_exam(exam_id)
        
        return jsonify({
            'success': True,
            'attempts': [attempt.to_dict() for attempt in attempts]
        })
        
    except Exception as e:
        logger.error(f"Failed to retrieve attempts: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/pdfs', methods=['GET'])
def get_all_pdfs():
    """Get all uploaded PDFs"""
    try:
        pdfs = db.get_all_pdfs()
        
        return jsonify({
            'success': True,
            'pdfs': [pdf.to_dict() for pdf in pdfs]
        })
        
    except Exception as e:
        logger.error(f"Failed to retrieve PDFs: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Error handlers
@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error"""
    return jsonify({'error': f'File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.0f}MB'}), 413


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    logger.info(f"Starting exam generator API on {FLASK_HOST}:{FLASK_PORT}")
    logger.info(f"Upload directory: {UPLOAD_DIR}")
    logger.info(f"Database: {db.db_path}")
    
    # Check for API key
    if not os.getenv('OPENAI_API_KEY'):
        logger.warning("⚠️  OPENAI_API_KEY not set. AI generation will not work!")
        logger.warning("   Set it with: $env:OPENAI_API_KEY='your-key-here'")
    
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=DEBUG)
