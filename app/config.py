import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-please-change-in-production')
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB max upload
    ALLOWED_EXTENSIONS = {
        'image': {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'},
        'document': {'pdf', 'docx', 'doc', 'txt', 'rtf', 'odt'},
        'spreadsheet': {'xlsx', 'xls', 'csv', 'ods'},
        'audio': {'mp3', 'wav', 'ogg', 'flac', 'aac'},
        'video': {'mp4', 'avi', 'mov', 'mkv', 'webm'}
    }

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = False
    TESTING = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False


# Dictionary with different configuration environments
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# Set active configuration
app_config = config[os.getenv('FLASK_ENV', 'default')]