from flask import Flask, request, jsonify
import os, json, csv, requests, mysql.connector
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)

# === Configuration ===
GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # API key from .env
MODEL = "llama3-70b-8192"
DATA_DIR = "data"

# === MySQL Connection ===
MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "mcp_user",
    "password": "1234",
    "database": "mcp_db",
    "auth_plugin": "mysql_native_password"
}

def load_mysql_context() -> str:
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
        print(f"❌ MySQL Connection Error: {err}")
        return f"\n\n--- MySQL Logs ---\nFailed to fetch logs: {err}"

def load_sales_performance_data() -> str:
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
        return f"Error loading sales data: {str(e)}"

def load_files_from_folder(folder_path: str) -> str:
    full_context = ""
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if filename.endswith((".txt", ".md")):
            with open(file_path, "r", encoding="utf-8") as file:
                full_context += f"\n\n--- Content from {filename} ---\n{file.read()}"
        elif filename.endswith(".json"):
            with open(file_path, "r", encoding="utf-8") as file:
                try:
                    data = json.load(file)
                    full_context += f"\n\n--- JSON from {filename} ---\n{json.dumps(data, indent=2)}"
                except json.JSONDecodeError:
                    full_context += f"\n\n--- Skipped invalid JSON file: {filename} ---"
        elif filename.endswith(".csv"):
            with open(file_path, "r", encoding="utf-8") as file:
                reader = csv.reader(file)
                csv_data = "\n".join([", ".join(row) for row in reader])
                full_context += f"\n\n--- CSV from {filename} ---\n{csv_data}"
    return full_context
 
def query_groq(user_prompt: str, context: str) -> str:
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
    data = request.get_json()
    user_prompt = data.get("prompt", "")

    # Combine all sources: file-based + MySQL + Sales Data
    file_context = load_files_from_folder(DATA_DIR)
    mysql_context = load_mysql_context()
    sales_context = load_sales_performance_data()
    combined_context = file_context + mysql_context + sales_context

    try:
        answer = query_groq(user_prompt, combined_context)
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5001)