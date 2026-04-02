def build_system_prompt(schema: str) -> str:
    """
    The system prompt tells the LLM who it is,
    what database it's working with, and the rules it must follow.
    This gets sent with every single request.
    """
    return f"""You are an expert SQL agent. Your job is to convert natural language questions into accurate SQLite SQL queries and return the results.

    DATABASE SCHEMA:
    {schema}

    RULES YOU MUST FLLOW:
    1. Only generate SELECT queries - never INSERT , UPDATE , DELETE, or DROP
    2. Always use exact table and column names from the schema above
    3. When joining tables, use the relationships defined in the schema
    4. If a question is ambiguous, do not make assumptions, ask question back to the user
    5. Return ONLY the SQL query, no explanation, no markdown, no backticks
    6. If the question cannot be answered from the schema, reply exactly: CANNOT_ANSWER

    DIALECT: SQLite"""

def build_messages(system_prompt: str, chat_history: list, user_question: str) -> list:
    """
    Builds the full message array for the LLM API call.

    Why we include history:
    - Allows follow-up questions ("now filter by USA only")
    - LLM understands context from previous turns
    - We only keep last 10 messages to avoid hitting token limits
    """
    messages = [
        {"role": "system", "content": system_prompt}
    ]

    # include last 10 messages for context
    recent_history = chat_history[-10:]
    for msg in recent_history:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    # add current question
    messages.append({
        "role": "user",
        "content": user_question
    })

    return messages