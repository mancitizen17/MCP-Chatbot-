from flask import Flask, request, render_template
import mysql.connector
import requests
import json
import re
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# -------------------- 1. Database Connection --------------------
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host='18.158.132.26',
            user='mcp_chatbot',
            password='StrongCHatMcpPassword123!',
            database='flatbeeGermany',
            port=3306,
            auth_plugin='mysql_native_password'
        )
        return conn
    except mysql.connector.Error as err:
        print(f"❌ DB Error: {err}")
        return None

# -------------------- 2. Generate SQL from Prompt --------------------
def generate_sql_from_prompt(prompt, model, api_key):
    import requests
    import re

    # --- Table schema description ---
    schema = """
    Table: crawl_soft_properties_1
    Columns:
      - address (varchar)
      - avg (double)
      - balcony (integer)
      - carousel (tinyint)
      - commission (tinyint)
      - crawl_soft_id (integer)
      - created (datetime)
      - district (varchar)
      - district_id (integer)
      - flag (varchar)
      - garage (integer)
      - hits (integer)
      - id (integer)
      - interestedin_purchase (integer)
      - lat (varchar)
      - lng (varchar)
      - modified (datetime)
      - no_wish_mail_sent (integer)
      - noaddress (tinyint)
      - nonserious (integer)
      - nonserious_w_u (integer)
      - onoff_prop_no (varchar)
      - p_type_id (integer)
      - parking (integer)
      - place (varchar)
      - point_premium (tinyint)
      - portal (integer)
      - price (double)
      - price_varient (double)
      - property_detail (text)
      - property_image (varchar)
      - property_title (text)
      - reason_real_sales (integer)
      - register_count (integer)
      - rooms (integer)
      - share (integer)
      - state (varchar)
      - state_id (integer)
      - terrace (integer)
      - test_property (tinyint)
      - total_living_area (double)
      - type (varchar)
      - type_name (varchar)
      - u_key (char)
      - zipcode (varchar)
    """

    # --- Diverse and detailed examples ---
    examples = """
    Example 1:
    Q: Show all properties with more than 2 rooms and a balcony in Munich.
    A: SELECT * FROM crawl_soft_properties_1 WHERE rooms > 2 AND balcony = 1 AND address LIKE '%Munich%';

    Example 2:
    Q: What is the average price for properties in district_id 5?
    A: SELECT AVG(price) FROM crawl_soft_properties_1 WHERE district_id = 5;

    Example 3:
    Q: List all properties available for purchase (interestedin_purchase = 1) with a garage.
    A: SELECT * FROM crawl_soft_properties_1 WHERE interestedin_purchase = 1 AND garage = 1;

    Example 4:
    Q: Show the addresses and prices of properties in Berlin with rent below 1200.
    A: SELECT address, price FROM crawl_soft_properties_1 WHERE address LIKE '%Berlin%' AND price < 1200;

    Example 5:
    Q: How many properties have a terrace and parking?
    A: SELECT COUNT(*) FROM crawl_soft_properties_1 WHERE terrace = 1 AND parking = 1;

    Example 6:
    Q: List property_title and price for properties with more than 100 square meters of living area.
    A: SELECT property_title, price FROM crawl_soft_properties_1 WHERE total_living_area > 100;

    Example 7:
    Q: Show all properties created after 2024-01-01.
    A: SELECT * FROM crawl_soft_properties_1 WHERE created > '2024-01-01';

    Example 8:
    Q: What is the maximum price of a property in zipcode 80331?
    A: SELECT MAX(price) FROM crawl_soft_properties_1 WHERE zipcode = '80331';

    Example 9:
    Q: List all properties in state 'Bavaria' with more than 3 rooms and a balcony or terrace.
    A: SELECT * FROM crawl_soft_properties_1 WHERE state = 'Bavaria' AND rooms > 3 AND (balcony = 1 OR terrace = 1);

    Example 10:
    Q: How many properties have been registered more than 10 times?
    A: SELECT COUNT(*) FROM crawl_soft_properties_1 WHERE register_count > 10;

    Example 11:
    Q: Show all properties where the price is between 1000 and 2000.
    A: SELECT * FROM crawl_soft_properties_1 WHERE price BETWEEN 1000 AND 2000;

    Example 12:
    Q: List the property_title, address, and price of the top 5 most expensive properties.
    A: SELECT property_title, address, price FROM crawl_soft_properties_1 ORDER BY price DESC LIMIT 5;

    Example 13:
    Q: Find properties with 'garden' in the property_detail.
    A: SELECT * FROM crawl_soft_properties_1 WHERE property_detail LIKE '%garden%';

    Example 14:
    Q: What is the average number of rooms for properties in district 'Charlottenburg'?
    A: SELECT AVG(rooms) FROM crawl_soft_properties_1 WHERE district = 'Charlottenburg';

    Example 15:
    Q: List all properties with no address information.
    A: SELECT * FROM crawl_soft_properties_1 WHERE noaddress = 1;

    Example 16:
    Q: Show the number of properties for each portal.
    A: SELECT portal, COUNT(*) FROM crawl_soft_properties_1 GROUP BY portal;

    Example 17:
    Q: List all properties with a price_varient greater than 0.
    A: SELECT * FROM crawl_soft_properties_1 WHERE price_varient > 0;

    Example 18:
    Q: Show the latest modified property.
    A: SELECT * FROM crawl_soft_properties_1 ORDER BY modified DESC LIMIT 1;

    Example 19:
    Q: What is the lowest price for a property in state_id 2?
    A: SELECT MIN(price) FROM crawl_soft_properties_1 WHERE state_id = 2;

    Example 20:
    Q: List properties with more than 2 balconies (if balcony is a count).
    A: SELECT * FROM crawl_soft_properties_1 WHERE balcony > 2;

    Example 21:
    Q: What is the lowest rent for a property in state_id 2?
    A: SELECT MIN(price) FROM crawl_soft_properties_1 WHERE state_id = 2;

    Example 22:
    Q: Show me properties that are rented
    A: SELECT * FROM crawl_soft_properties_1 WHERE type= 'Rent' ;

    """

    system_message = f"""
    You are a helpful assistant that translates natural language into SQL queries for a MySQL database.
    The relevant table is:
    {schema}
    Here are some examples:
    {examples}
    ONLY return the raw SQL query.
    """

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt}
    ]
    data = {
        "model": model,
        "messages": messages,
        "temperature": 0.3
    }

    try:
        response = requests.post(GROQ_URL, headers=headers, json=data)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']

        # Clean up SQL from any wrapping text
        sql_match = re.search(r"(SELECT|INSERT|UPDATE|DELETE).*?;", content, re.IGNORECASE | re.DOTALL)
        if sql_match:
            return sql_match.group(0).strip()
        else:
            return None
    except Exception as e:
        print(f"❌ SQL Generation Error: {e}")
        return None


# -------------------- 3. Execute SQL Query --------------------
def execute_sql_query(conn, sql_query):
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql_query)
        return cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"❌ SQL Exec Error: {err}")
        return []
    finally:
        cursor.close()


# -------------------- 4. Human-Friendly Summary --------------------
from datetime import datetime, date

def clean_data_for_json(data):
    def convert(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return obj
    return [{k: convert(v) for k, v in row.items()} for row in data]

def explain_results_with_llama(prompt, rows, model, api_key):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    cleaned_rows = clean_data_for_json(rows)

    messages = [
        {"role": "system", "content": "You are an AI assistant who explains SQL query results in human-friendly language."},
        {"role": "user", "content": f"Prompt: {prompt}\n\nResults:\n{json.dumps(cleaned_rows, indent=2)}"}
    ]
    data = {
        "model": model,
        "messages": messages,
        "temperature": 0.4
    }

    try:
        response = requests.post(GROQ_URL, headers=headers, json=data)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"❌ Explanation Error: {e}")
        return "Error generating human-readable output."

# -------------------- 5. Web Interface --------------------
@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    sql_query = None
    explanation = None

    if request.method == 'POST':
        prompt = request.form.get('prompt')
        conn = get_db_connection()

        if conn:
            sql_query = generate_sql_from_prompt(prompt, MODEL_NAME, GROQ_API_KEY)
            if sql_query:
                result = execute_sql_query(conn, sql_query)
                explanation = explain_results_with_llama(prompt, result, MODEL_NAME, GROQ_API_KEY)
            conn.close()

    return render_template("final.html", sql_query=sql_query, result=result, explanation=explanation)

# -------------------- 6. Config --------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # API key from .env
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama3-70b-8192"

if __name__ == "__main__":
    app.run(debug=True)