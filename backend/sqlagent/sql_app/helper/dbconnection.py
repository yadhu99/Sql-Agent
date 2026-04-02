import psycopg2
import os


def get_pg_connection():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    return conn


def db_connect(session_id: str = None):
    conn = get_pg_connection()
    cursor = conn.cursor()

    if session_id:
        schema_name = f"session_{session_id.replace('-', '_')}"
        cursor.execute(f'SET search_path TO "{schema_name}", public')

    return conn, cursor


def create_session_schema(session_id: str):
    schema_name = f"session_{session_id.replace('-', '_')}"
    conn = get_pg_connection()
    cursor = conn.cursor()
    cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')
    conn.commit()
    conn.close()
    return schema_name


def drop_session_schema(session_id: str):
    schema_name = f"session_{session_id.replace('-', '_')}"
    conn = get_pg_connection()
    cursor = conn.cursor()
    cursor.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
    conn.commit()
    conn.close()