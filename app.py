import os
import sqlite3
from flask import Flask, request, jsonify, render_template_string
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

DB_PATH = "demo.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            profession TEXT NOT NULL
        )
    ''')
    conn.commit()
    return conn, cursor


def read_data(query="SELECT * FROM people"):
    conn, cursor = init_db()
    try:
        cursor.execute(query)
        return cursor.fetchall()
    except sqlite3.Error as e:
        return [f"Error: {e}"]
    finally:
        conn.close()


HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
<title>MCP Chatbot</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body { font-family: -apple-system, sans-serif; max-width: 700px; margin: 40px auto; padding: 0 16px; background:#0f172a; color:#e2e8f0;}
  h2 { text-align:center; }
  #chat { border:1px solid #334155; border-radius:10px; height:420px; overflow-y:auto; padding:14px; background:#1e293b;}
  .msg { margin:8px 0; padding:9px 13px; border-radius:10px; max-width:80%; line-height:1.4; }
  .user { background:#2563eb; margin-left:auto; text-align:right; }
  .bot { background:#334155; }
  #inputRow { display:flex; margin-top:12px; gap:8px; }
  #userInput { flex:1; padding:11px; border-radius:8px; border:1px solid #334155; background:#0f172a; color:#fff; font-size:15px; }
  button { padding:11px 18px; border:none; border-radius:8px; background:#2563eb; color:#fff; cursor:pointer; font-size:15px; }
  button:hover { background:#1d4ed8; }
</style>
</head>
<body>
<h2>MCP Chatbot</h2>
<div id="chat"></div>
<div id="inputRow">
  <input id="userInput" placeholder="Ask me something..." autofocus />
  <button onclick="sendMessage()">Send</button>
</div>
<script>
async function sendMessage() {
  const input = document.getElementById('userInput');
  const chat = document.getElementById('chat');
  const text = input.value.trim();
  if (!text) return;
  chat.innerHTML += `<div class="msg user">${text}</div>`;
  input.value = '';
  chat.scrollTop = chat.scrollHeight;

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text})
    });
    const data = await res.json();
    chat.innerHTML += `<div class="msg bot">${data.reply}</div>`;
  } catch (err) {
    chat.innerHTML += `<div class="msg bot">Error reaching server.</div>`;
  }
  chat.scrollTop = chat.scrollHeight;
}
document.getElementById('userInput').addEventListener('keydown', e => {
  if (e.key === 'Enter') sendMessage();
});
</script>
</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(HTML_PAGE)


@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "")

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant for a small demo database. "
                        "The database has a 'people' table with columns: id, name, age, profession."
                    ),
                },
                {"role": "user", "content": user_message},
            ],
        )
        reply = completion.choices[0].message.content
    except Exception as e:
        reply = f"Sorry, something went wrong: {e}"

    return jsonify({"reply": reply})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
