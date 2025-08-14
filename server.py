import sqlite3
import argparse
import pandas as pd
from mcp.server.fastmcp import FastMCP

mcp = FastMCP('sqlite-demo')

def init_db():
    conn = sqlite3.connect('demo.db')
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

@mcp.tool()
def add_data(query: str) -> bool:
    if not isinstance(query, str):
        print("❌ Invalid query format. Expected a string SQL statement.")
        return False

    conn, cursor = init_db()
    try:
        cursor.execute(query)
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error adding data: {e}")
        return False
    finally:
        conn.close()

@mcp.tool()
def read_data(query: str = "SELECT * FROM people") -> list:
    if not isinstance(query, str):
        print("Query must be a string.")
        return []
    conn, cursor = init_db()
    try:
        cursor.execute(query)
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Error reading data: {e}")
        return []
    finally:
        conn.close()


@mcp.tool()
def count_shows_by_year(year: str) -> int:
    conn = sqlite3.connect('demo.db')
    cursor = conn.cursor()
    try:
        query = f"SELECT COUNT(*) FROM shows WHERE year = '{year}'"
        cursor.execute(query)
        result = cursor.fetchone()
        return result[0] if result else 0
    except sqlite3.Error as e:
        print(f"Error querying data: {e}")
        return 0
    finally:
        conn.close()


def load_csv_to_db(csv_path: str, plot: bool = False):
    try:
        df = pd.read_csv(csv_path, encoding='ISO-8859-1')  # Handles special characters
        required_cols = {'name', 'age', 'profession'}
        if not required_cols.issubset(df.columns):
            print("CSV must have columns: name, age, profession")
            return False

        conn, _ = init_db()
        df.to_sql('people', conn, if_exists='append', index=False)
        conn.close()
        print("✅ CSV data inserted successfully.")

        if plot:
            plot_df(df)  # Plot directly from the uploaded DataFrame

        return True
    except Exception as e:
        print(f"❌ Failed to load CSV: {e}")
        return False

def user_prompt():
    print("📋 Choose one of the following:")
    print("1: Enter a manual SQL query")
    print("2: Provide a CSV file path to insert data")
    choice = input("Your choice (1 or 2): ").strip()

    if choice == "1":
        print("✍️ Enter your SQL query (end with semicolon):")
        query = input(">> ").strip()
        if query.lower().startswith("insert"):
            if add_data(query):
                print("✅ Data inserted successfully.")
            else:
                print("❌ Insertion failed.")
        else:
            result = read_data(query)
            print("📊 Query Result:")
            for row in result:
                print(row)

    elif choice == "2":
        csv_path = input("📂 Enter path to CSV file: ").strip()
        plot_choice = input("📊 Do you want to plot this CSV data? (y/n): ").strip().lower()
        plot_flag = plot_choice == 'y'
        load_csv_to_db(csv_path, plot=plot_flag)
    else:
        print("❗Invalid choice. Skipping manual input.")

if __name__ == "__main__":
    # Prompt user first
    user_prompt()

    print("🚀Starting FastMCP server...")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--server_type", type=str, default="sse", choices=["sse", "stdio"]
    )
    args = parser.parse_args()
    mcp.run(args.server_type)
