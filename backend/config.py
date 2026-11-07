"""
Configuration settings for the exam generator application
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Data directories
DATA_DIR = BASE_DIR / 'data'
UPLOAD_DIR = DATA_DIR / 'uploads'
CACHE_DIR = DATA_DIR / 'cache'
DATABASE_PATH = DATA_DIR / 'database.db'

# Create directories if they don't exist
for directory in [DATA_DIR, UPLOAD_DIR, CACHE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Flask settings
FLASK_HOST = '127.0.0.1'
FLASK_PORT = 5000
DEBUG = True

# File upload settings
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}

# PDF extraction settings
USE_OCR = True  # Enable OCR for scanned PDFs
OCR_LANGUAGE = 'eng'  # Tesseract language code
MIN_TEXT_CONFIDENCE = 60  # Minimum OCR confidence percentage

# AI settings
AI_OPENAI_KEY = os.getenv('OPENAI_API_KEY', '')
AI_GEMINI_KEY = os.getenv('GEMINI_API_KEY', '')
AI_API_KEY = AI_GEMINI_KEY or AI_OPENAI_KEY
DEFAULT_AI_PROVIDER = 'demo'  # 'demo', 'gemini', or 'openai'
AI_MODEL = 'gemini-1.5-flash' if AI_GEMINI_KEY else ('gpt-4o-mini' if AI_OPENAI_KEY else 'demo')
AI_TEMPERATURE = 0.7
AI_MAX_TOKENS = 3000

# Question generation settings
DEFAULT_NUM_QUESTIONS = 10
MIN_QUESTIONS = 1
MAX_QUESTIONS = 100
ANSWERS_PER_QUESTION = 4

# Database settings
DB_TIMEOUT = 30  # SQLite timeout in seconds
