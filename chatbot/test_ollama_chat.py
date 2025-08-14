import requests

response = requests.post(
    #"http://localhost:11434/api/chat",
    json={
        "model": "codellama:7b-instruct",
        "messages": [
            {"role": "user", "content": "Tell me about the planet Earth"}
        ],
        "stream": False
    }
)

print(response.status_code)
print(response.json())
