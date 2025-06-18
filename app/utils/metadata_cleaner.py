"""
Utility module for removing metadata from various file types.
"""
import os
import logging
import tempfile
import shutil
from PIL import Image
import io
import PyPDF2
import docx
from docx.opc.constants import RELATIONSHIP_TYPE as RT

# Import specialized libraries
try:
    import pikepdf
    PIKEPDF_AVAILABLE = True
except ImportError:
    PIKEPDF_AVAILABLE = False

try:
    import mutagen
    from mutagen.mp3 import MP3
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4
    from mutagen.wave import WAVE
    from mutagen.oggvorbis import OggVorbis
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

try:
    from oletools import oleobj
    OLETOOLS_AVAILABLE = True
except ImportError:
    OLETOOLS_AVAILABLE = False


class MetadataCleaner:
    """Base class for metadata cleaning."""

    def clean(self, file_path):
        """
        Clean metadata from a file.

        Args:
            file_path (str): Path to the file

        Returns:
            tuple: (success, message, cleaned_file_path)
        """
        raise NotImplementedError("Subclasses must implement clean method")


class ImageMetadataCleaner(MetadataCleaner):
    """Clean metadata from image files."""

    def clean(self, file_path):
        """
        Remove all metadata from an image file.

        Args:
            file_path (str): Path to the image file

        Returns:
            tuple: (success, message, cleaned_file_path)
        """
        try:
            # Create a temporary file
            temp_fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(file_path)[1])
            os.close(temp_fd)

            # Open the image and save it without metadata
            with Image.open(file_path) as img:
                # Create a new image with the same content but without metadata
                data = list(img.getdata())
                img_without_exif = Image.new(img.mode, img.size)
                img_without_exif.putdata(data)
                
                # Save the new image
                img_without_exif.save(temp_path)

            # Replace the original file with the cleaned one
            shutil.move(temp_path, file_path)
            
            return True, "Successfully removed metadata from image", file_path
        except Exception as e:
            logging.error(f"Error cleaning image metadata: {str(e)}")
            # Clean up temp file if it exists
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
            return False, f"Error cleaning metadata: {str(e)}", file_path


class PDFMetadataCleaner(MetadataCleaner):
    """Clean metadata from PDF files."""

    def clean(self, file_path):
        """
        Remove all metadata from a PDF file.

        Args:
            file_path (str): Path to the PDF file

        Returns:
            tuple: (success, message, cleaned_file_path)
        """
        # Try with pikepdf first (more comprehensive)
        if PIKEPDF_AVAILABLE:
            try:
                # Create a temporary file
                temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
                os.close(temp_fd)
                
                # Open and clean the PDF with pikepdf
                with pikepdf.open(file_path) as pdf:
                    # Remove document info dictionary
                    pdf.docinfo.clear()
                    # Remove XMP metadata if present
                    if pdf.Root.get('/Metadata'):
                        del pdf.Root['/Metadata']
                    # Save the cleaned PDF
                    pdf.save(temp_path)
                
                # Replace the original file with the cleaned one
                shutil.move(temp_path, file_path)
                
                return True, "Successfully removed metadata from PDF using pikepdf", file_path
            except Exception as e:
                logging.error(f"Error cleaning PDF metadata with pikepdf: {str(e)}")
                # Clean up temp file if it exists
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    os.remove(temp_path)
                # Fall back to PyPDF2
        
        # Fallback to PyPDF2 if pikepdf is not available or failed
        try:
            # Create a temporary file
            temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
            os.close(temp_fd)
            
            # Open the original PDF
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                writer = PyPDF2.PdfWriter()
                
                # Copy all pages to the new PDF
                for page in reader.pages:
                    writer.add_page(page)
                
                # Don't copy the metadata
                # PyPDF2 doesn't copy metadata by default when creating a new PdfWriter
                
                # Write the cleaned PDF to the temporary file
                with open(temp_path, 'wb') as output_file:
                    writer.write(output_file)
            
            # Replace the original file with the cleaned one
            shutil.move(temp_path, file_path)
            
            return True, "Successfully removed metadata from PDF using PyPDF2", file_path
        except Exception as e:
            logging.error(f"Error cleaning PDF metadata with PyPDF2: {str(e)}")
            # Clean up temp file if it exists
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
            return False, f"Error cleaning metadata: {str(e)}", file_path


class DocxMetadataCleaner(MetadataCleaner):
    """Clean metadata from DOCX files."""

    def clean(self, file_path):
        """
        Remove all metadata from a DOCX file.

        Args:
            file_path (str): Path to the DOCX file

        Returns:
            tuple: (success, message, cleaned_file_path)
        """
        try:
            # Create a temporary file
            temp_fd, temp_path = tempfile.mkstemp(suffix='.docx')
            os.close(temp_fd)
            
            # Open the document
            doc = docx.Document(file_path)
            
            # Clear core properties
            core_props = doc.core_properties
            core_props.author = ""
            core_props.category = ""
            core_props.comments = ""
            core_props.content_status = ""
            core_props.created = None
            core_props.identifier = ""
            core_props.keywords = ""
            core_props.language = ""
            core_props.last_modified_by = ""
            core_props.last_printed = None
            core_props.modified = None
            core_props.revision = 1
            core_props.subject = ""
            core_props.title = ""
            core_props.version = ""
            
            # Save the cleaned document
            doc.save(temp_path)
            
            # Replace the original file with the cleaned one
            shutil.move(temp_path, file_path)
            
            return True, "Successfully removed metadata from DOCX", file_path
        except Exception as e:
            logging.error(f"Error cleaning DOCX metadata: {str(e)}")
            # Clean up temp file if it exists
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
            return False, f"Error cleaning metadata: {str(e)}", file_path


class AudioMetadataCleaner(MetadataCleaner):
    """Clean metadata from audio files."""

    def clean(self, file_path):
        """
        Remove all metadata from an audio file.

        Args:
            file_path (str): Path to the audio file

        Returns:
            tuple: (success, message, cleaned_file_path)
        """
        if not MUTAGEN_AVAILABLE:
            return False, "Mutagen library not available for audio metadata cleaning", file_path
        
        try:
            extension = os.path.splitext(file_path)[1].lower()
            
            # Handle different audio formats
            if extension == '.mp3':
                audio = MP3(file_path)
                audio.delete()
                audio.save()
            elif extension == '.flac':
                audio = FLAC(file_path)
                audio.delete()
                audio.save()
            elif extension == '.m4a' or extension == '.mp4':
                audio = MP4(file_path)
                audio.delete()
                audio.save()
            elif extension == '.wav':
                audio = WAVE(file_path)
                audio.delete()
                audio.save()
            elif extension == '.ogg':
                audio = OggVorbis(file_path)
                audio.delete()
                audio.save()
            else:
                # Try generic approach for other formats
                try:
                    audio = mutagen.File(file_path)
                    if audio:
                        audio.delete()
                        audio.save()
                    else:
                        return False, f"Unsupported audio format: {extension}", file_path
                except Exception as e:
                    return False, f"Error cleaning metadata from unsupported format: {str(e)}", file_path
            
            return True, f"Successfully removed metadata from audio file", file_path
        except Exception as e:
            logging.error(f"Error cleaning audio metadata: {str(e)}")
            return False, f"Error cleaning metadata: {str(e)}", file_path


def get_cleaner_for_file(file_path):
    """
    Determine the appropriate cleaner based on the file type.

    Args:
        file_path (str): Path to the file

    Returns:
        MetadataCleaner: An instance of the appropriate cleaner class
    """
    extension = os.path.splitext(file_path)[1].lower()
    
    # Image files
    if extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
        return ImageMetadataCleaner()
    
    # PDF files
    elif extension == '.pdf':
        return PDFMetadataCleaner()
    
    # DOCX files
    elif extension == '.docx':
        return DocxMetadataCleaner()
    
    # Audio files
    elif extension in ['.mp3', '.flac', '.m4a', '.wav', '.ogg']:
        return AudioMetadataCleaner()
    
    # Default to None for unsupported file types
    return None


def clean_metadata(file_path):
    """
    Clean metadata from a file using the appropriate cleaner.

    Args:
        file_path (str): Path to the file

    Returns:
        tuple: (success, message, cleaned_file_path)
    """
    cleaner = get_cleaner_for_file(file_path)
    if cleaner:
        return cleaner.clean(file_path)
    else:
        return False, "Unsupported file type for metadata cleaning", file_path
