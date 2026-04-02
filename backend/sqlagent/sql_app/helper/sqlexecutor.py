import psycopg2
from .dbconnection import db_connect


def is_safe_query(sql: str) -> bool:
    cleaned = sql.strip().upper()
    dangerous = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE', 'TRUNCATE']
    for keyword in dangerous:
        if cleaned.startswith(keyword):
            return False
    return True


def execute_query(session_id: str, sql: str) -> dict:
    if not is_safe_query(sql):
        return {
            "success": False,
            "error": "Query rejected — only SELECT queries are allowed"
        }

    try:
        conn, cursor = db_connect(session_id)
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()

        return {
            "success": True,
            "columns": columns,
            "rows": [list(row) for row in rows],
            "row_count": len(rows)
        }

    except psycopg2.Error as e:
        return {
            "success": False,
            "error": str(e)
        }