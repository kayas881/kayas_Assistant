# test_model.py
import requests

url = "http://localhost:8008/generate"

payload = {
    "prompt": "Open Spotify and play some jazz",
    "system": "You are a helpful UI automation assistant. Break down user requests into tool calls.",
    "temperature": 0.1
}

print("⏳ Sending request... (This triggers model loading, so wait 1-2 mins)")
try:
    response = requests.post(url, json=payload)
    print("\n✅ Response Received:")
    print(response.json()["text"])
except Exception as e:
    print(f"❌ Error: {e}")