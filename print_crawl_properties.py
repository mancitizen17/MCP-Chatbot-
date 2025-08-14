import mysql.connector

def get_db_connection(config):
    """Establishes and returns a database connection."""
    try:
        conn = mysql.connector.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            port=config['port'],
            auth_plugin=config['auth_plugin'] 
        )
        if conn.is_connected():
            print("Successfully connected to MySQL database!")
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None

def print_row_by_id(connection, table_name, row_id):
    """
    Fetches and prints a row from the specified table where the 'id' column matches row_id.
    Assumes the primary key/ID column is named 'id'.
    """
    if not connection:
        print("No database connection available.")
        return

    cursor = connection.cursor(dictionary=True) 

    try:
        query = f"SELECT * FROM {table_name} WHERE id = %s"
        cursor.execute(query, (row_id,))
        row = cursor.fetchone()

        if row:
            print(f"\nRow with ID {row_id} from table '{table_name}':")
            for key, value in row.items():
                print(f"  {key}: {value}")
        else:
            print(f"\nNo row found with ID {row_id} in table '{table_name}'.")

    except mysql.connector.Error as err:
        print(f"Error executing query: {err}")
    finally:
        cursor.close()

# my database configuration
db_config = {
    'host': '18.158.132.26',
    'user': 'mcp_chatbot',
    'password': 'StrongCHatMcpPassword123!',
    'database': 'flatbeeGermany',
    'port': 3306,
    'auth_plugin': 'mysql_native_password'
}

if __name__ == "__main__":
    conn = None
    try:
        conn = get_db_connection(db_config)
        if conn:
            while True:
                prompt = input("\nEnter a command (e.g., 'print the row with id 1900' or 'exit'): ").strip().lower()

                if prompt.startswith("print the row with id "):
                    try:
                        # Extract the ID from the prompt
                        parts = prompt.split("id ")
                        if len(parts) > 1:
                            row_id_str = parts[1].strip()
                            # Remove any non-digit characters if they exist (e.g., from a period)
                            row_id_str = ''.join(filter(str.isdigit, row_id_str))
                            row_id = int(row_id_str)
                            print_row_by_id(conn, "crawl_properties", row_id)
                        else:
                            print("Invalid prompt format. Please use 'print the row with id [number]'.")
                    except ValueError:
                        print("Invalid ID. Please enter a valid number.")
                elif prompt == "exit":
                    print("Exiting.")
                    break
                else:
                    print("Unknown command. Please try again.")
    finally:
        if conn and conn.is_connected():
            conn.close()
            print("\nMySQL connection closed.")