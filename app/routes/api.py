from flask import Blueprint, request, jsonify, current_app, send_file
import os
import tempfile
import logging
from app.utils.file_utils import allowed_file, save_uploaded_file, CustomJSONEncoder
from app.utils.extractors import extract_metadata
from app.utils.ai_analysis import analyze_metadata, generate_report
from app.utils.metadata_cleaner import clean_metadata
from app.models.metadata import File, Metadata, AIAnalysis
from app.utils.database import get_db
import json

api_bp = Blueprint('api', __name__)

@api_bp.route('/extract', methods=['POST'])
def extract():
    """
    API endpoint to extract metadata from an uploaded file.

    Returns:
        JSON response with extracted metadata
    """
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': 'No file part in the request'
        }), 400

    file = request.files['file']

    # If user does not select file, browser submits an empty file
    if file.filename == '':
        return jsonify({
            'success': False,
            'error': 'No file selected'
        }), 400

    # Check if the file has an allowed extension
    if file and allowed_file(file.filename):
        try:
            # Save the uploaded file
            file_path, original_filename, safe_filename, file_size, mime_type = save_uploaded_file(file)

            # Get file extension
            file_extension = os.path.splitext(original_filename)[1].lower().lstrip('.')

            # Extract metadata
            metadata_dict = extract_metadata(file_path)

            # Store file and metadata in database if 'store' parameter is true
            store_in_db = request.form.get('store', 'false').lower() == 'true'
            file_id = None

            if store_in_db:
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

                # Create metadata record
                text_preview = metadata_dict.get('text_preview', '')
                extraction_time = metadata_dict.get('extraction_time_ms', 0)

                metadata_type = metadata_dict.get('extracted_by', '').replace('MetadataExtractor', '').lower()
                if not metadata_type:
                    metadata_type = 'generic'

                # Serialize metadata_dict using our custom encoder
                json_metadata = json.dumps(metadata_dict, cls=CustomJSONEncoder)
                json_metadata_dict = json.loads(json_metadata)

                db_metadata = Metadata(
                    file_id=db_file.id,
                    metadata_type=metadata_type,
                    metadata_json=json_metadata_dict,
                    extraction_duration=extraction_time,
                    extracted_text=text_preview
                )

                db.add(db_metadata)
                db.commit()
                file_id = db_file.id

            # Return the extracted metadata
            # Use the safe version of metadata that we've already converted
            if store_in_db:
                safe_metadata = json_metadata_dict
            else:
                # Convert metadata to safe JSON
                json_metadata = json.dumps(metadata_dict, cls=CustomJSONEncoder)
                safe_metadata = json.loads(json_metadata)

            response = {
                'success': True,
                'filename': original_filename,
                'file_size': file_size,
                'mime_type': mime_type,
                'metadata': safe_metadata
            }

            if file_id:
                response['file_id'] = file_id

            return jsonify(response)

        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    else:
        return jsonify({
            'success': False,
            'error': 'File type not allowed'
        }), 400

@api_bp.route('/files', methods=['GET'])
def get_files():
    """
    API endpoint to get list of files with extracted metadata.

    Returns:
        JSON response with file list
    """
    try:
        db = next(get_db())
        files = db.query(File).order_by(File.uploaded_at.desc()).all()

        file_list = []
        for file in files:
            file_list.append({
                'id': file.id,
                'filename': file.original_filename,
                'file_size': file.file_size,
                'mime_type': file.mime_type,
                'uploaded_at': file.uploaded_at.isoformat() if file.uploaded_at else None
            })

        return jsonify({
            'success': True,
            'count': len(file_list),
            'files': file_list
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/files/<int:file_id>', methods=['GET'])
def get_file_metadata(file_id):
    """
    API endpoint to get metadata for a specific file.

    Args:
        file_id (int): File ID

    Returns:
        JSON response with file metadata
    """
    try:
        db = next(get_db())
        file = db.query(File).filter(File.id == file_id).first()

        if not file:
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404

        metadata = db.query(Metadata).filter(Metadata.file_id == file_id).first()

        response = {
            'success': True,
            'file': {
                'id': file.id,
                'filename': file.original_filename,
                'file_size': file.file_size,
                'mime_type': file.mime_type,
                'file_extension': file.file_extension,
                'uploaded_at': file.uploaded_at.isoformat() if file.uploaded_at else None
            }
        }

        if metadata:
            response['metadata'] = {
                'type': metadata.metadata_type,
                'extraction_duration': metadata.extraction_duration,
                'extracted_at': metadata.extracted_at.isoformat() if metadata.extracted_at else None,
                'data': metadata.metadata_json
            }

            if metadata.extracted_text:
                response['metadata']['text_preview'] = metadata.extracted_text

            # Include AI analysis if available
            if metadata.ai_analysis:
                response['ai_analysis'] = {
                    'has_anomalies': metadata.ai_analysis.has_anomalies,
                    'has_privacy_concerns': metadata.ai_analysis.has_privacy_concerns,
                    'summary': metadata.ai_analysis.summary,
                    'analyzed_at': metadata.ai_analysis.analyzed_at.isoformat() if metadata.ai_analysis.analyzed_at else None,
                    'data': metadata.ai_analysis.analysis_json
                }

        return jsonify(response)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/files/<int:file_id>/analyze', methods=['POST'])
def analyze_file(file_id):
    """
    API endpoint to analyze metadata using Gemini AI.

    Args:
        file_id (int): File ID

    Returns:
        JSON response with analysis results
    """
    try:
        db = next(get_db())
        file = db.query(File).filter(File.id == file_id).first()

        if not file:
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404

        metadata = db.query(Metadata).filter(Metadata.file_id == file_id).first()

        if not metadata:
            return jsonify({
                'success': False,
                'error': 'Metadata not found for this file'
            }), 404

        # Check if analysis already exists
        existing_analysis = db.query(AIAnalysis).filter(AIAnalysis.metadata_id == metadata.id).first()

        # If force parameter is not set to true and analysis exists, return existing analysis
        force_analysis = request.args.get('force', 'false').lower() == 'true'
        if existing_analysis and not force_analysis:
            return jsonify({
                'success': True,
                'message': 'Analysis already exists',
                'analysis': {
                    'has_anomalies': existing_analysis.has_anomalies,
                    'has_privacy_concerns': existing_analysis.has_privacy_concerns,
                    'summary': existing_analysis.summary,
                    'analyzed_at': existing_analysis.analyzed_at.isoformat() if existing_analysis.analyzed_at else None,
                    'data': existing_analysis.analysis_json
                }
            })

        # Prepare file info for analysis
        file_info = {
            'id': file.id,
            'original_filename': file.original_filename,
            'file_size': file.file_size,
            'mime_type': file.mime_type,
            'file_extension': file.file_extension,
            'uploaded_at': file.uploaded_at.isoformat() if file.uploaded_at else None
        }

        # Perform AI analysis
        analysis_result = analyze_metadata(metadata.metadata_json, file_info)

        # Check if analysis was successful
        if analysis_result.get('status') == 'failed':
            error_message = analysis_result.get('error', 'Unknown error during analysis')
            logging.error(f"AI analysis failed: {error_message}")
            return jsonify({
                'success': False,
                'error': error_message,
                'analysis_result': analysis_result
            }), 500

        # Extract key information from analysis result
        has_anomalies = analysis_result.get('anomalies', {}).get('detected', False)
        has_privacy_concerns = analysis_result.get('privacy_concerns', {}).get('detected', False)
        summary = analysis_result.get('summary', 'No summary available')

        # Create or update AI analysis in database
        if existing_analysis:
            existing_analysis.analysis_json = analysis_result
            existing_analysis.has_anomalies = has_anomalies
            existing_analysis.has_privacy_concerns = has_privacy_concerns
            existing_analysis.summary = summary
            db.commit()
            analysis_id = existing_analysis.id
        else:
            new_analysis = AIAnalysis(
                metadata_id=metadata.id,
                analysis_json=analysis_result,
                has_anomalies=has_anomalies,
                has_privacy_concerns=has_privacy_concerns,
                summary=summary
            )
            db.add(new_analysis)
            db.commit()
            analysis_id = new_analysis.id

        return jsonify({
            'success': True,
            'message': 'Analysis completed successfully',
            'analysis_id': analysis_id,
            'analysis': {
                'has_anomalies': has_anomalies,
                'has_privacy_concerns': has_privacy_concerns,
                'summary': summary,
                'data': analysis_result
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/files/<int:file_id>/report', methods=['GET'])
def generate_file_report(file_id):
    """
    API endpoint to generate an HTML report for a file.

    Args:
        file_id (int): File ID

    Returns:
        HTML report or JSON error
    """
    try:
        db = next(get_db())
        file = db.query(File).filter(File.id == file_id).first()

        if not file:
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404

        metadata = db.query(Metadata).filter(Metadata.file_id == file_id).first()

        if not metadata:
            return jsonify({
                'success': False,
                'error': 'Metadata not found for this file'
            }), 404

        # Check if AI analysis exists
        analysis = db.query(AIAnalysis).filter(AIAnalysis.metadata_id == metadata.id).first()

        if not analysis:
            # If no analysis exists, create one
            file_info = {
                'id': file.id,
                'original_filename': file.original_filename,
                'file_size': file.file_size,
                'mime_type': file.mime_type,
                'file_extension': file.file_extension,
                'uploaded_at': file.uploaded_at.isoformat() if file.uploaded_at else None
            }

            analysis_result = analyze_metadata(metadata.metadata_json, file_info)

            # Check if analysis was successful
            if analysis_result.get('status') == 'failed':
                error_message = analysis_result.get('error', 'Unknown error during analysis')
                logging.error(f"AI analysis failed during report generation: {error_message}")
                return jsonify({
                    'success': False,
                    'error': error_message,
                    'details': 'Failed to generate AI analysis for the report. Please check your Gemini API key configuration.'
                }), 500

            # Extract key information from analysis result
            has_anomalies = analysis_result.get('anomalies', {}).get('detected', False)
            has_privacy_concerns = analysis_result.get('privacy_concerns', {}).get('detected', False)
            summary = analysis_result.get('summary', 'No summary available')

            # Create AI analysis in database
            analysis = AIAnalysis(
                metadata_id=metadata.id,
                analysis_json=analysis_result,
                has_anomalies=has_anomalies,
                has_privacy_concerns=has_privacy_concerns,
                summary=summary
            )
            db.add(analysis)
            db.commit()

        # Prepare file info for report
        file_info = {
            'id': file.id,
            'original_filename': file.original_filename,
            'file_size': file.file_size,
            'mime_type': file.mime_type,
            'file_extension': file.file_extension,
            'uploaded_at': file.uploaded_at.isoformat() if file.uploaded_at else None
        }

        # Generate HTML report
        html_report = generate_report(metadata.metadata_json, file_info, analysis.analysis_json)

        # Create a temporary file to store the HTML report
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as temp_file:
            temp_file.write(html_report.encode('utf-8'))
            temp_path = temp_file.name

        # Generate a filename for the report
        report_filename = f"MetaXtract_Report_{file.original_filename.split('.')[0]}.html"

        # Send the file as an attachment
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=report_filename,
            mimetype='text/html'
        )

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/files/<int:file_id>', methods=['DELETE'])
def delete_file(file_id):
    """
    API endpoint to delete a file and its metadata.

    Args:
        file_id (int): File ID

    Returns:
        JSON response indicating success or failure
    """
    try:
        db = next(get_db())
        file = db.query(File).filter(File.id == file_id).first()

        if not file:
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404

        # Delete the physical file
        if os.path.exists(file.file_path):
            os.remove(file.file_path)

        # Delete from database (cascade will delete metadata)
        db.delete(file)
        db.commit()

        return jsonify({
            'success': True,
            'message': f'File {file.original_filename} deleted successfully'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/files/<int:file_id>/clean-metadata', methods=['POST'])
def clean_file_metadata(file_id):
    """
    API endpoint to remove all metadata from a file.

    Args:
        file_id (int): File ID

    Returns:
        JSON response with cleaning results
    """
    try:
        db = next(get_db())
        file = db.query(File).filter(File.id == file_id).first()

        if not file:
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404

        # Check if file exists on disk
        if not os.path.exists(file.file_path):
            return jsonify({
                'success': False,
                'error': 'File not found on disk'
            }), 404

        # Clean metadata from the file
        success, message, cleaned_file_path = clean_metadata(file.file_path)

        if not success:
            return jsonify({
                'success': False,
                'error': message
            }), 400

        # Re-extract metadata to update the database
        metadata_dict = extract_metadata(file.file_path)

        # Update the metadata in the database
        metadata = db.query(Metadata).filter(Metadata.file_id == file_id).first()
        if metadata:
            # Update existing metadata
            metadata.metadata_json = metadata_dict
            db.commit()

        return jsonify({
            'success': True,
            'message': 'Metadata successfully removed from file',
            'details': message
        })

    except Exception as e:
        logging.error(f"Error cleaning metadata: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500