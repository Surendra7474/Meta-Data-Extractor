import os
import sys

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from dotenv import load_dotenv

# Load environment variables - try .env.vercel first, then fall back to .env
if os.path.exists('.env.vercel'):
    load_dotenv('.env.vercel')
else:
    load_dotenv()

# Create Flask application
app = create_app(os.getenv('FLASK_ENV', 'production'))

# Create upload directory if it doesn't exist
upload_dir = os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'])
if not os.path.exists(upload_dir):
    os.makedirs(upload_dir)

# Run setup script to ensure database is initialized
from app.utils.database import Base, engine
Base.metadata.create_all(bind=engine)

# This is for Vercel serverless deployment
if __name__ == '__main__':
    app.run(
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    )
