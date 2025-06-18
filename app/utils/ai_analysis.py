"""
Utility module for AI analysis of metadata using Google's Gemini API.
"""
import os
import json
import datetime
import google.generativeai as genai
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure the Gemini API with the API key
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logging.warning("GEMINI_API_KEY not found in environment variables. AI analysis will not work.")

def analyze_metadata(metadata_dict, file_info):
    """
    Analyze metadata using Google's Gemini API.

    Args:
        metadata_dict (dict): The metadata to analyze
        file_info (dict): Basic file information

    Returns:
        dict: Analysis results including anomalies, privacy concerns, and summary
    """
    if not GEMINI_API_KEY:
        return {
            "error": "GEMINI_API_KEY not configured. Please add your Gemini API key to the .env file.",
            "status": "failed"
        }

    try:
        # Format the metadata for better readability
        formatted_metadata = json.dumps(metadata_dict, indent=2)

        # Create a prompt for Gemini
        prompt = f"""
        I have extracted metadata from a file with the following information:

        File name: {file_info.get('original_filename', 'Unknown')}
        File type: {file_info.get('mime_type', 'Unknown')}
        File size: {file_info.get('file_size', 'Unknown')} bytes

        Here is the extracted metadata:

        {formatted_metadata}

        Please analyze this metadata and provide the following:

        1. Anomalies: Does this metadata contain any anomalies or signs of tampering? If so, what are they?
        2. Privacy Concerns: Does this metadata contain any privacy-sensitive information that the user should be aware of?
        3. Summary: Provide a concise summary of the most important metadata information.

        Format your response as JSON with the following structure:
        {{
            "anomalies": {{
                "detected": true/false,
                "details": "Description of anomalies if any"
            }},
            "privacy_concerns": {{
                "detected": true/false,
                "details": "Description of privacy concerns if any"
            }},
            "summary": "A concise summary of the metadata"
        }}
        """

        # Generate content using Gemini
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content(prompt)

        # Parse the response
        try:
            # Try to extract JSON from the response
            response_text = response.text
            # Find JSON content (it might be wrapped in markdown code blocks)
            if "```json" in response_text:
                json_content = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_content = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_content = response_text

            analysis_result = json.loads(json_content)

            # Add timestamp and status
            analysis_result["timestamp"] = datetime.datetime.now().isoformat()
            analysis_result["status"] = "success"

            return analysis_result

        except json.JSONDecodeError:
            # If JSON parsing fails, return the raw text
            return {
                "error": "Failed to parse JSON response",
                "raw_response": response.text,
                "timestamp": datetime.datetime.now().isoformat(),
                "status": "partial"
            }

    except Exception as e:
        logging.error(f"Error in AI analysis: {str(e)}")
        return {
            "error": str(e),
            "timestamp": datetime.datetime.now().isoformat(),
            "status": "failed"
        }

def generate_report(metadata_dict, file_info, analysis_result):
    """
    Generate a formal HTML report based on metadata and AI analysis.

    Args:
        metadata_dict (dict): The metadata
        file_info (dict): Basic file information
        analysis_result (dict): AI analysis results

    Returns:
        str: HTML report content
    """
    try:
        # Get current date and time
        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        day_str = now.strftime("%A")
        time_str = now.strftime("%H:%M:%S")

        # Get summary from analysis result
        summary = analysis_result.get("summary", "No summary available")

        # Get anomalies and privacy concerns
        anomalies = analysis_result.get("anomalies", {})
        privacy_concerns = analysis_result.get("privacy_concerns", {})

        # Create formal HTML report with official styling based on logo.html
        html_report = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MetaXtract Report - {file_info.get('original_filename', 'Unknown File')}</title>
    <style>
        :root {{
            --accent-blue: #0099ff;
            --accent-light: #66c7ff;
            --accent-dark: #0066cc;
            --border-color: rgba(0, 0, 0, 0.1);
        }}

        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: black;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: white;
        }}

        .header {{
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid var(--accent-blue);
            padding-bottom: 15px;
        }}

        .logo-container {{
            margin-bottom: 15px;
        }}

        .logo {{
            font-size: 48px;
            font-weight: bold;
            color: black;
            margin-bottom: 5px;
        }}

        .logo span {{
            color: var(--accent-light);
        }}

        .tagline {{
            font-size: 16px;
            color: black;
            margin-top: 5px;
        }}

        .date-info {{
            margin-top: 15px;
            font-size: 14px;
            color: #666;
        }}

        .section {{
            margin-bottom: 25px;
        }}

        .section-title {{
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
            border-bottom: 1px solid var(--accent-blue);
            padding-bottom: 5px;
            color: var(--accent-dark);
        }}

        .file-info {{
            background-color: #f9f9f9;
            padding: 15px;
            border: 1px solid var(--border-color);
            border-radius: 5px;
            margin-bottom: 20px;
        }}

        .summary {{
            padding: 15px;
            border: 1px solid var(--border-color);
            border-radius: 5px;
            margin-bottom: 20px;
        }}

        .alert {{
            padding: 15px;
            border: 1px solid var(--border-color);
            border-radius: 5px;
            margin-bottom: 20px;
        }}

        .alert-warning {{
            border-left: 4px solid #ff9800;
        }}

        .alert-danger {{
            border-left: 4px solid #f44336;
        }}

        .footer {{
            margin-top: 30px;
            text-align: center;
            font-size: 12px;
            border-top: 1px solid var(--accent-blue);
            padding-top: 15px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo-container">
            <div class="logo">Meta<span>Xtract</span></div>
            <div class="tagline">Metadata Intelligence, Powered by AI</div>
        </div>
        <div class="date-info">
            Report generated on {day_str}, {date_str} at {time_str}
        </div>
    </div>

    <div class="section">
        <div class="section-title">File Information</div>
        <div class="file-info">
            <p><strong>Filename:</strong> {file_info.get('original_filename', 'Unknown')}</p>
            <p><strong>File Type:</strong> {file_info.get('mime_type', 'Unknown')}</p>
            <p><strong>File Size:</strong> {file_info.get('file_size', 'Unknown')} bytes</p>
            <p><strong>Upload Date:</strong> {file_info.get('uploaded_at', 'Unknown')}</p>
        </div>
    </div>

    <div class="section">
        <div class="section-title">AI Analysis Summary</div>
        <div class="summary">
            <p>{summary}</p>
        </div>
    </div>"""

        # Add anomalies section if detected
        if anomalies.get("detected"):
            html_report += f"""
    <div class="section">
        <div class="section-title">Anomalies Detected</div>
        <div class="alert alert-warning">
            <p>{anomalies.get("details", "No details available")}</p>
        </div>
    </div>"""

        # Add privacy concerns section if detected
        if privacy_concerns.get("detected"):
            html_report += f"""
    <div class="section">
        <div class="section-title">Privacy Concerns</div>
        <div class="alert alert-danger">
            <p>{privacy_concerns.get("details", "No details available")}</p>
        </div>
    </div>"""

        # Add footer and close HTML tags
        html_report += f"""
    <div class="footer">
        <p>Generated by MetaXtract using Google Gemini AI</p>
        <p>© {now.year} MetaXtract | Official Report</p>
    </div>
</body>
</html>"""

        return html_report

    except Exception as e:
        logging.error(f"Error generating report: {str(e)}")
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>MetaXtract Report - Error</title>
    <style>
        :root {{
            --accent-blue: #0099ff;
            --accent-light: #66c7ff;
        }}
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #000;
            margin: 40px;
            background-color: white;
        }}
        h1 {{
            border-bottom: 1px solid var(--accent-blue);
            padding-bottom: 10px;
            color: var(--accent-blue);
        }}
        .logo {{
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 20px;
        }}
        .logo span {{
            color: var(--accent-light);
        }}
    </style>
</head>
<body>
    <div class="logo">Meta<span>Xtract</span></div>
    <h1>Error Generating Report</h1>
    <p>An error occurred while generating the report: {str(e)}</p>
</body>
</html>"""
