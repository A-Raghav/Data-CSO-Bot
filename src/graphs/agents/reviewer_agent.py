from textwrap import dedent
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from src.utils.text_coercion import coerce_ai_to_text
from src.utils.check_tool_calls import has_tool_calls
from src.graphs.llms.gemini import get_llm
from src.models.graph_states import ParentState
from src.graphs.tools.reviewer_tools import hybrid_retrieval_tool, data_analyst_tool, provenance_tool


TOOLS = [hybrid_retrieval_tool, data_analyst_tool, provenance_tool]
llm = get_llm(model="gemini-2.5-flash-lite")
llm_with_tools_poc = llm.bind_tools(TOOLS)

reviewer_system_prompt = dedent(
    """\
        # GOAL: I'm a helpful assistant. My job is to answer the user-question using all the facts available.

        # INSTRUCTIONS:
        - I have the following tools available for my tasks:
            1. hybrid_retrieval_tool: To retrieve relevant table IDs from CSO-DATA based on user queries.
            2. data_analyst_tool: To run the analysis on the retrieved tables.
            3. provenance_tool: To fetch the provenance information (analysis report containing low-level code used for generating analysis) for a specific table.
        - Once I have the relevant data from tables, I will invoke the `data_analyst_tool` with the list of all all relevant table_ids.
        - Once I have the results from the analysis, I will answer the user's question in detail, using only the insights gained from the analysis.
        - I will cite the sources of my information (table-IDs) against each fact.
        - For follow up questions:
            1. If the user explicitly asks a follow-up question for the code / filters / methodology used in generating the insights, I will retrieve the provenance information by calling the `provenance_tool`, and only then answer the user follow-up question
            2. If the user asks for additional analysis or a different perspective on the data, I will re-run the analysis with the new parameters and provide the updated results.

        # RETURN FORMAT:
        - The final answer containing text / tables should be in Markdown format
    """
)


def reviewer_agent(state: ParentState):
    response = {}
    iter = state.get("iter", 0) + 1
    messages = state["messages"]

    if isinstance(messages[-1], HumanMessage):
        if state.get("question", None) is not None and messages[-1].content != state["question"]:
            iter = 0 # reset iteration for new questions

        response["question"] = messages[-1].content
    
    res = llm_with_tools_poc.invoke(
        [SystemMessage(content=reviewer_system_prompt, name="reviewer_agent")] + messages,
        config={"response_mime_type": "text/plain"},

    )

    if iter > 12:
        response["messages"] = [AIMessage("Max iterations reached, ending...")]
    else:
        res = coerce_ai_to_text(res) if isinstance(res, AIMessage) and not has_tool_calls(res) else res
        response["messages"] = [res]
    
    response["iter"] = iter

    return response