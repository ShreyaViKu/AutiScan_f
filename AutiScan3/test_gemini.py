import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get('GEMINI_API_KEY')
print("Key:", api_key)

if not api_key:
    print("No API Key found")
    exit(1)

genai.configure(api_key=api_key)

try:
    for m in genai.list_models():
        print(m.name)
except Exception as e:
    print("Error listing models:", e)

try:
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content('hi')
    print("Flash Response:", response.text)
except Exception as e:
    print("Error with flash:", e)

try:
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content('hi')
    print("Pro Response:", response.text)
except Exception as e:
    print("Error with pro:", e)
