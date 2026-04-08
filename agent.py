import speech_recognition as sr
import pyttsx3
import sys
import re

# Using Local Microsoft Phi-3.5-mini-instruct
MODEL_NAME = "microsoft/Phi-3.5-mini-instruct"

def speak(text, engine):
    """Uses pyttsx3 to speak the generated text."""
    print(f"Agent speaking: {text}")
    engine.say(text)
    engine.runAndWait()

def initialize_local_brain():
    import torch
    from transformers import pipeline, BitsAndBytesConfig
    
    print(f"🚀 [GPU BRAIN] Initializing {MODEL_NAME} for your RTX 4050...")
    
    try:
        # Check for NVIDIA GPU
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            print(f"✅ NVIDIA GPU DETECTED: {gpu_name}")
            device_map = "auto"
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True
            )
            model_kwargs = {"quantization_config": bnb_config, "attn_implementation": "sdpa"}
        else:
            print("⚠️ NVIDIA GPU NOT DETECTED. Running on CPU (Slower).")
            device_map = {"": "cpu"}
            bnb_config = None
            model_kwargs = {}

        pipe = pipeline(
            "text-generation",
            model=MODEL_NAME,
            device_map=device_map,
            model_kwargs=model_kwargs,
            trust_remote_code=True
        )
        return pipe
    except Exception as e:
        print(f"Failed to load GPU brain: {e}")
        return None

def generate_text(pipe, prompt):
    """Uses Local Model to generate a response."""
    print("Agent is thinking locally...")
    
    if pipe is None:
        return "I'm sorry, my local brain isn't initialized. Try running 'pip install torch transformers'."
        
    try:
        # FIX 1: Use apply_chat_template for correct Phi-3.5 formatting
        messages = [
            {"role": "system", "content": "You are a helpful AI assistant. Give concise, direct answers."},
            {"role": "user", "content": prompt}
        ]
        full_prompt = pipe.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # FIX 2: Safely build terminators - skip None IDs to prevent crashes
        end_token = pipe.tokenizer.convert_tokens_to_ids("<|end|>")
        eot_token = pipe.tokenizer.convert_tokens_to_ids("<|eot_id|>")
        terminators = [t for t in [pipe.tokenizer.eos_token_id, end_token, eot_token] if t is not None]

        result = pipe(
            full_prompt,
            max_new_tokens=150,
            do_sample=True,
            temperature=0.7,
            repetition_penalty=1.1,
            eos_token_id=terminators,
            pad_token_id=pipe.tokenizer.eos_token_id,
            return_full_text=False
        )

        text_output = result[0]["generated_text"]

        # FIX 3: Strip all leftover special/control tokens from output
        text_output = re.sub(r"<\|[^|]+\|>", "", text_output).strip()

        return text_output if text_output else "I could not generate a response. Please try again."
    except Exception as e:
        return f"I had an error thinking locally: {e}"

def main():
    print("Welcome to the Oumi Voice Agent!")

    # Initialize TTS Engine
    tts_engine = pyttsx3.init()
    tts_engine.setProperty("rate", 150)

    # FIX 4: Select a natural-sounding voice if available
    voices = tts_engine.getProperty("voices")
    if voices:
        tts_engine.setProperty("voice", voices[0].id)

    # Initialize Local Brain
    pipe = initialize_local_brain()

    # FIX 5: Removed duplicate 'import speech_recognition as sr' (already imported at top)
    recognizer = sr.Recognizer()

    try:
        mic_list = sr.Microphone.list_microphone_names()
        print(f"Detected Audio Devices: {len(mic_list)}")

        if len(mic_list) == 0:
            print("ERROR: No microphone detected! Please check Windows Privacy Settings.")
            sys.exit(1)

        microphone = sr.Microphone()
        print("Microphone initialized successfully!")
    except Exception as e:
        print(f"CRITICAL: Failed to initialize audio system: {e}")
        print("Tip: Make sure PyAudio is installed. Run: pip install pyaudio")
        sys.exit(1)

    print("\nInitialization complete! You can start talking now.")
    speak("Hello! I am ready.", tts_engine)

    try:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            while True:
                print("\nListening...")
                try:
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)
                    text = recognizer.recognize_google(audio)
                    print(f"You said: {text}")

                    if text.lower() in ["exit", "quit", "stop", "goodbye"]:
                        speak("Goodbye!", tts_engine)
                        break

                    response = generate_text(pipe, text)
                    if response:
                        speak(response, tts_engine)

                except sr.WaitTimeoutError:
                    pass  # Just listen again
                except sr.UnknownValueError:
                    print("Could not understand the audio.")
                except sr.RequestError as e:
                    print(f"Could not request results from STT service: {e}")

    except KeyboardInterrupt:
        print("\nStopping Voice Agent...")
        speak("Shutting down.", tts_engine)
        sys.exit(0)

if __name__ == "__main__":
    main()
