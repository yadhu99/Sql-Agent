from qdrant_client.models import Filter, FieldCondition, MatchValue
import re

from .dbconnection import db_connect
from .embeddings import embed_text
from .vectorstore import COLLECTION_NAME, client


def _load_session_table_metadata(session_id: str) -> list[dict]:
    schema_name = f"session_{session_id.replace('-', '_')}"
    print(f"[retriever] Loading table metadata for schema={schema_name}")
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
        table_names = [row[0] for row in cursor.fetchall()]

        metadata = []
        for table_name in table_names:
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
                """,
                (schema_name, table_name),
            )
            columns = [row[0] for row in cursor.fetchall()]
            metadata.append({"table_name": table_name, "columns": columns})

        print(
            f"[retriever] Loaded metadata for {len(metadata)} tables in session_id={session_id}"
        )
        return metadata
    finally:
        conn.close()


def _lexical_table_fallback(question: str, table_metadata: list[dict], top_k: int) -> list[str]:
    tokens = {
        token
        for token in re.split(r"[^a-z0-9_]+", question.lower())
        if token and len(token) > 1
    }
    if not tokens:
        print("[retriever] No lexical tokens found in question; using first tables as fallback")
        return [table["table_name"] for table in table_metadata[:top_k]]

    scored_tables = []
    for table in table_metadata:
        searchable_parts = [table["table_name"], *table["columns"]]
        searchable_tokens = {
            part.lower().replace("_", " ")
            for part in searchable_parts
        }

        score = 0
        for token in tokens:
            for searchable in searchable_tokens:
                if token in searchable:
                    score += 1

        if score > 0:
            scored_tables.append((score, table["table_name"]))

    if scored_tables:
        scored_tables.sort(key=lambda item: (-item[0], item[1]))
        print(f"[retriever] Lexical scoring matched {len(scored_tables)} tables")
        return [table_name for _, table_name in scored_tables[:top_k]]

    print("[retriever] Lexical scoring found no matches; using first tables as fallback")
    return [table["table_name"] for table in table_metadata[:top_k]]


def get_relevant_tables(session_id: str, question: str, top_k: int = 8):
    print(
        f"[retriever] Starting relevant table lookup for session_id={session_id} top_k={top_k}"
    )
    table_metadata = _load_session_table_metadata(session_id)
    if not table_metadata:
        print(f"[retriever] No table metadata found for session_id={session_id}")
        return []

    vector = embed_text(question)
    print(f"[retriever] Built question embedding with length={len(vector)}")

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        limit=top_k,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="session_id",
                    match=MatchValue(value=session_id)
                )
            ]
        )
    )

    points = results[0] if isinstance(results, tuple) else results.points
    print(f"[retriever] Qdrant returned {len(points)} points")
    semantic_tables = []
    for point in points:
        table_name = point.payload.get("table_name")
        if table_name and table_name not in semantic_tables:
            semantic_tables.append(table_name)

    print("Session ID:", session_id)
    print("Question:", question)
    print("Embedding vector length:", len(vector))
    print("Raw Qdrant result:", results)

    lexical_tables = _lexical_table_fallback(question, table_metadata, top_k)
    merged_tables = []

    for table_name in semantic_tables + lexical_tables:
        if table_name not in merged_tables:
            merged_tables.append(table_name)
        if len(merged_tables) >= top_k:
            break

    print("Semantic tables:", semantic_tables)
    print("Lexical fallback tables:", lexical_tables)
    print("Relevant tables selected:", merged_tables)

    return merged_tables
