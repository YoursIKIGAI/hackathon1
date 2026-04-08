from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import threading
import traceback
import sys
import os
import random
from dotenv import load_dotenv

load_dotenv()

# Port 5005 is used to bypass the stuck process on 5000
PORT = 5005

app = Flask(__name__)
# Enable CORS so the UI on port 5000 can talk to this API on port 5005
CORS(app)

# --- Local Model Initialization ---
LOCAL_MODEL_NAME = "microsoft/Phi-3.5-mini-instruct"
print(f"🚀 [GPU BRAIN] Activating NVIDIA RTX 4050 (Phi-3.5)...")

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, BitsAndBytesConfig
    import bitsandbytes as bnb
    
    # --- MONKEY PATCH FOR PHI-3.5 CRASH ---
    # Newer 'transformers' libraries removed get_max_length from DynamicCache, but Phi-3.5 still calls it.
    from transformers.cache_utils import DynamicCache
    if not hasattr(DynamicCache, "get_max_length"):
        DynamicCache.get_max_length = lambda self: 131072 # Phi-3.5 max context length
    # --------------------------------------
    
    # Check for NVIDIA GPU
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram = torch.cuda.mem_get_info(0)[1] / (1024**3)
        print(f"✅ NVIDIA GPU DETECTED: {gpu_name} ({vram:.1f}GB VRAM)")
        
        # Force the model exclusively onto the GPU to prevent slow CPU swapping
        device_map = {"": 0}
        
        # 4-bit quantization to fit comfortably in 6GB VRAM
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True
        )
    else:
        print("⚠️ NVIDIA GPU NOT DETECTED by Torch. Falling back to CPU.")
        device_map = {"": "cpu"}
        bnb_config = None
        
    # Initialize the local pipeline with GPU optimizations
    pipe = pipeline(
        "text-generation",
        model=LOCAL_MODEL_NAME,
        device_map=device_map,
        model_kwargs={
            "quantization_config": bnb_config,
            "attn_implementation": "eager"
        } if bnb_config else {"attn_implementation": "eager"},
        trust_remote_code=True
    )
    print("✅ GPU BRAIN INITIALIZED! No more OpenAI quota needed.")
    client = "local" # Sentinel for local inference
except Exception as e:
    print(f"DEBUG: Error Details: {str(e)}")
    print("ERROR: ML Libraries failed. Attempting CPU-only fallback...")
    try:
        from transformers import pipeline
        pipe = pipeline("text-generation", model=LOCAL_MODEL_NAME, device="cpu")
        client = "local"
        print("✅ CPU-ONLY FALLBACK SUCCESSFUL.")
    except Exception as e2:
        print(f"CRITICAL: CPU Fallback failed: {e2}")
        client = None

@app.route("/")
def index():
    # Still serves the index.html just in case the user goes to 5005 directly
    return render_template("index.html")

@app.route("/test_mic")
def test_mic():
    return """
    <html>
        <body>
            <h1>Minimal Mic Test</h1>
            <button id="btn" style="padding: 20px; font-size: 20px;">CLICK ME TO TEST MIC</button>
            <p id="status">Status: Waiting...</p>
            <script>
                document.getElementById('btn').onclick = async () => {
                    document.getElementById('status').innerText = "Status: Testing...";
                    try {
                        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                        alert("✅ SUCCESS: Microphone access granted!");
                        stream.getTracks().forEach(track => track.stop());
                    } catch (e) {
                        alert("❌ FAIL: " + e.name + " - " + e.message);
                    }
                };
            </script>
        </body>
    </html>
    """

conversation_history = []
SYSTEM_PROMPT = {"role": "system", "content": "You are Oumi, a friendly, concise voice assistant. Always reply directly in 1-2 short sentences. Do not analyze the prompt."}

@app.route("/api/chat", methods=["POST"])
def chat():
    global conversation_history
    
    data = request.json
    prompt = data.get("message", "")
    if not prompt:
        return jsonify({"error": "No message provided."}), 400
        
    print(f"\nUser asked (Local): {prompt}")
    
    if client is None:
        # Mock Response Fallback
        reply = "I'm hearing you, but my local brain isn't installed correctly yet. Please run the setup scripts!"
        print(f"Mock Replied: {reply}")
        return jsonify({"response": reply})
        
    try:
        # Add user's new message to memory
        conversation_history.append({"role": "user", "content": prompt})
        
        # Keep last 10 elements to prevent context overflow (5 turns max)
        if len(conversation_history) > 10:
            conversation_history = conversation_history[-10:]
            
        messages = [SYSTEM_PROMPT] + conversation_history
        
        print("Brain is thinking locally...")
        
        # Let pipeline handle the chat template and correct stop tokens automatically
        result = pipe(
            messages, 
            max_new_tokens=500, 
            do_sample=True,
            temperature=0.3,
        )
        
        # Pipeline returns the full message history, the newest response is the last item
        reply = result[0]['generated_text'][-1]['content'].strip()
        
        # Add Assistant response to memory
        conversation_history.append({"role": "assistant", "content": reply})
        
        print(f"AI Replied Locally: {reply}")
        return jsonify({"response": reply})
        
    except Exception as e:
        error_msg = f"Local Inference Error: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        return jsonify({"error": error_msg}), 500

if __name__ == "__main__":
    print(f"\n🚀 OUMI SERVER V2 STARTING ON PORT {PORT}")
    print(f"URL: http://127.0.0.1:{PORT}/")
    app.run(debug=True, port=PORT, use_reloader=False)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
