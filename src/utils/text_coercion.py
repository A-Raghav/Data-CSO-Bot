from langchain_core.messages import AIMessage


def _to_text(content) -> str:
    # Handles str, list[str], list[dict-like parts], or anything else.
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        pieces = []
        for part in content:
            if isinstance(part, str):
                pieces.append(part)
            elif isinstance(part, dict):
                # Gemini often uses {"type":"text","text": "..."} parts
                pieces.append(part.get("text", ""))
            else:
                # Some wrappers expose objects with a .text attr
                pieces.append(getattr(part, "text", str(part)))
        return "\n".join(pieces)
    return str(content)

def coerce_ai_to_text(ai: AIMessage) -> AIMessage:
    text = _to_text(ai.content)
    # Rewrap as a new AIMessage keeping useful metadata
    return AIMessage(
        content=text,
        additional_kwargs=ai.additional_kwargs,
        response_metadata=getattr(ai, "response_metadata", None)
    )