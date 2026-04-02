from langgraph.graph import StateGraph, END
from .state import AgentState
from .nodes import (
    planner_node,
    sql_generator_node,
    executor_node,
    self_corrector_node,
    should_retry
)


def build_agent() -> StateGraph:
    """
    Builds and compiles the LangGraph agent.

    Flow:
    planner → sql_generator → executor → should_retry?
                                              ↓
                              success → END
                              retry   → self_corrector → executor
                              failed  → END
    """
    graph = StateGraph(AgentState)

    # add nodes
    graph.add_node("planner", planner_node)
    graph.add_node("sql_generator", sql_generator_node)
    graph.add_node("executor", executor_node)
    graph.add_node("self_corrector", self_corrector_node)

    # define flow
    graph.set_entry_point("planner")
    graph.add_edge("planner", "sql_generator")
    graph.add_edge("sql_generator", "executor")

    # conditional edge — decision point after executor
    graph.add_conditional_edges(
        "executor",
        should_retry,
        {
            "success": END,
            "failed": END,
            "retry": "self_corrector"
        }
    )

    # after self correction go back to executor
    graph.add_edge("self_corrector", "executor")

    return graph.compile()

agent = build_agent()