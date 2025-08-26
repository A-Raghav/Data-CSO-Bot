from langchain_google_genai import ChatGoogleGenerativeAI
from google.genai import types


def get_llm(
    model: str = "gemini-2.5-flash-lite",
    temperature: float = 0.5,
    max_tokens: int = None,
    timeout: float = None,
    max_retries: int = 2,
    dynamic_thinking: bool = True
):
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=-1)
    ) if dynamic_thinking else None
    return ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        max_retries=max_retries,
        config=config
    )