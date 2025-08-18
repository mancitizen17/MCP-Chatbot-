# MCP-Chatbot 

An AI-powered chatbot built with Groq LLM, Flask, and LlamaIndex.  
It supports **tool calling** and interacts with a custom database using MCP.

---

## 🚀 Features
- Uses **Groq API** for fast and efficient LLM responses
- Supports **tool calling** with MCP
- Chat interface that can handle user queries
- Connects to a local database (`demo.db`)
- Environment variable support with `.env` for secure API keys

---

## 📂 Project Structure
mcp server/
│── chatbot/              # Core chatbot logic
│── OllamaClient.py       # Client for Groq + LlamaIndex
│── server.py             # Flask server
│── demo.db               # Sample database
│── netflix_titles.csv    # Example dataset
│── .gitignore
│── .env (not committed)  # API key goes here

---

## ⚙️ Setup

### 1. Clone the repo
```bash
git clone https://github.com/mancitizen17/MCP-Chatbot-.git
cd MCP-Chatbot-
```

### 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # On Mac/Linux
.venv\Scripts\activate      # On Windows

### 3. Install dependencies
pip install -r requirements.txt

### 4. Add your API Key
GROQ_API_KEY=your_real_api_key_here

### 5. Run the server
python server.py

### Tech Stack
Python
Flask
Groq API
LlamaIndex
SQLite (demo.db)
