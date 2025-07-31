import sounddevice as sd
import queue
import sys
import json
import pyttsx3
import requests
from vosk import Model, KaldiRecognizer
from dotenv import load_dotenv
import os

load_dotenv()  # Load variables from .env file
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ====== CONFIG ======
MODEL_PATH = "vosk-model-small-en-us-0.15"  # Unzipped Vosk model folder
# =====================

q = queue.Queue()
engine = pyttsx3.init()
engine.setProperty('rate', 180)

def callback(indata, frames, time, status):
    q.put(bytes(indata))

# Function to send prompt to OpenAI and get a response
def get_ai_response(prompt):
    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print("API error:", e)
        return "Sorry, I had trouble thinking of a response."

# Load Vosk Model
try:
    model = Model(MODEL_PATH)
except Exception as e:
    print("Could not find Vosk model. Check MODEL_PATH.")
    sys.exit(1)

rec = KaldiRecognizer(model, 16000)

print("🎤 Say something! (Press Ctrl+C to exit)\n")

with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                       channels=1, callback=callback):
    try:
        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                spoken_text = result.get("text", "").strip()

                if spoken_text:
                    print(f"🗣 You: {spoken_text}")
                    response = get_ai_response(spoken_text)
                    print(f"🤖 AI: {response}")

                    engine.say(response)
                    engine.runAndWait()

    except KeyboardInterrupt:
        print("\n[Assistant] Session ended.")
        engine.say("Goodbye!")
        engine.runAndWait()
