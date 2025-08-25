from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, START

from src.graphs.tools.analyst_tools import python_code_executor
from src.models.graph_states import AnalystSubgraphState
from src.graphs.agents.analyst_agent import analyst_node


def _create_analyst_graph():
    TOOLS = [python_code_executor]
    tool_node = ToolNode(TOOLS)

    analyst_graph_builder = StateGraph(AnalystSubgraphState)

    analyst_graph_builder.add_node("analyst_node", analyst_node)
    analyst_graph_builder.add_node("tools", tool_node)
    analyst_graph_builder.add_edge(START, "analyst_node")
    analyst_graph_builder.add_conditional_edges("analyst_node", tools_condition)
    analyst_graph_builder.add_edge("tools", "analyst_node")

    analyst_graph = analyst_graph_builder.compile()
    return analyst_graph


analyst_graph = _create_analyst_graph()