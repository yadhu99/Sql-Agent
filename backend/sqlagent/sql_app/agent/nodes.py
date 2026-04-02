import os
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from ..helper.sqlexecutor import execute_query

MAX_RETRIES = 3


def get_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY")
    )


def planner_node(state: dict) -> dict:
    """
    Why: before writing SQL, the agent reads the question
    and schema and makes a plan. This improves SQL quality
    for complex multi-table questions.
    """

    llm= get_llm()
    messages = [
            SystemMessage(content=f"""You are a SQL planning expert.
    Given a database schema and a user question, create a brief plan 
    for how to answer it using SQL. Mention which tables and joins are needed.
    Keep the plan to 2-3 sentences maximum.

    SCHEMA:
    {state['schema']}"""),
            HumanMessage(content=state['question'])
        ]
    
    response = llm.invoke(messages)

    return {
        **state,
        "plan": response.content,
        "status": "generating"
    }


def sql_generator_node(state: dict) -> dict:
    """
    Why: uses the plan + schema to generate accurate SQL.
    Having a plan first means the LLM already knows which
    tables and joins are needed before writing the query.
    """

    llm = get_llm()
    messages = [
            SystemMessage(content=f"""You are an expert SQL agent for SQLite.
    Your job is to write a single SQL SELECT query to answer the user's question.

    SCHEMA:
    {state['schema']}

    PLAN:
    {state['plan']}

    STRICT RULES:
    1. Return ONLY the raw SQL query — no explanation, no markdown, no backticks
    2. Only SELECT queries — never INSERT, UPDATE, DELETE, DROP
    3. Use exact table and column names from the schema
    4. Use proper SQLite syntax
    5. If you cannot answer, reply exactly: CANNOT_ANSWER"""),
            HumanMessage(content=state['question'])
        ]
    response = llm.invoke(messages)
    sql = response.content.strip()

    return {
        **state,
        "sql": sql,
        "status": "executing"
    }

def executor_node(state: dict) -> dict:
    sql = state.get('sql', '').strip()

    if not sql or sql == 'CANNOT_ANSWER':
        return {
            **state,
            "status": "failed",
            "error": "This question cannot be answered from the available data."
        }

    result = execute_query(
        session_id=state['session_id'],
        sql=sql
    )

    if result['success']:
        return {
            **state,
            "columns": result['columns'],
            "rows": result['rows'],
            "row_count": result['row_count'],
            "error": None,
            "status": "success"
        }
    else:
        return {
            **state,
            "error": result['error'],
            "status": "retrying"
        }
    
def self_corrector_node(state: dict) -> dict:
    """
    Why: instead of just returning an error to the user,
    the agent sends the broken SQL + error message back
    to the LLM and asks it to fix the query.
    This is the core agentic behaviour — the agent
    recovers from mistakes automatically.
    """
    llm = get_llm()

    messages = [
        SystemMessage(content=f"""You are an expert SQL debugger for SQLite.
        A SQL query failed. Fix it and return ONLY the corrected SQL query.
        No explanation, no markdown, no backticks.

        SCHEMA:
        {state['schema']}"""),
                HumanMessage(content=f"""Original question: {state['question']}

        Failed SQL:
        {state['sql']}

        Error:
        {state['error']}

        Return the fixed SQL query only.""")
            ]

    response = llm.invoke(messages)
    fixed_sql = response.content.strip()

    return {
        **state,
        "sql": fixed_sql,
        "retry_count": state['retry_count'] + 1,
        "status": "executing"
    }

def should_retry(state: dict) -> str:
    """
    Why: this is the conditional edge — the decision point
    in the graph. It decides whether to retry, give up, or
    return the result.

    Returns the name of the next node to go to.
    """
    if state['status'] == 'success':
        return "success"
    elif state['status'] == 'failed':
        return "failed"
    elif state['retry_count'] >= MAX_RETRIES:
        return "failed"
    else:
        return "retry"
    


