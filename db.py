import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

# Database Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'online_banking')
}

def get_db_connection():
    """
    Returns a connected MySQL connection object and a cursor.
    The caller is responsible for committing transactions and closing the connection.
    """
    conn = mysql.connector.connect(**DB_CONFIG)
    # Using dictionary=True so rows are returned as dicts rather than tuples
    cursor = conn.cursor(dictionary=True)
    return conn, cursor

def call_procedure(cursor, proc_call, params=None):
    """
    Execute a stored procedure CALL statement and return the first result row.
    Automatically consumes extra result sets produced by the MySQL CALL protocol.
    """
    cursor.execute(proc_call, params)
    result = cursor.fetchone()
    try:
        while cursor.nextset():
            pass
    except Exception:
        pass
    return result
