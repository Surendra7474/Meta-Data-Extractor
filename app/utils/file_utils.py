import os
import uuid
import magic
from werkzeug.utils import secure_filename
from app.config import app_config
import hashlib
import time
import mimetypes
import json
from flask import current_app

def allowed_file(filename):
    """
    Check if a file has an allowed extension.
    
    Args:
        filename (str): The filename to check
        
    Returns:
        bool: True if file extension is allowed, False otherwise
    """
    if '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    
    # Check across all allowed file types
    for file_types in app_config.ALLOWED_EXTENSIONS.values():
        if ext in file_types:
            return True
            
    return False

def get_file_type(filename):
    """
    Get the general file type category based on extension.
    
    Args:
        filename (str): The filename to check
        
    Returns:
        str: File type category ('image', 'document', etc.) or None if not recognized
    """
    if '.' not in filename:
        return None
    
    ext = filename.rsplit('.', 1)[1].lower()
    
    for file_type, extensions in app_config.ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            return file_type
            
    return None

def get_safe_filename(filename):
    """
    Generate a safe filename that preserves the original extension.
    
    Args:
        filename (str): Original filename
        
    Returns:
        str: Safe filename with unique ID
    """
    if not filename:
        return None
        
    # Secure the filename
    secure_name = secure_filename(filename)
    
    # Get the extension
    ext = ""
    if '.' in secure_name:
        ext = secure_name.rsplit('.', 1)[1].lower()
        name = secure_name.rsplit('.', 1)[0]
    else:
        name = secure_name
    
    # Create unique filename
    unique_name = f"{name}_{uuid.uuid4().hex}"
    if ext:
        unique_name = f"{unique_name}.{ext}"
    
    return unique_name

def ensure_upload_dir():
    """
    Ensure the upload directory exists.
    
    Returns:
        str: Path to the upload directory
    """
    upload_dir = os.path.join(os.getcwd(), app_config.UPLOAD_FOLDER)
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    return upload_dir

def save_uploaded_file(file, directory=None):
    """
    Save an uploaded file to disk.
    
    Args:
        file: Flask file object
        directory (str, optional): Subdirectory to save in. Defaults to None.
        
    Returns:
        tuple: (saved_path, original_filename, safe_filename, file_size, mime_type)
    """
    if not file:
        return None
    
    # Ensure the filename is safe
    original_filename = file.filename
    safe_filename = get_safe_filename(original_filename)
    
    # Create base upload directory
    upload_dir = ensure_upload_dir()
    
    # Create subdirectory if specified
    if directory:
        upload_dir = os.path.join(upload_dir, directory)
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
    
    # Save the file
    file_path = os.path.join(upload_dir, safe_filename)
    file.save(file_path)
    
    # Get file details
    file_size = os.path.getsize(file_path)
    mime = magic.Magic(mime=True)
    mime_type = mime.from_file(file_path)
    
    return file_path, original_filename, safe_filename, file_size, mime_type

def calculate_file_hash(file_path, hash_algorithm="sha256"):
    """
    Calculate cryptographic hash of a file.
    
    Args:
        file_path (str): Path to the file
        hash_algorithm (str): Hash algorithm to use (sha256, md5, etc.)
        
    Returns:
        str: Hexadecimal digest of the file hash
    """
    try:
        hash_obj = hashlib.new(hash_algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except Exception as e:
        return f"Error calculating hash: {str(e)}"

# Add this new class for JSON serialization
class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle non-serializable types like Rational numbers from EXIF data.
    """
    def default(self, obj):
        # For PILs IFDRational type (used in EXIF data)
        if hasattr(obj, 'numerator') and hasattr(obj, 'denominator'):
            if obj.denominator == 0:
                return 0  # Avoid division by zero
            return float(obj.numerator) / float(obj.denominator)
        # For any other non-serializable types
        try:
            return str(obj)
        except:
            return None 