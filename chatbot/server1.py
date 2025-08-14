from flask import Flask, request, jsonify
import os, json, csv, io, mysql.connector, requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# === Configuration ===
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "llama3-70b-8192"
DATA_DIR = "data"

# === MySQL Connection ===
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "mcp_user",
    "password": 1234,
    "database": "mcp_db"
}


def load_mysql_context() -> str:
    """
    (Unchanged) Load from MySQL 'system_logs'.
    """
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT component_name, status_message, timestamp FROM system_logs")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return "\n\n--- MySQL Logs ---\nNo logs found in system_logs table."

        output = "\n\n--- MySQL Logs ---\n"
        for row in rows:
            output += f"Component: {row[0]}, Status: {row[1]}, Time: {row[2]}\n"
        return output
    except mysql.connector.Error as err:
        return f"\n\n--- MySQL Logs ---\nFailed to fetch logs: {err}"


def load_sales_performance_data() -> str:
    """
    (Unchanged) Load from MySQL 'sales_performance_2024'.
    """
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM sales_performance_2024")
        rows = cursor.fetchall()
        conn.close()

        context = "\n\n--- Sales Performance Data (2024) ---\n"
        for row in rows:
            context += (
                f"{row['employee_name']} in {row['month']}: "
                f"{row['items_sold']} items sold, Revenue: ${row['revenue']}, Salary: ${row['salary']}\n"
            )
        return context
    except Exception as e:
        return f"\n\n--- Sales Performance Data ---\nError loading sales data: {str(e)}"


def load_files_from_folder(folder_path: str) -> str:
    """
    (Unchanged) Read .txt, .md, .json, .csv from a local folder.
    """
    full_context = ""
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if filename.endswith((".txt", ".md")):
            with open(file_path, "r", encoding="utf-8") as f:
                full_context += f"\n\n--- Content from {filename} ---\n{f.read()}"
        elif filename.endswith(".json"):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    full_context += f"\n\n--- JSON from {filename} ---\n{json.dumps(data, indent=2)}"
                except json.JSONDecodeError:
                    full_context += f"\n\n--- Skipped invalid JSON file: {filename} ---"
        elif filename.endswith(".csv"):
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                csv_data = "\n".join([", ".join(row) for row in reader])
                full_context += f"\n\n--- CSV from {filename} ---\n{csv_data}"
    return full_context


def query_groq(user_prompt: str, context: str) -> str:
    """
    (Unchanged) Send system+user messages to Groq API and return the assistant's reply.
    """
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that uses multi-source context to answer queries."},
            {"role": "user", "content": f"{context}\n\nQuestion: {user_prompt}"}
        ],
        "temperature": 0.4
    }

    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        raise Exception(f"Groq Error: {response.status_code}\n{response.text}")


@app.route("/ask", methods=["POST"])
def handle_query():
    """
    (Unchanged) Read from fixed DATA_DIR + MySQL, then call Groq.
    """
    data = request.get_json()
    user_prompt = data.get("prompt", "")

    # Combine all sources: file-based + MySQL + Sales Data
    file_context  = load_files_from_folder(DATA_DIR)
    mysql_context = load_mysql_context()
    sales_context = load_sales_performance_data()
    combined_context = file_context + mysql_context + sales_context

    try:
        answer = query_groq(user_prompt, combined_context)
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/ask_with_data", methods=["POST"])
def handle_query_with_data():
    """
    NEW endpoint: Accepts prompt + arbitrary data payloads (JSON, CSV, text, etc.)
    so that the client can send data on-the-fly, and the server will parse them
    into one “context” string before calling the LLM.
    """

    # Expecting a JSON body like:
    # {
    #   "prompt": "... your question ...",
    #   "data_payload": [
    #       {
    #         "filename": "sales_q1.csv",
    #         "content": "employee,month,items_sold,revenue,salary\nAlice,January,100,5000,3000\nBob,January,80,4000,2800\n..."
    #       },
    #       {
    #         "filename": "notes.txt",
    #         "content": "This is a note about the project background..."
    #       },
    #       {
    #         "filename": "config.json",
    #         "content": "{\"threshold\": 0.75, \"regions\": [\"US\", \"EU\"]}"
    #       }
    #       # ... any number of items ...
    #   ]
    # }
    #
    # Alternatively, you could also allow clients to send a 'data_type' field 
    # instead of filename (e.g. “data_type”: “application/json” + raw content). 
    # Here we use “filename” to infer type via its extension.

    payload = request.get_json()
    user_prompt = payload.get("prompt", "").strip()
    data_items = payload.get("data_payload", [])

    if not user_prompt:
        return jsonify({"error": "Missing 'prompt' in request"}), 400

    # Build a single “context” string from all uploaded data items:
    combined_context = ""

    for idx, item in enumerate(data_items):
        fname = item.get("filename", f"item_{idx}")
        raw_content = item.get("content", "")

        if not raw_content:
            # Skip empty content with a warning in context
            combined_context += f"\n\n--- Skipped empty item: {fname} ---\n"
            continue

        # Infer type based on filename extension (lowercased):
        lower = fname.lower()
        if lower.endswith(".json"):
            # Try to load JSON; if valid, pretty‐print it
            try:
                data_obj = json.loads(raw_content)
                pretty = json.dumps(data_obj, indent=2)
                combined_context += f"\n\n--- JSON from {fname} ---\n{pretty}"
            except json.JSONDecodeError:
                combined_context += f"\n\n--- Invalid JSON provided in {fname}; raw text used ---\n{raw_content}"

        elif lower.endswith(".csv"):
            # Parse CSV rows. We can either do a simple .split or use csv.reader:
            try:
                reader = csv.reader(io.StringIO(raw_content))
                rows = list(reader)
                # Re‐serialize it into a tab‐separated or comma‐separated block:
                csv_lines = "\n".join([", ".join(row) for row in rows])
                combined_context += f"\n\n--- CSV from {fname} ---\n{csv_lines}"
            except Exception as e:
                combined_context += f"\n\n--- Failed to parse CSV from {fname} (error: {e}); raw text used ---\n{raw_content}"

        elif lower.endswith((".txt", ".md")):
            # Plain text or markdown; just include as-is
            combined_context += f"\n\n--- Text from {fname} ---\n{raw_content}"

        else:
            # Fallback: include raw_content as “unknown format” under that filename
            combined_context += f"\n\n--- Unrecognized format ({fname}); raw content below ---\n{raw_content}"

    # (Optional) You can still append your MySQL + Sales logs if you want:
    # mysql_context = load_mysql_context()
    # sales_context = load_sales_performance_data()
    # combined_context += mysql_context + sales_context
    # combined_text += mysql_text + sales_text
    

    try:
        answer = query_groq(user_prompt, combined_context)
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # By default Flask binds to 127.0.0.1:5000. Change port or host if needed.
    app.run(port=5001)
