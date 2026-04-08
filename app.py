from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import threading
import traceback
import sys
import os
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = "gpt-4o-mini"

app = Flask(__name__)
CORS(app)

print(f"Initializing OpenAI client...")

try:
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and api_key != "your_openai_api_key_here":
        client = OpenAI(api_key=api_key)
        print("OpenAI client initialized successfully!")
    else:
        print("WARNING: OPENAI_API_KEY is missing or placeholder. Running in MOCK MODE.")
        client = None
except Exception as e:
    print(f"Failed to load OpenAI client: {e}")
    client = None

@app.route("/")
def index():
    return render_template("index.html")

conversation_history = []
SYSTEM_PROMPT = {"role": "system", "content": "You are Oumi, a smart, conversational voice assistant. You MUST reply with the direct factual answer first, followed by exactly ONE short sentence of the most important context. Be extremely concise. Never write paragraphs."}

@app.route("/api/chat", methods=["POST"])
def chat():
    global conversation_history
    
    data = request.json
    prompt = data.get("message", "")
    if not prompt:
        return jsonify({"error": "No message provided."}), 400
        
    print(f"\nUser asked: {prompt}")
    
    if client is None:
        # Mock Response Fallback
        mock_replies = [
            "I'm Oumi, your AI assistant! (Mock Response: Please add your OpenAI API Key to .env to enable my full brain.)",
            "I can hear you! (Mock Response: Once you set your API_KEY, I'll be much smarter.)",
            "Ready to help! (Mock Response: I'm currently running in test mode without an API key.)"
        ]
        import random
        reply = random.choice(mock_replies)
        print(f"Mock Replied: {reply}")
        return jsonify({"response": reply})
        
    try:
        # Add user's new message to memory
        conversation_history.append({"role": "user", "content": prompt})
        
        # Keep last 10 elements to prevent context overflow (5 turns max)
        if len(conversation_history) > 10:
            conversation_history = conversation_history[-10:]
            
        messages = [SYSTEM_PROMPT] + conversation_history
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=250,
            temperature=0.1
        )
        reply = response.choices[0].message.content.strip()
        
        # Add Assistant response to memory
        conversation_history.append({"role": "assistant", "content": reply})
        
        print(f"AI Replied: {reply}")
        return jsonify({"response": reply})
        
    except Exception as e:
        error_msg = f"Inference Error: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        return jsonify({"error": error_msg}), 500

if __name__ == "__main__":
    # Enabled debug=True and use_reloader=True for easier development
    app.run(debug=True, port=5000, use_reloader=True)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
