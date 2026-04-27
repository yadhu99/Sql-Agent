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
    print(f"[sql] execute_query called for session_id={session_id}")
    print(f"[sql] SQL to execute: {sql}")
    if not is_safe_query(sql):
        print("[sql] Query rejected by safety check")
        return {
            "success": False,
            "error": "Query rejected — only SELECT queries are allowed"
        }

    try:
        conn, cursor = db_connect(session_id)
        print("[sql] Database connection established")
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        print(
            f"[sql] Query succeeded with column_count={len(columns)} row_count={len(rows)}"
        )

        return {
            "success": True,
            "columns": columns,
            "rows": [list(row) for row in rows],
            "row_count": len(rows)
        }

    except psycopg2.Error as e:
        print(f"[sql] Query failed with database error: {e}")
        return {
            "success": False,
            "error": str(e)
        }
