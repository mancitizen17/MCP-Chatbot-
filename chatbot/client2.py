import requests

def main():
    print("\n MCP Client - Ask me anything using multi-source knowledge! \n")

    while True:
        user_input = input("\n Your Question (or type 'exit'): \n")
        if user_input.lower() == "exit":
            break

        try:
            # Send user prompt to the server
            res = requests.post("http://localhost:5001/ask", json={"prompt": user_input})
            if res.status_code == 200:
                response = res.json()
                print("\n Answer:\n")
                print(response.get("answer", "No answer received from server."))
            else:
                print(f"❌ Server error {res.status_code}: {res.text}")
        except Exception as e:
            print(f"❌ Could not connect to MCP server: {e}")

if __name__ == "__main__":
    main()
