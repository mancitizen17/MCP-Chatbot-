import os
import json
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
    """Run a read-only SELECT against demo.db and return real rows."""
    if not query.strip().lower().startswith("select"):
        return {"error": "Only SELECT queries are allowed for read_data."}
    conn, cursor = init_db()
    try:
        cursor.execute(query)
        columns = [d[0] for d in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        return {"columns": columns, "rows": rows}
    except sqlite3.Error as e:
        return {"error": str(e)}
    finally:
        conn.close()


def add_data(query: str):
    """Run an INSERT against demo.db."""
    if not query.strip().lower().startswith("insert"):
        return {"error": "Only INSERT statements are allowed for add_data."}
    conn, cursor = init_db()
    try:
        cursor.execute(query)
        conn.commit()
        return {"success": True, "rows_inserted": cursor.rowcount}
    except sqlite3.Error as e:
        return {"error": str(e)}
    finally:
        conn.close()


# Tool definitions the model can choose to call, in Groq/OpenAI function-calling format.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_data",
            "description": (
                "Run a SELECT SQL query against the 'people' table "
                "(columns: id, name, age, profession) and return the real matching rows."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A SQL SELECT statement, e.g. 'SELECT * FROM people WHERE age > 30'.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_data",
            "description": "Run an INSERT SQL statement to add a new row to the 'people' table.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A SQL INSERT statement targeting the 'people' table.",
                    }
                },
                "required": ["query"],
            },
        },
    },
]

AVAILABLE_TOOLS = {"read_data": read_data, "add_data": add_data}


HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
<title>MCP Console</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --ink: #12151c;
    --panel: #1a1e28;
    --panel-line: #2a2f3d;
    --amber: #e8a33d;
    --teal: #4fb8a8;
    --text: #e7e9ee;
    --text-dim: #8b91a1;
  }
  * { box-sizing: border-box; }
  body {
    font-family: 'Inter', sans-serif;
    background: var(--ink);
    background-image:
      radial-gradient(circle at 15% 10%, rgba(79,184,168,0.06), transparent 40%),
      radial-gradient(circle at 85% 90%, rgba(232,163,61,0.05), transparent 40%);
    color: var(--text);
    margin: 0;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
  }
  #app {
    width: 100%;
    max-width: 640px;
  }
  #statusbar {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 0 4px 14px;
  }
  #dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--teal);
    box-shadow: 0 0 0 0 rgba(79,184,168,0.6);
    animation: pulse 2.2s infinite;
  }
  @keyframes pulse {
    0%   { box-shadow: 0 0 0 0 rgba(79,184,168,0.55); }
    70%  { box-shadow: 0 0 0 7px rgba(79,184,168,0); }
    100% { box-shadow: 0 0 0 0 rgba(79,184,168,0); }
  }
  #title {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
    font-size: 17px;
    letter-spacing: -0.01em;
  }
  #subtitle {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    color: var(--text-dim);
    margin-left: auto;
  }
  #panel {
    background: var(--panel);
    border: 1px solid var(--panel-line);
    border-radius: 14px;
    overflow: hidden;
  }
  #chat {
    height: 440px;
    overflow-y: auto;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  #chat::-webkit-scrollbar { width: 8px; }
  #chat::-webkit-scrollbar-thumb { background: var(--panel-line); border-radius: 8px; }
  .row { display: flex; }
  .row.user { justify-content: flex-end; }
  .bubble {
    max-width: 78%;
    padding: 10px 14px;
    border-radius: 12px;
    font-size: 14.5px;
    line-height: 1.5;
  }
  .row.user .bubble {
    background: var(--amber);
    color: #23180a;
    border-bottom-right-radius: 3px;
  }
  .row.bot .bubble {
    background: #20242f;
    border: 1px solid var(--panel-line);
    border-left: 2px solid var(--teal);
    border-bottom-left-radius: 3px;
    color: var(--text);
  }
  .typing .bubble {
    display: flex;
    gap: 4px;
    align-items: center;
    padding: 13px 14px;
  }
  .typing span {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: var(--text-dim);
    animation: blink 1.3s infinite ease-in-out;
  }
  .typing span:nth-child(2) { animation-delay: 0.15s; }
  .typing span:nth-child(3) { animation-delay: 0.3s; }
  @keyframes blink {
    0%, 80%, 100% { opacity: 0.25; transform: scale(0.85); }
    40% { opacity: 1; transform: scale(1); }
  }
  #inputbar {
    display: flex;
    gap: 8px;
    padding: 14px;
    border-top: 1px solid var(--panel-line);
    background: #171b24;
  }
  #userInput {
    flex: 1;
    padding: 11px 13px;
    border-radius: 9px;
    border: 1px solid var(--panel-line);
    background: var(--ink);
    color: var(--text);
    font-family: 'Inter', sans-serif;
    font-size: 14.5px;
    outline: none;
  }
  #userInput:focus { border-color: var(--teal); }
  #userInput::placeholder { color: var(--text-dim); }
  #send {
    padding: 0 18px;
    border: none;
    border-radius: 9px;
    background: var(--amber);
    color: #23180a;
    font-weight: 600;
    font-size: 14px;
    cursor: pointer;
    transition: filter 0.15s ease;
  }
  #send:hover { filter: brightness(1.08); }
  #send:disabled { opacity: 0.5; cursor: default; }
  #hint {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11.5px;
    color: var(--text-dim);
    text-align: center;
    padding: 10px 0 0;
  }
</style>
</head>
<body>
<div id="app">
  <div id="statusbar">
    <div id="dot"></div>
    <div id="title">MCP Console</div>
    <div id="subtitle">demo.db · groq</div>
  </div>
  <div id="panel">
    <div id="chat"></div>
    <div id="inputbar">
      <input id="userInput" placeholder="Ask something..." autofocus />
      <button id="send" onclick="sendMessage()">Send</button>
    </div>
  </div>
  <div id="hint">first response may take a moment if the server was asleep</div>
</div>
<script>
function addBubble(role, html) {
  const chat = document.getElementById('chat');
  const row = document.createElement('div');
  row.className = 'row ' + role;
  row.innerHTML = `<div class="bubble">${html}</div>`;
  chat.appendChild(row);
  chat.scrollTop = chat.scrollHeight;
  return row;
}

async function sendMessage() {
  const input = document.getElementById('userInput');
  const button = document.getElementById('send');
  const text = input.value.trim();
  if (!text) return;

  addBubble('user', text);
  input.value = '';
  button.disabled = true;

  const typingRow = addBubble('bot', '');
  typingRow.classList.add('typing');
  typingRow.querySelector('.bubble').innerHTML = '<span></span><span></span><span></span>';

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: text})
    });
    const data = await res.json();
    typingRow.remove();
    addBubble('bot', data.reply);
  } catch (err) {
    typingRow.remove();
    addBubble('bot', 'Error reaching server.');
  }
  button.disabled = false;
  input.focus();
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


SYSTEM_PROMPT = {
    "role": "system",
    "content": (
                    "You are Supernova, a helpful assistant for a small demo database. "
        "The database has a 'people' table with columns: id, name, age, profession. "
        "You have tools (read_data, add_data) that run real queries against this database — "
        "always use them to answer questions about the data instead of guessing or making up rows. "
        "You were built for this MCP-Chatbot project by mansi. "
        "If the user asks your name, who made you, or what model/AI you are, "
        "respond only that you are Supernova, an assistant built for this project by mansi. "
        "Never mention ChatGPT, GPT, OpenAI, Groq, Ollama, or any underlying model/provider name, "
        "even if asked directly or indirectly. "
        "\n\n"
        "If the user asks about mansi (the creator of this project), you can share the following: "
        "Mansi Manoj Menon is a B.Tech in Computer Science and Engineering 2026 graduate "
        "from Nirma University, Ahmedabad. She was born and brought up in the UAE, and her family is "
        "originally from Kerala, India — she moved to Ahmedabad for university and currently lives there. "
        "She has interned as an AIML Engineer and has fun building chatbots, "
        "AI agents, and cloud/data-analytics systems using tools like AWS, Python, SQL, and "
        "Retrieval-Augmented Generation (RAG). She's AWS Certified (AI Practitioner) and has co-authored a "
        "book chapter on blockchain in genomics. Outside of tech, she loves dancing, crochet, and binge-"
        "watching movies ;p. Keep this friendly and conversational — don't recite it like a resume dump unless "
        "the user specifically asks for her full background."
    ),
}


@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "")
    messages = [SYSTEM_PROMPT, {"role": "user", "content": user_message}]

    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        response_message = completion.choices[0].message

        if response_message.tool_calls:
            messages.append(response_message)

            for tool_call in response_message.tool_calls:
                fn_name = tool_call.function.name
                try:
                    fn_args = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    fn_args = {}

                fn = AVAILABLE_TOOLS.get(fn_name)
                result = fn(**fn_args) if fn else {"error": f"Unknown tool: {fn_name}"}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": fn_name,
                    "content": json.dumps(result, default=str),
                })

            followup = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=messages,
            )
            reply = followup.choices[0].message.content
        else:
            reply = response_message.content

    except Exception as e:
        reply = f"Sorry, something went wrong: {e}"

    return jsonify({"reply": reply})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
