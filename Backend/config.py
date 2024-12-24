import os
from datetime import timedelta

class Config:
    # Get the absolute path to the project root directory
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # Database
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(BASE_DIR, "db", "dhan_api.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Create the db directory if it doesn't exist
    DB_DIR = os.path.join(BASE_DIR, "db")
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
        
    # Ensure the database file exists and has correct permissions
    DB_FILE = os.path.join(DB_DIR, "dhan_api.db")
    if not os.path.exists(DB_FILE):
        # Create an empty file with write permissions
        with open(DB_FILE, 'w') as f:
            pass
        # Set file permissions to allow writing
        os.chmod(DB_FILE, 0o666)
    
    # JWT settings
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key')  # Change in production
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    
    # Firebase settings
    FIREBASE_CREDENTIALS = os.path.join(BASE_DIR, 'firebase-credentials.json')
