from textwrap import dedent
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from src.graphs.llms.gemini import get_llm
from src.models.graph_states import AnalystSubgraphState
from src.graphs.tools.analyst_tools import python_code_executor


SYSTEM_PROMPT_ANALYST = dedent(
    f"""\
        # ROLE: I am a Data Analyst Agent that has access to Python-shell tool/function - `python_code_executor(code: str, description: str)`.

        # INSTRUCTIONS:
            - I call the `python_code_executor` tool to analyse the data.
            - Once I feel I know enough, I give a crisp and concise answer to the user's question.

        # NOTE:
            - The python-script should import necessary libraries (pandas, numpy, os, pathlib, etc) to read the CSV file and perform data manipulation 
            - The python-script use `print` statements for printing any statistics that you need to fetch.
            - In a single tool-call to `python_code_executor`, I ask for a single statistic to be fetched.
            - I keep the commentary limited in this step.
            - Once I have enough statistics to answer the user's question, I give a crisp and concise answer to user's question, with proper data backing it up.
        
        # WARNINGS:
            - For tool-calls to `python_code_executor` tool, only send the python code as `code` parameter
            - Do not include any visualizations or plots in the code.
            - In case I get reported back with any errors in executing the python code, I should make necessary corrections and call the python_code_executor tool to re-run the code.
            - The "Analysis-Plan" provided to me is a rough plan, I should adapt it as per the data available in the table.
        
        # TIPS:
            - For high cardinality columns, consider using simple keyword based filtering (like `str.contains('abc|xyz')`). Also consider items / categories related to said keywords.
    """
)

TOOLS = [python_code_executor]

llm = get_llm(model="gemini-2.5-flash")
llm_with_code_exec_tool = llm.bind_tools(
    tools=TOOLS,
    allowed_function_names=["python_code_executor"]
)

async def analyst_node(state: AnalystSubgraphState) -> str:
    """
    The analyst agent has access to the Python-Shell tool and uses it answer the user query by analysing the data available in context.

    Args:
        state (State): The state containing the messages and other data.
    
    Returns:
        str: The response from the analyst agent.
    """
    try:
        question = state["question"]
        analysis_plan = state["analysis_plan"]
        context = state["context"]
        old_messages = state["messages"]
        report = state.get("report", [])

        system_prompt = SYSTEM_PROMPT_ANALYST
        iters = state.get("iters", 0)
        iters += 1

        context = f"CONTEXT:\n{context}\n\nANALYSIS PLAN:\n{analysis_plan}"
        msgs = [
            SystemMessage(content=system_prompt, name="analyst_node"),
            SystemMessage(content=context, name="analyst_node"),
            HumanMessage(content=question, name="analyst_node"),
        ] + old_messages
        
        if iters <= 10:
            # print("Running data-analyst agent...")
            res = await llm_with_code_exec_tool.ainvoke(msgs)
        else:
            # print("Stopping tool-calls as max-iterations reached. Generating final response...")
            res = await llm.ainvoke(msgs)
            return {"messages": [res], "iters": iters, "context": context, "report": report}

        if isinstance(res, AIMessage):
            return {"messages": [res], "iters": iters, "context": context, "report": report}
        else:
            res = AIMessage("Error generating code. Please try again.")
            return {"messages": [res], "iters": iters, "context": context, "report": report}
    except Exception as e:
        res = AIMessage(f"Error occurred during analysis: {str(e)}")
        return {"messages": [res], "iters": iters, "context": context, "report": report}
