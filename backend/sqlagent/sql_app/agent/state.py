from typing import TypedDict, Optional


class AgentState(TypedDict):
    question: str
    schema: str
    session_id: str
    plan: str
    sql: str
    columns: list
    rows: list
    row_count: int
    error: Optional[str]
    retry_count: int
    status: str