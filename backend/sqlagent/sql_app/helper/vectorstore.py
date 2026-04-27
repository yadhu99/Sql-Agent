import os
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PayloadSchemaType, PointStruct, VectorParams

from .embeddings import embed_text


QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

if not QDRANT_URL or not QDRANT_API_KEY:
    raise ValueError("Qdrant credentials missing. Check environment variables.")

client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
)

COLLECTION_NAME = "table_schema_embeddings"

def _build_embedding_text(table_name: str, columns: list[str]) -> str:
    normalized_table_name = table_name.replace("_", " ")
    normalized_columns = [column.replace("_", " ") for column in columns]

    return (
        f"Table name: {table_name}. "
        f"Table description: {normalized_table_name}. "
        f"Columns: {', '.join(columns)}. "
        f"Normalized columns: {', '.join(normalized_columns)}."
    )


def _build_point_id(session_id: str, table_name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{session_id}:{table_name}"))


def store_table_embeddings(session_id: str, table_summaries: list[dict]) -> None:
    if not table_summaries:
        print(f"[qdrant] No table summaries to index for session_id={session_id}")
        return

    print(
        f"[qdrant] Preparing to index {len(table_summaries)} tables for session_id={session_id}"
    )
    points = []
    for table_summary in table_summaries:
        table_name = table_summary["table_name"]
        columns = table_summary["columns"]
        searchable_text = _build_embedding_text(table_name, columns)
        vector = embed_text(searchable_text)
        print(
            f"[qdrant] Built embedding for table={table_name} columns={len(columns)} "
            f"vector_length={len(vector)}"
        )

        points.append(
            PointStruct(
                id=_build_point_id(session_id, table_name),
                vector=vector,
                payload={
                    "table_name": table_name,
                    "session_id": session_id,
                    "columns": columns,
                    "searchable_text": searchable_text,
                },
            )
        )

    client.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"[qdrant] Indexed {len(points)} table embeddings for session_id={session_id}")


def store_table_embedding(session_id: str, table_name: str, columns: list[str]) -> None:
    store_table_embeddings(
        session_id,
        [{"table_name": table_name, "columns": columns}],
    )

def create_collection_if_not_exists():
    print(f"[qdrant] Ensuring collection exists: {COLLECTION_NAME}")
    collections = client.get_collections().collections
    names = [c.name for c in collections]

    if COLLECTION_NAME not in names:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
        print(f"[qdrant] Created collection={COLLECTION_NAME}")

    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="session_id",
        field_schema=PayloadSchemaType.KEYWORD
    )
    print("[qdrant] Ensured payload index on session_id")

    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="table_name",
        field_schema=PayloadSchemaType.KEYWORD
    )
    print("[qdrant] Ensured payload index on table_name")
