# Metadata Extractor

A powerful Flask application for extracting metadata from various file types.

## Features

- Extract metadata from multiple file types:
  - Images (PNG, JPG, GIF, BMP, TIFF, WebP)
  - Documents (PDF, DOCX, DOC, TXT, RTF)
  - Spreadsheets (XLSX, XLS, CSV)
  - Audio files (MP3, WAV, OGG, FLAC)
  - Video files (MP4, AVI, MOV, MKV)
- Store and manage uploaded files
- RESTful API for programmatic access
- User-friendly web interface
- Search and filter capabilities

## Installation

### Prerequisites

- **Python 3.10 or 3.11** (Python 3.13 is NOT compatible due to SQLAlchemy typing issues)
- PostgreSQL, MySQL, or SQLite database

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/metadata-extractor.git
   cd metadata-extractor
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Verify your Python version:
   ```
   python check_python_version.py
   ```
   This script will check if your Python version is compatible with the project.

4. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```

5. Create a `.env` file in the project root with the following configuration:
   ```
   FLASK_ENV=development
   FLASK_DEBUG=True
   SECRET_KEY=your-secret-key

   # Database configuration
   DB_ENGINE=postgresql  # or mysql
   DB_USER=
   DB_PASSWORD=
   DB_HOST=localhost
   DB_PORT=5432  # 3306 for MySQL
   DB_NAME=metadata_extractor

   # Flask configuration
   FLASK_HOST=0.0.0.0
   FLASK_PORT=5000
   ```

6. Create the database:
   ```
   # For PostgreSQL
   createdb metadata_extractor

   # For MySQL
   mysql -u root -p
   CREATE DATABASE metadata_extractor;
   ```

## Testing

### Test Gemini API Integration

To test if the Gemini API integration is working correctly:

```
python test_gemini.py
```

### Test Metadata Extraction

To test metadata extraction and analysis on a file:

```
python test_metadata.py path/to/your/file.jpg
```

Replace `path/to/your/file.jpg` with the path to the file you want to analyze.

## Running the Application

### Local Development

Run the Flask application:
```
python app.py
```

The application will automatically check if your Python version is compatible before starting. If you're using Python 3.13, the application will display an error message and exit.

The application will be available at http://localhost:5000


## API Documentation

MetaXtract provides a RESTful API for programmatic access.

### Endpoints

#### Extract Metadata
```
POST /api/extract
```
Parameters:
- `file` (required): File to upload
- `store` (optional): Whether to store the file and metadata (true/false)

Example:
```
curl -X POST -F "file=@path/to/your/file.jpg" -F "store=true" http://localhost:5000/api/extract
```

#### Analyze Metadata
```
POST /api/analyze
```
Parameters:
- `file_id` (required): ID of the file to analyze

Example:
```
curl -X POST -H "Content-Type: application/json" -d '{"file_id": 1}' http://localhost:5000/api/analyze
```

#### Get All Files
```
GET /api/files
```

Example:
```
curl -X GET http://localhost:5000/api/files
```

#### Get File Metadata
```
GET /api/files/{file_id}
```

Example:
```
curl -X GET http://localhost:5000/api/files/1
```

#### Get File Analysis
```
GET /api/files/{file_id}/analysis
```

Example:
```
curl -X GET http://localhost:5000/api/files/1/analysis
```

#### Delete File
```
DELETE /api/files/{file_id}
```

Example:
```
curl -X DELETE http://localhost:5000/api/files/1
```

## Supported File Types

- **Images**: PNG, JPG, JPEG, GIF, BMP, TIFF, WebP
- **Documents**: PDF, DOCX, DOC, TXT, RTF, ODT
- **Spreadsheets**: XLSX, XLS, CSV, ODS
- **Audio**: MP3, WAV, OGG, FLAC, AAC
- **Video**: MP4, AVI, MOV, MKV, WebM