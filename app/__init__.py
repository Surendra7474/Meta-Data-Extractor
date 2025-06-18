import os
from flask import Flask
from flask_wtf.csrf import CSRFProtect

def create_app(config_name=None):
    """
    Factory function to create and configure the Flask application.

    Args:
        config_name (str, optional): Configuration to use. Defaults to None.

    Returns:
        Flask: Configured Flask application
    """
    app = Flask(__name__)

    # Initialize CSRF protection
    csrf = CSRFProtect(app)

    # Load configuration
    from app.config import config
    config_name = config_name or os.getenv('FLASK_ENV', 'default')
    app.config.from_object(config[config_name])

    # Configure custom JSON encoder for the Flask app
    from app.utils.file_utils import CustomJSONEncoder
    app.json.encoder = CustomJSONEncoder

    # Initialize extensions here if needed

    # Create upload directory if it doesn't exist
    upload_dir = os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'])
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    # Register Jinja2 filters
    @app.template_filter('format_bytes')
    def format_bytes(size):
        """
        Format bytes to a human-readable string
        (e.g., 1024 -> 1 KB, 1048576 -> 1 MB)
        """
        units = ['bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']

        # Handle edge cases
        if size == 0:
            return "0 bytes"
        if size == 1:
            return "1 byte"

        # Find the appropriate unit
        i = 0
        while size >= 1024 and i < len(units) - 1:
            size /= 1024
            i += 1

        # Format with appropriate precision
        if i == 0:  # Still in bytes, no decimal
            return f"{int(size)} {units[i]}"
        else:
            return f"{size:.1f} {units[i]}"

    # Register datetime filter for formatting
    @app.template_filter('datetime')
    def format_datetime(value):
        """Format a datetime object to a readable string."""
        if value is None:
            return ""
        return value.strftime('%Y-%m-%d %H:%M:%S')

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')

    # Exempt API routes from CSRF protection
    csrf.exempt(api_bp)

    # Create database tables
    from app.utils.database import Base, engine
    from app.models.metadata import File, Metadata, AIAnalysis

    Base.metadata.create_all(bind=engine)

    return app