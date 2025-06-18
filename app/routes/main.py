from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, abort
from werkzeug.utils import secure_filename
import os
from app.utils.file_utils import allowed_file, save_uploaded_file, calculate_file_hash, CustomJSONEncoder
from app.utils.extractors import extract_metadata
from app.models.metadata import File, Metadata, AIAnalysis
from app.utils.database import get_db
from sqlalchemy.orm import Session
import logging
import json
import threading
import queue
import time

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page route."""
    # Get database session
    db = next(get_db())

    # Get most recent 3 files
    recent_files = db.query(File).order_by(File.uploaded_at.desc()).limit(3).all()

    # Get statistics for dashboard
    files_count = db.query(File).count()
    images_count = db.query(File).filter(File.mime_type.like('image/%')).count()
    docs_count = db.query(File).filter(
        (File.mime_type == 'application/pdf') |
        (File.mime_type.like('application/vnd.openxmlformats-officedocument.%')) |
        (File.mime_type.like('text/%'))
    ).count()

    # Count security alerts - files with steganography potential
    security_alerts = 0
    for file in db.query(File).all():
        metadata = db.query(Metadata).filter_by(file_id=file.id).first()
        if metadata and metadata.metadata_json:
            try:
                metadata_dict = metadata.metadata_json
                # Check for steganography analysis results
                if metadata_dict.get('steganography_analysis'):
                    analysis = metadata_dict['steganography_analysis']
                    # Check if any analysis returned concerning values
                    if analysis.get('lsb_analysis', {}).get('suspicious', False) or \
                       analysis.get('chi_square_analysis', {}).get('suspicious', False) or \
                       analysis.get('sample_pair_analysis', {}).get('suspicious', False):
                        security_alerts += 1
            except Exception:
                pass

    return render_template('index.html',
                          recent_files=recent_files,
                          files_count=files_count,
                          images_count=images_count,
                          docs_count=docs_count,
                          security_alerts=security_alerts)

@main_bp.route('/upload', methods=['GET', 'POST'])
def upload_file():
    """File upload route with timeout protection."""
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)

        file = request.files['file']

        # If user does not select file, browser submits an empty file
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)

        # Check if the file has an allowed extension
        if file and allowed_file(file.filename):
            try:
                # Save the uploaded file
                file_path, original_filename, safe_filename, file_size, mime_type = save_uploaded_file(file)

                # Get file extension
                file_extension = os.path.splitext(original_filename)[1].lower().lstrip('.')

                # Calculate file hash
                file_hash = calculate_file_hash(file_path)
                logging.info(f"Calculated file hash: {file_hash}")

                # Extract metadata with timeout
                result_queue = queue.Queue()

                def extract_with_timeout():
                    try:
                        metadata = extract_metadata(file_path)
                        # Add file hash to metadata
                        metadata['hash'] = file_hash
                        result_queue.put(('success', metadata))
                    except Exception as e:
                        logging.error(f"Error in metadata extraction thread: {str(e)}")
                        result_queue.put(('error', str(e)))

                # Start metadata extraction in a separate thread
                extraction_thread = threading.Thread(target=extract_with_timeout)
                extraction_thread.daemon = True
                extraction_thread.start()

                # Wait for the extraction to complete with a timeout
                MAX_WAIT_TIME = 30  # Maximum 30 seconds wait time
                extraction_thread.join(MAX_WAIT_TIME)

                metadata_dict = None
                if extraction_thread.is_alive():
                    # If thread is still running after timeout, proceed with minimal metadata
                    logging.warning(f"Metadata extraction timed out for file: {original_filename}")
                    metadata_dict = {
                        "extracted_by": "BasicFileInfo",
                        "file_info": {
                            "file_size": file_size,
                            "mime_type": mime_type,
                            "extension": file_extension,
                            "hash": file_hash
                        },
                        "extraction_duration": MAX_WAIT_TIME * 1000,
                        "extraction_status": "timeout",
                        "warning": "Metadata extraction timed out, only basic information is available"
                    }
                else:
                    # Get the result from the queue
                    try:
                        status, result = result_queue.get(block=False)
                        if status == 'success':
                            metadata_dict = result
                        else:
                            raise Exception(result)
                    except queue.Empty:
                        # This shouldn't happen if the thread completed
                        logging.error("Thread completed but no result in queue")
                        metadata_dict = {
                            "extracted_by": "BasicFileInfo",
                            "file_info": {
                                "file_size": file_size,
                                "mime_type": mime_type,
                                "extension": file_extension,
                                "hash": file_hash
                            },
                            "extraction_status": "error",
                            "error": "Unknown error in metadata extraction"
                        }

                # Store file and metadata in database
                db = next(get_db())

                # Create file record
                db_file = File(
                    filename=safe_filename,
                    original_filename=original_filename,
                    file_path=file_path,
                    file_size=file_size,
                    mime_type=mime_type,
                    file_extension=file_extension
                )
                db.add(db_file)
                db.flush()  # Get the file ID

                # Get text from different possible locations in metadata dict
                extracted_text = metadata_dict.get('extracted_text', '')
                if not extracted_text and 'text_preview' in metadata_dict:
                    extracted_text = metadata_dict.get('text_preview', '')

                # Log the extracted text for debugging
                logging.info(f"Extracted text length: {len(extracted_text)} characters")
                if len(extracted_text) > 0:
                    logging.info(f"First 100 chars: {extracted_text[:100]}...")

                extraction_time = metadata_dict.get('extraction_duration', metadata_dict.get('extraction_time_ms', 0))

                metadata_type = metadata_dict.get('extracted_by', '').replace('MetadataExtractor', '').lower()
                if not metadata_type:
                    metadata_type = 'generic'

                # Serialize metadata_dict using our custom encoder to handle non-serializable types
                json_metadata = json.dumps(metadata_dict, cls=CustomJSONEncoder)
                json_metadata_dict = json.loads(json_metadata)  # Convert back to dict with safe values

                db_metadata = Metadata(
                    file_id=db_file.id,
                    metadata_type=metadata_type,
                    metadata_json=json_metadata_dict,
                    extraction_duration=extraction_time,
                    extracted_text=extracted_text
                )

                db.add(db_metadata)
                db.commit()

                # Check if extraction timed out
                if metadata_dict.get('extraction_status') == 'timeout':
                    flash('File uploaded successfully. Metadata extraction took longer than expected, only basic information is available.', 'warning')
                else:
                    flash('File uploaded and metadata extracted successfully', 'success')

                # Redirect to file details page
                return redirect(url_for('main.file_details', file_id=db_file.id))

            except Exception as e:
                logging.error(f"Error processing upload: {str(e)}")
                flash(f'Error processing file: {str(e)}', 'error')
                return redirect(request.url)
        else:
            flash('File type not allowed', 'error')
            return redirect(request.url)

    return render_template('upload.html')

@main_bp.route('/files')
def file_list():
    """List all files with extracted metadata."""
    db = next(get_db())
    files = db.query(File).order_by(File.uploaded_at.desc()).all()
    return render_template('file_list.html', files=files)

@main_bp.route('/files/<int:file_id>')
def file_details(file_id):
    """Display file details and extracted metadata."""
    db = next(get_db())
    file = db.query(File).filter(File.id == file_id).first()
    if file is None:
        abort(404)
    metadata = db.query(Metadata).filter(Metadata.file_id == file_id).first()

    # Debug log to check metadata content
    if metadata:
        logging.info(f"Metadata found for file {file_id}: type={metadata.metadata_type}")

        # Check if extracted text is available
        if metadata.extracted_text:
            text_length = len(metadata.extracted_text)
            logging.info(f"Extracted text available: {text_length} characters")
            if text_length > 0:
                logging.info(f"Text sample: {metadata.extracted_text[:100]}...")
        else:
            logging.warning(f"No extracted text available for file {file_id}")

        # Ensure metadata_json is a Python dict (not a string)
        if isinstance(metadata.metadata_json, str):
            try:
                metadata.metadata_json = json.loads(metadata.metadata_json)
                logging.info("Converted metadata_json from string to dict")
            except Exception as e:
                logging.error(f"Error parsing metadata_json: {e}")

        # Check if AI analysis exists
        ai_analysis = db.query(AIAnalysis).filter(AIAnalysis.metadata_id == metadata.id).first()
        if ai_analysis:
            logging.info(f"AI analysis found for metadata {metadata.id}")
            metadata.ai_analysis = ai_analysis
        else:
            logging.info(f"No AI analysis found for metadata {metadata.id}")
    else:
        logging.warning(f"No metadata found for file {file_id}")

    return render_template('file_details.html', file=file, metadata=metadata)

@main_bp.route('/download/<int:file_id>')
def download_file(file_id):
    """Download the original file."""
    db = next(get_db())
    file = db.query(File).filter(File.id == file_id).first()
    if file is None:
        abort(404)

    # Get the directory and filename
    directory = os.path.dirname(file.file_path)
    filename = os.path.basename(file.file_path)

    return send_from_directory(directory, filename, as_attachment=True, download_name=file.original_filename)

@main_bp.route('/about')
def about():
    """About page."""
    return render_template('about.html')

@main_bp.route('/delete_file/<int:file_id>', methods=['POST'])
def delete_file(file_id):
    """Delete a file and its metadata."""
    try:
        db = next(get_db())
        file = db.query(File).filter(File.id == file_id).first()

        if file is None:
            flash('File not found', 'error')
            return redirect(url_for('main.file_list'))

        # Delete the physical file
        if os.path.exists(file.file_path):
            os.remove(file.file_path)

        # Store filename for flash message
        filename = file.original_filename

        # Delete from database (cascade will delete metadata)
        db.delete(file)
        db.commit()

        flash(f'File "{filename}" deleted successfully', 'success')
    except Exception as e:
        logging.error(f"Error deleting file: {str(e)}")
        flash(f'Error deleting file: {str(e)}', 'error')

    return redirect(url_for('main.file_list'))