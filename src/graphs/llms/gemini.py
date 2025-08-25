from langchain_google_genai import ChatGoogleGenerativeAI


llm_low = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-lite",
    temperature=0.5,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)
llm_med = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.5,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)
llm_high  = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0.5,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)