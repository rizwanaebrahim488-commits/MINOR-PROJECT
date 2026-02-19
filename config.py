"""
Configuration file for Attendance Tracker
Change COLLEGE_NAME, SECRET_KEY, etc. to match your college
"""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base configuration - works on Render too!"""
    
    # Database - SQLite (single file, no server needed)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'attendance.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security key (change this to random string!)
    SECRET_KEY = 'your-secret-key-12345678901234567890'
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = 1800
    
    # File upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    
    # Twilio (for SMS notifications - optional)
    TWILIO_ACCOUNT_SID = 'your-account-sid'
    TWILIO_AUTH_TOKEN = 'your-auth-token'
    TWILIO_PHONE_NUMBER = '+1234567890'
    
    # College Info
    COLLEGE_NAME = "Your College Name"
    COLLEGE_CITY = "Your City"

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = DevelopmentConfig()
