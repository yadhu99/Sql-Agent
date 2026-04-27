import os
import json
from groq import Groq

from .helper.dbconnection import db_connect
from .models import CSVSession, ChatMessage
from .agent.graph import agent
from .helper.retriever import get_relevant_tables


def infer_relationships_with_llm(
    session_id: str,
    selected_tables: list[str] | None = None,
) -> list:
    schema_name = f"session_{session_id.replace('-', '_')}"
    print(
        f"[schema] infer_relationships_with_llm start session_id={session_id} "
        f"selected_tables={selected_tables}"
    )
    conn, cursor = db_connect(session_id)

    cursor.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = %s
    """, (schema_name,))
    tables = [row[0] for row in cursor.fetchall()]
    if selected_tables is not None:
        selected_table_set = set(selected_tables)
        tables = [table for table in tables if table in selected_table_set]
    print(f"[schema] LLM relationship inference will inspect {len(tables)} tables")

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
        parsed = json.loads(raw.strip())
        print(f"[schema] LLM inferred {len(parsed)} relationships")
        return parsed
    except json.JSONDecodeError:
        print("[schema] Failed to parse LLM relationship output as JSON")
        return []


def infer_relationships(
    session_id: str,
    selected_tables: list[str] | None = None,
    include_llm: bool = True,
) -> list:
    schema_name = f"session_{session_id.replace('-', '_')}"
    print(
        f"[schema] infer_relationships start session_id={session_id} "
        f"selected_tables={selected_tables} include_llm={include_llm}"
    )
    conn, cursor = db_connect(session_id)

    cursor.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = %s
    """, (schema_name,))
    tables = [row[0] for row in cursor.fetchall()]
    if selected_tables is not None:
        selected_table_set = set(selected_tables)
        tables = [table for table in tables if table in selected_table_set]
    print(f"[schema] Checking relationships across {len(tables)} tables")

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

    if include_llm and tables and len(tables) <= 25:
        try:
            llm_relationships = infer_relationships_with_llm(
                session_id,
                selected_tables=tables,
            )
            for rel in llm_relationships:
                if rel["from_table"] not in table_columns or rel["to_table"] not in table_columns:
                    continue

                pair = (rel['from_table'], rel['from_column'])
                if pair not in matched_pairs:
                    rel['method'] = 'llm'
                    relationships.append(rel)
        except Exception as e:
            print(f"LLM inference failed: {e}")

    print(f"[schema] Total relationships inferred: {len(relationships)}")
    return relationships


def get_session_tables(session_id: str) -> list[str]:
    schema_name = f"session_{session_id.replace('-', '_')}"
    print(f"[schema] Loading session tables for schema={schema_name}")
    conn, cursor = db_connect(session_id)

    try:
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
            ORDER BY table_name
            """,
            (schema_name,),
        )
        tables = [row[0] for row in cursor.fetchall()]
        print(f"[schema] Found {len(tables)} tables for session_id={session_id}")
        return tables
    finally:
        conn.close()


def extract_full_schema(session_id: str) -> str:
    schema_name = f"session_{session_id.replace('-', '_')}"
    print(f"[schema] Building full schema for session_id={session_id}")
    conn, cursor = db_connect(session_id)

    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
        ORDER BY table_name
    """, (schema_name,))
    tables = [row[0] for row in cursor.fetchall()]
    print(f"[schema] Full schema includes {len(tables)} tables")

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

    relationships = infer_relationships(
        session_id,
        selected_tables=tables,
        include_llm=len(tables) <= 25,
    )
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

def extract_filtered_schema(session_id: str, tables: list[str]) -> str:
    schema_name = f"session_{session_id.replace('-', '_')}"
    print(
        f"[schema] Building filtered schema for session_id={session_id} "
        f"with tables={tables}"
    )
    conn, cursor = db_connect(session_id)

    schema_lines = ["Tables:"]

    for table in tables:
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
        """, (schema_name, table))

        columns = cursor.fetchall()

        schema_lines.append(f"\n  {table}:")
        for col in columns:
            schema_lines.append(f"    - {col[0]} ({col[1]})")

    conn.close()

    relationships = infer_relationships(
        session_id,
        selected_tables=tables,
        include_llm=False,
    )

    if relationships:
        schema_lines.append("\nRelationships:")
        for rel in relationships:
            method = rel.get("method", "")
            schema_lines.append(
                f"  - {rel['from_table']}.{rel['from_column']} -> "
                f"{rel['to_table']}.{rel['to_column']} ({method})"
            )

    return "\n".join(schema_lines)

def process_chat_message(session_id: str, user_question: str) -> dict:
    print(
        f"[chat-service] process_chat_message start session_id={session_id} "
        f"question={user_question}"
    )
    try:
        session = CSVSession.objects.get(session_id=session_id)
    except CSVSession.DoesNotExist:
        print(f"[chat-service] Session not found for session_id={session_id}")
        return {"error": "Session not found. Please upload CSV files first."}

    all_tables = get_session_tables(session_id)
    if not all_tables:
        print(f"[chat-service] No tables found for session_id={session_id}")
        return {"error": "No tables found for this session. Please upload CSV files first."}

    top_k = min(12, max(5, len(all_tables) // 10 + 4))
    print(
        f"[chat-service] all_tables={len(all_tables)} computed_top_k={top_k}"
    )
    relevant_tables = get_relevant_tables(session_id, user_question, top_k=top_k)
    if not relevant_tables:
        relevant_tables = all_tables[:top_k]
        print(
            f"[chat-service] Retrieval empty, falling back to first tables={relevant_tables}"
        )

    schema = extract_filtered_schema(session_id, relevant_tables)
    print("=== SCHEMA BEING SENT TO LLM ===")
    print(schema)
    print("================================")


    history_qs = ChatMessage.objects.filter(session=session).order_by('created_at')
    chat_history = [
        {"role": msg.role, "content": msg.Content}
        for msg in history_qs
    ]
    print(f"[chat-service] Loaded chat_history_count={len(chat_history)}")

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
    print(
        f"[chat-service] Agent finished with status={final_state.get('status')} "
        f"retry_count={final_state.get('retry_count')}"
    )
    print(f"[chat-service] Final SQL={final_state.get('sql')}")

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

    print("Relevant tables:", relevant_tables)

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
    
