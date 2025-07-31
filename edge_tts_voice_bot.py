import sounddevice as sd
import queue
import sys
import json
import requests
import pyttsx3
import asyncio
import edge_tts
import pygame
import time
import os
from dotenv import load_dotenv
from vosk import Model, KaldiRecognizer

load_dotenv()  # Load variables from .env file
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ========== CONFIG ==========
MODEL_PATH = "vosk-model-small-en-us-0.15"
GROQ_MODEL = "llama3-8b-8192"  # Or use "mixtral-8x7b-32768"
# ============================

q = queue.Queue()

def callback(indata, frames, time, status):
    q.put(bytes(indata))

async def speak(text, voice="en-GB-LibbyNeural"):
    try:
        filename = "reply.mp3"

        # Wait if file exists
        while os.path.exists(filename):
            try:
                os.remove(filename)
                break
            except PermissionError:
                time.sleep(0.2)

        # Generate new MP3
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(filename)

        # Play MP3 using pygame
        pygame.mixer.init()
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()

        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

        # Unload and quit pygame mixer before deleting file
        pygame.mixer.music.unload()
        pygame.mixer.quit()

        # Now safe to delete the file
        os.remove(filename)

    except Exception as e:
        print("[TTS Error]:", e)
        
def ask_groq(prompt):
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print("[Groq API error]:", e)
        return "Sorry, I couldn't think of a good response."

# Load Vosk model
try:
    model = Model(MODEL_PATH)
except Exception:
    print("Vosk model not found. Make sure the MODEL_PATH is correct.")
    sys.exit(1)

rec = KaldiRecognizer(model, 16000)

print("🎤 Say something! (Ctrl+C to exit)\n")

with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                       channels=1, callback=callback):
    try:
        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                spoken = result.get("text", "").strip()

                if spoken:
                    print(f"🗣 You: {spoken}")
                    reply = ask_groq(spoken)
                    print(f"🤖 AI: {reply}")
                    asyncio.run(speak(reply))

    except KeyboardInterrupt:
        print("\n[Assistant] Goodbye.")
        asyncio.run(speak("Goodbye. Talk to you later!"))