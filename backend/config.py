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
ALLOWED_EXTENSIONS = {'pdf'}

# PDF extraction settings
USE_OCR = True  # Enable OCR for scanned PDFs
OCR_LANGUAGE = 'eng'  # Tesseract language code
MIN_TEXT_CONFIDENCE = 60  # Minimum OCR confidence percentage

# AI settings (OpenAI example - you can swap with other providers)
AI_API_KEY = os.getenv('OPENAI_API_KEY', '')
AI_MODEL = 'gpt-3.5-turbo'  # or 'gpt-4' for better quality
AI_TEMPERATURE = 0.7
AI_MAX_TOKENS = 2000

# Question generation settings
DEFAULT_NUM_QUESTIONS = 10
MIN_QUESTIONS = 1
MAX_QUESTIONS = 50
ANSWERS_PER_QUESTION = 4  # Fixed as per requirements

# Database settings
DB_TIMEOUT = 30  # SQLite timeout in seconds
