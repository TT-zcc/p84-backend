import os
from flask import Blueprint, jsonify, request
from dotenv import load_dotenv

# Loading environment variables
load_dotenv()

try:
    import google.generativeai as genai
except ImportError:
    genai = None

blueprint = Blueprint("ai", __name__, url_prefix="/ai")

# Configure API Key
API_KEY = os.getenv("GOOGLE_API_KEY")

if genai and API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel("models/gemini-2.5-flash-lite")
else:
    model = None

@blueprint.route("/ask", methods=["POST"])
def ask_ai():
    if model is None:
        return jsonify({"error": "Gemini model is not available or not configured."}), 500

    data = request.get_json()
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"error": "Missing question"}), 400

    try:
        response = model.generate_content(question)
        answer = response.text.strip()
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
