import os
import json
import psycopg2
from groq import Groq
from .helper.dbconnection import db_connect, create_session_schema
from .helper.csvloader import csv_to_postgres
from .models import CSVSession, ChatMessage
from .agent.graph import agent


def infer_relationships_with_llm(session_id: str) -> list:
    schema_name = f"session_{session_id.replace('-', '_')}"
    conn, cursor = db_connect(session_id)

    cursor.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = %s
    """, (schema_name,))
    tables = [row[0] for row in cursor.fetchall()]

    context_lines = []
    for table in tables:
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
        """, (schema_name, table))
        columns = cursor.fetchall()

        cursor.execute(f'SELECT * FROM "{schema_name}"."{table}" LIMIT 5')
        rows = cursor.fetchall()

        context_lines.append(f"Table: {table}")
        context_lines.append("Columns: " + ", ".join([f"{c[0]} ({c[1]})" for c in columns]))
        context_lines.append("Sample data:")
        for row in rows:
            context_lines.append(f"  {row}")
        context_lines.append("")

    conn.close()

    context = "\n".join(context_lines)
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    prompt = f"""You are a database expert. Analyse these tables and their sample data,
            then identify relationships between them based on matching values or logical connections.

            {context}

            Return ONLY a JSON array like this, no explanation, no markdown:
            [
            {{"from_table": "orders", "from_column": "buyer", "to_table": "customers", "to_column": "name"}}
            ]

            If no relationships found, return an empty array: []"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    raw = response.choices[0].message.content.strip()
    try:
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        return []


def infer_relationships(session_id: str) -> list:
    schema_name = f"session_{session_id.replace('-', '_')}"
    conn, cursor = db_connect(session_id)

    cursor.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = %s
    """, (schema_name,))
    tables = [row[0] for row in cursor.fetchall()]

    table_columns = {}
    for table in tables:
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
        """, (schema_name, table))
        table_columns[table] = [row[0] for row in cursor.fetchall()]

    conn.close()

    relationships = []
    matched_pairs = set()

    for table, columns in table_columns.items():
        for col in columns:
            if col.endswith('_id'):
                referenced_name = col[:-3]
                candidates = [referenced_name, referenced_name + 's', referenced_name + 'es']
                for candidate in candidates:
                    if candidate in table_columns:
                        if 'id' in table_columns[candidate]:
                            rel = {
                                'from_table': table,
                                'from_column': col,
                                'to_table': candidate,
                                'to_column': 'id',
                                'method': 'column_name'
                            }
                            relationships.append(rel)
                            matched_pairs.add((table, col))
                            break

    try:
        llm_relationships = infer_relationships_with_llm(session_id)
        for rel in llm_relationships:
            pair = (rel['from_table'], rel['from_column'])
            if pair not in matched_pairs:
                rel['method'] = 'llm'
                relationships.append(rel)
    except Exception as e:
        print(f"LLM inference failed: {e}")

    return relationships


def extract_full_schema(session_id: str) -> str:
    schema_name = f"session_{session_id.replace('-', '_')}"
    conn, cursor = db_connect(session_id)

    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
        ORDER BY table_name
    """, (schema_name,))
    tables = [row[0] for row in cursor.fetchall()]

    schema_lines = ["Tables:"]

    for table in tables:
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """, (schema_name, table))
        columns = cursor.fetchall()

        schema_lines.append(f"\n  {table}:")
        for col in columns:
            schema_lines.append(f"    - {col[0]} ({col[1]})")

        cursor.execute(f'SELECT * FROM "{schema_name}"."{table}" LIMIT 3')
        rows = cursor.fetchall()
        schema_lines.append(f"  Sample rows:")
        for row in rows:
            schema_lines.append(f"    {row}")

    conn.close()

    relationships = infer_relationships(session_id)
    if relationships:
        schema_lines.append("\nRelationships:")
        for rel in relationships:
            method = rel.get('method', '')
            schema_lines.append(
                f"  - {rel['from_table']}.{rel['from_column']} → "
                f"{rel['to_table']}.{rel['to_column']}  ({method})"
            )
    else:
        schema_lines.append("\nRelationships: none detected")

    return "\n".join(schema_lines)

def process_chat_message(session_id: str, user_question: str) -> dict:
    try:
        session = CSVSession.objects.get(session_id=session_id)
    except CSVSession.DoesNotExist:
        return {"error": "Session not found. Please upload CSV files first."}

    schema = extract_full_schema(session_id)

    history_qs = ChatMessage.objects.filter(session=session).order_by('created_at')
    chat_history = [
        {"role": msg.role, "content": msg.Content}
        for msg in history_qs
    ]

    initial_state = {
        "question": user_question,
        "schema": schema,
        "session_id": session_id,
        "plan": "",
        "sql": "",
        "columns": [],
        "rows": [],
        "row_count": 0,
        "error": None,
        "retry_count": 0,
        "status": "planning"
    }

    final_state = agent.invoke(initial_state)

    ChatMessage.objects.create(
        session=session,
        role='user',
        Content=user_question
    )
    ChatMessage.objects.create(
        session=session,
        role='assistant',
        Content=final_state.get('sql', ''),
        sql_query=final_state.get('sql', '')
    )

    if final_state['status'] == 'success':
        return {
            "success": True,
            "question": user_question,
            "plan": final_state['plan'],
            "sql": final_state['sql'],
            "columns": final_state['columns'],
            "rows": final_state['rows'],
            "row_count": final_state['row_count'],
            "retries": final_state['retry_count']
        }
    else:
        return {
            "success": False,
            "question": user_question,
            "plan": final_state.get('plan', ''),
            "sql": final_state.get('sql', ''),
            "error": final_state.get('error', 'Query failed after maximum retries')
        }