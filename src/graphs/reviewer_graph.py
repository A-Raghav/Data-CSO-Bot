from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition

from src.models.graph_states import ParentState
from src.graphs.agents.reviewer_agent import reviewer_agent
from src.graphs.tools.reviewer_tools import hybrid_retrieval_tool, data_analyst_tool, provenance_tool


TOOLS = [hybrid_retrieval_tool, data_analyst_tool, provenance_tool]

def create_reviewer_graph(store=None, checkpointer=None):
    tool_node = ToolNode(TOOLS)

    graph_builder = StateGraph(ParentState)

    graph_builder.add_node("reviewer_agent", reviewer_agent)
    graph_builder.add_node("tools", tool_node)
    graph_builder.add_edge(START, "reviewer_agent")
    graph_builder.add_conditional_edges("reviewer_agent", tools_condition)
    graph_builder.add_edge("tools", "reviewer_agent")

    app = graph_builder.compile(
        store=store,
        checkpointer=checkpointer,
    )
    return app

