import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure the Gemini API with the API key
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("GEMINI_API_KEY not found in environment variables. Please set it in .env file.")
    exit(1)

# Test the Gemini API
def test_gemini():
    try:
        # Create a model
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Generate content
        response = model.generate_content("Hello, what can you tell me about metadata in files?")
        
        # Print the response
        print("Response from Gemini API:")
        print(response.text)
        
        print("\nTest successful!")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_gemini()
