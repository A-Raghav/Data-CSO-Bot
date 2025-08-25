from langchain_core.messages import AIMessage


def has_tool_calls(msg: AIMessage) -> bool:
    """
    Check if the AIMessage has tool calls.
    
    Args:
        msg (AIMessage): The AI message to check.
    
    Returns:
        bool: True if the message has tool calls, False otherwise.
    """
    return getattr(msg, "tool_calls", []) != [] or \
           bool(getattr(msg, "additional_kwargs", {}).get("function_call") or \
                getattr(msg, "additional_kwargs", {}).get("tool_calls"))
