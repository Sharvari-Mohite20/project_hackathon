import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'campus-lost-and-found-super-secret-key-2026'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f"sqlite:///{os.path.join(basedir, 'campus_lost_found.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload configuration
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
    
    # College Metadata
    COLLEGE_NAME = "Apex University of Science & Technology"
    CAMPUS_NAME = "Main Technology Campus"
    SECURITY_DESK_LOCATION = "Central Security Office, Ground Floor, Admin Block A"
    SECURITY_CONTACT_PHONE = "+91 98765 43210"
    SECURITY_CONTACT_EMAIL = "security@apexuni.edu"
    OFFICE_HOURS = "Mon - Sat: 8:00 AM - 8:00 PM"
