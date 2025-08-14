import mysql.connector

config = {
    "host": "localhost",
    "port": 3306,
    "user": "mcp_user",
    "password": "1234",
    "database": "mcp_db",
    "auth_plugin": "mysql_native_password"
}

try:
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES;")
    for table in cursor.fetchall():
        print(table)
    conn.close()
    print("✅ Connection successful!")
except Exception as e:
    print("❌ Connection failed:", e)
