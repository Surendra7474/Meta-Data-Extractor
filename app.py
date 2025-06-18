import os
import sys
import platform
from app import create_app
from dotenv import load_dotenv

# Check Python version compatibility
def check_python_version():
    """Check if the Python version is compatible with the project."""
    python_version = sys.version_info
    version_string = platform.python_version()

    # Check if Python version is 3.13.x (known incompatible)
    if python_version.major == 3 and python_version.minor == 13:
        print(f"❌ Python version {version_string} is NOT compatible with MetaXtract.")
        print("   SQLAlchemy 2.0.23 has typing issues with Python 3.13.")
        print("   Please use Python 3.11.x or 3.10.x instead.")
        return False
    return True

# Verify Python version before proceeding
if not check_python_version():
    sys.exit(1)

# Load environment variables
load_dotenv()

# Create Flask application
app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    # Create upload directory if it doesn't exist
    upload_dir = os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'])
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    # Run the application
    app.run(
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    )