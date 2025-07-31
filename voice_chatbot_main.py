import asyncio
import edge_tts
import pygame
import os
import time
import requests
import json
from dotenv import load_dotenv

# ========== CONFIGURATION ==========
# Since HF API has widespread 404 issues, we'll use multiple alternatives
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

#Option 1: OpenAI API (requires API key from openai.com)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
USE_OPENAI = False  # Set to True if you have an OpenAI API key

# Option 2: Ollama (local AI - free but requires installation)
OLLAMA_BASE_URL = "http://localhost:11434"  # Default Ollama URL
USE_OLLAMA = False  # Set to True if you have Ollama installed

# Option 3: Groq API (free tier available)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
USE_GROQ = True  # Set to True if you have a Groq API key

VOICE = "en-US-AvaNeural"
STYLE = "cheerful"
MAX_TURNS = 4
# ===================================

def query_openai(user_message, conversation_history=[]):
    """Query OpenAI API"""
    if not OPENAI_API_KEY:
        return "[ERROR] OpenAI API key not provided"
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    messages = [{"role": "system", "content": "You are a helpful, friendly AI assistant. Keep responses concise and conversational."}]
    
    for turn in conversation_history[-MAX_TURNS:]:
        messages.append({"role": "user", "content": turn["user"]})
        messages.append({"role": "assistant", "content": turn["ai"]})
    
    messages.append({"role": "user", "content": user_message})
    
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": messages,
        "max_tokens": 150,
        "temperature": 0.7
    }
    
    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", 
                               headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            return f"[ERROR] OpenAI API: {response.status_code} - {response.text[:100]}"
    except Exception as e:
        return f"[ERROR] OpenAI API error: {e}"

def query_ollama(user_message, conversation_history=[]):
    """Query local Ollama installation"""
    try:
        # Check if Ollama is running
        health_response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if health_response.status_code != 200:
            return "[ERROR] Ollama not running. Start it with 'ollama serve'"
    except:
        return "[ERROR] Ollama not available. Install from https://ollama.ai/"
    
    # Build conversation context
    context = "You are a helpful, friendly AI assistant. Keep responses concise and conversational.\n\n"
    for turn in conversation_history[-MAX_TURNS:]:
        context += f"Human: {turn['user']}\nAssistant: {turn['ai']}\n\n"
    context += f"Human: {user_message}\nAssistant:"
    
    payload = {
        "model": "llama3.2:3b",  # Change to any model you have installed
        "prompt": context,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 150
        }
    }
    
    try:
        response = requests.post(f"{OLLAMA_BASE_URL}/api/generate", 
                               json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            return result["response"].strip()
        else:
            return f"[ERROR] Ollama: {response.status_code} - {response.text[:100]}"
    except Exception as e:
        return f"[ERROR] Ollama error: {e}"

#One being used currently
def query_groq(user_message, conversation_history=[]):
    """Query Groq API"""
    if not GROQ_API_KEY:
        return "[ERROR] Groq API key not provided"
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    messages = [{"role": "system", "content": "You are a helpful, friendly AI assistant. Keep responses concise and conversational."}]
    
    for turn in conversation_history[-MAX_TURNS:]:
        messages.append({"role": "user", "content": turn["user"]})
        messages.append({"role": "assistant", "content": turn["ai"]})
    
    messages.append({"role": "user", "content": user_message})
    
    payload = {
        "model": "llama3-8b-8192",  # Fast Groq model
        "messages": messages,
        "max_tokens": 150,
        "temperature": 0.7
    }
    
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", 
                               headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            return f"[ERROR] Groq API: {response.status_code} - {response.text[:100]}"
    except Exception as e:
        return f"[ERROR] Groq API error: {e}"

def query_ai(user_message, conversation_history=[]):
    """Try different AI services in order of preference"""
    
    # Try Ollama first (local, free, private)
    if USE_OLLAMA:
        print("[DEBUG] Trying Ollama...")
        response = query_ollama(user_message, conversation_history)
        if not response.startswith("[ERROR]"):
            return response
        print(f"Ollama failed: {response}")
    
    # Try Groq (free tier, fast)
    if USE_GROQ:
        print("[DEBUG] Trying Groq...")
        response = query_groq(user_message, conversation_history)
        if not response.startswith("[ERROR]"):
            return response
        print(f"Groq failed: {response}")
    
    # Try OpenAI (paid, reliable)
    if USE_OPENAI:
        print("[DEBUG] Trying OpenAI...")
        response = query_openai(user_message, conversation_history)
        if not response.startswith("[ERROR]"):
            return response
        print(f"OpenAI failed: {response}")
    
    return "[ERROR] All AI services failed. Please configure at least one API service."

def play_mp3(filename):
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    except Exception as e:
        print(f"[AUDIO ERROR]: {e}")
    finally:
        try:
            os.remove(filename)
        except Exception:
            pass

async def speak_edge(text, voice=VOICE):#, style=STYLE)
    filename = f"tts_reply_{int(time.time() * 1000)}.mp3"
    try:
        # Clean text for TTS
        clean_text = text
        if text.startswith("[ERROR]") or text.startswith("[DEBUG]"):
            clean_text = "Sorry, there was an error processing your request."
        
        communicate = edge_tts.Communicate(clean_text, voice=voice)
        await communicate.save(filename)
        play_mp3(filename)
    except Exception as e:
        print(f"[TTS ERROR]: {e}")

def setup_guide():
    """Show setup instructions for different AI services"""
    print("=== AI Service Setup Guide ===\n")
    
    print("🤖 OPTION 1: Ollama (Recommended - Free & Local)")
    print("1. Install Ollama from https://ollama.ai/")
    print("2. Run: ollama pull llama3.2:3b")
    print("3. Run: ollama serve")
    print("4. Set USE_OLLAMA = True in the code")
    print("✅ Pros: Free, private, no API keys needed")
    print("❌ Cons: Requires local installation, uses disk space\n")
    
    print("🚀 OPTION 2: Groq (Fast & Free Tier)")
    print("1. Sign up at https://console.groq.com/")
    print("2. Get API key from https://console.groq.com/keys")
    print("3. Set GROQ_API_KEY in the code")
    print("4. Set USE_GROQ = True")
    print("✅ Pros: Very fast, generous free tier")
    print("❌ Cons: Requires account, rate limits\n")
    
    print("💰 OPTION 3: OpenAI (Paid but Reliable)")
    print("1. Sign up at https://platform.openai.com/")
    print("2. Add credit to your account")
    print("3. Get API key from https://platform.openai.com/api-keys")
    print("4. Set OPENAI_API_KEY in the code")
    print("5. Set USE_OPENAI = True")
    print("✅ Pros: Most reliable, high quality")
    print("❌ Cons: Costs money per request\n")

def test_services():
    """Test which AI services are available"""
    print("🔍 Testing available AI services...\n")
    
    available_services = []
    
    if USE_OLLAMA:
        try:
            response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                if models:
                    print(f"✅ Ollama is running with {len(models)} models")
                    available_services.append("Ollama")
                else:
                    print("⚠️ Ollama running but no models installed")
            else:
                print("❌ Ollama not responding")
        except:
            print("❌ Ollama not available")
    
    if USE_GROQ and GROQ_API_KEY:
        test_response = query_groq("Hello", [])
        if not test_response.startswith("[ERROR]"):
            print("✅ Groq API working")
            available_services.append("Groq")
        else:
            print(f"❌ Groq API failed: {test_response[:50]}...")
    
    if USE_OPENAI and OPENAI_API_KEY:
        test_response = query_openai("Hello", [])
        if not test_response.startswith("[ERROR]"):
            print("✅ OpenAI API working")
            available_services.append("OpenAI")
        else:
            print(f"❌ OpenAI API failed: {test_response[:50]}...")
    
    return available_services

def main():
    print("=== Voice Assistant (HuggingFace Alternative) ===\n")
    
    # Test available services
    available = test_services()
    
    if not available:
        print("\n❌ No AI services are configured or working!")
        setup_guide()
        return
    
    print(f"\n✅ Available services: {', '.join(available)}")
    print("\nType your question (Ctrl+C to quit):")
    
    history = []
    
    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            
            ai_reply = query_ai(user_input, history)
            print("AI:", ai_reply)
            
            # Only speak and save to history if we got a valid response
            if not ai_reply.startswith("[ERROR]"):
                asyncio.run(speak_edge(ai_reply, VOICE))
                history.append({"user": user_input, "ai": ai_reply})
            else:
                print("Try configuring one of the AI services above.")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()