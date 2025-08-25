from typing import  Annotated, List, Dict
from langgraph.types import Command
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from langchain_core.tools import tool, InjectedToolCallId

from src.utils.python_runner import run_python_safely


@tool(name_or_callable="python_code_executor", parse_docstring=True)
def python_code_executor(
    code: str,
    description: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> str:
    """
    Executes the given Python code and returns the output.
    
    Args:
        code (str): The Python code to execute.
        description (str): A short description of the code being executed.
    
    Returns:
        str: The output of the executed code.
    """
    # print("Executing code in python_code_executor: ", description, "\n")
    result = run_python_safely(code)

    existing_reports : List[Dict] = state.get("report", [])
    

    if 'error' in result:
        current_report = {
            "task": description,
            "code": code,
            "result": result.get("error", ""),
        }
        existing_reports.append(current_report)
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=f"Error executing code: {result['error']}",
                        tool_call_id=tool_call_id,
                        name="python_code_executor"
                    )
                ],
                "report": existing_reports,
            }
        )
    else:
        # print("Result from python_code_executor: ", str(result['stdout'])[:100])
        current_report = {
            "task": description,
            "code": code,
            "result": result.get("stdout", ""),
        }
        existing_reports.append(current_report)
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=result['stdout'],
                        tool_call_id=tool_call_id,
                        name="python_code_executor"
                    )
                ],
                "report": existing_reports
            }
        )