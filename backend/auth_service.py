"""
Authentication & Authorization Service for StudyGeneratorExam
Provides:
- Bcrypt password hashing and verification
- JWT token issuance, verification, and cookie management
- Time-limited email verification and password reset tokens
- Strict input validation (email format, password complexity)
- In-memory sliding window rate limiting
- Flask route decorators: @login_required, @admin_required
"""
import re
import os
import time
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from functools import wraps
import bcrypt
import jwt
from flask import request, jsonify, g, current_app

from config import FLASK_HOST
from models import User
from database import Database

# Secret key for JWT signing
JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY") or "studygeneratorexam_secure_jwt_secret_key_2026_xyz"
JWT_ALGORITHM = "HS256"

# Rate Limiter storage: {ip_address: [(timestamp, action), ...]}
_rate_limit_records = {}


class AuthService:
    """Core security and authentication provider"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plain text password using bcrypt with salt"""
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against bcrypt hash"""
        if not plain_password or not hashed_password:
            return False
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False

    @staticmethod
    def validate_signup_input(email: str, password: str, name: str) -> Tuple[bool, Optional[str]]:
        """Validate email, password, and name formatting"""
        if not name or len(name.strip()) < 2:
            return False, "Full name must be at least 2 characters long."
        
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not email or not re.match(email_regex, email.strip()):
            return False, "Please enter a valid email address."
        
        if not password or len(password) < 8:
            return False, "Password must be at least 8 characters long."
        
        # At least one digit and one letter
        has_letter = any(c.isalpha() for c in password)
        has_digit = any(c.isdigit() for c in password)
        if not (has_letter and has_digit):
            return False, "Password must contain both letters and at least one number."
        
        return True, None

    @staticmethod
    def generate_token(user: User, remember_me: bool = False) -> str:
        """Generate JWT access token"""
        days = 30 if remember_me else 1
        now = datetime.utcnow()
        payload = {
            'sub': str(user.id),
            'email': user.email,
            'name': user.name,
            'role': user.role,
            'plan': user.plan,
            'iat': now,
            'exp': now + timedelta(days=days)
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """Decode and verify JWT access token"""
        if not token:
            return None
        try:
            return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            return None
        except Exception:
            return None

    @staticmethod
    def generate_random_token(length: int = 32) -> str:
        """Generate cryptographically secure URL-safe token"""
        return secrets.token_urlsafe(length)

    @staticmethod
    def check_rate_limit(action: str, max_attempts: int = 10, window_seconds: int = 600) -> bool:
        """
        Check if client IP has exceeded max allowed actions in time window.
        Returns True if allowed, False if rate limited.
        """
        client_ip = request.remote_addr or '127.0.0.1'
        now = time.time()
        
        # Clean older entries
        if client_ip not in _rate_limit_records:
            _rate_limit_records[client_ip] = []
        
        # Filter attempts within current window
        _rate_limit_records[client_ip] = [
            (ts, act) for (ts, act) in _rate_limit_records[client_ip]
            if now - ts < window_seconds
        ]
        
        # Count matching action attempts
        action_count = sum(1 for (ts, act) in _rate_limit_records[client_ip] if act == action)
        if action_count >= max_attempts:
            return False
        
        # Record this attempt
        _rate_limit_records[client_ip].append((now, action))
        return True


def get_token_from_request() -> Optional[str]:
    """Extract bearer token from Authorization header or httpOnly cookie"""
    # 1. Authorization header: "Bearer <token>"
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    
    # 2. X-Access-Token header
    custom_header = request.headers.get("X-Access-Token")
    if custom_header:
        return custom_header.strip()
    
    # 3. Cookie: access_token
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token.strip()
        
    return None


def login_required(f):
    """Decorator to require valid authenticated user session"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_request()
        if not token:
            return jsonify({
                'success': False,
                'error': 'Authentication required. Please sign in.',
                'code': 'UNAUTHORIZED'
            }), 401

        payload = AuthService.decode_token(token)
        if not payload:
            return jsonify({
                'success': False,
                'error': 'Session expired or invalid. Please sign in again.',
                'code': 'TOKEN_EXPIRED'
            }), 401

        db = Database()
        user_id = int(payload.get('sub')) if payload.get('sub') else None
        user = db.get_user_by_id(user_id) if user_id else None
        if not user:
            return jsonify({
                'success': False,
                'error': 'User account not found.',
                'code': 'USER_NOT_FOUND'
            }), 401

        # Attach user to Flask request context
        g.current_user = user
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require user with role == 'admin'"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        user = getattr(g, 'current_user', None)
        if not user or user.role != 'admin':
            return jsonify({
                'success': False,
                'error': 'Administrative privileges required.',
                'code': 'FORBIDDEN'
            }), 403
        return f(*args, **kwargs)
    return decorated_function
