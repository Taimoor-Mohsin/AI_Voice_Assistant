import requests
payload = {
    "model": "mistral",
    "messages": [{"role": "user", "content": "hello"}],
    "stream": False
}
response = requests.post("http://localhost:11434/api/chat", json=payload)
print(response.json())
