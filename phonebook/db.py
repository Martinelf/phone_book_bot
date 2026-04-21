import psycopg2
from psycopg2 import sql

# Database connection setup
def get_connection():
    return psycopg2.connect(
        dbname="phone_bot",
        user="postgres",
        password="root",
        host="localhost",
        port="5432"
    )

# Query execution
def execute_query(query, params=None):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if query.strip().lower().startswith("select"):
                return cur.fetchall()
            conn.commit()
    finally:
        conn.close()