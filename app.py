from typing import Literal
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import ToolNode
from langchain.schema.runnable.config import RunnableConfig
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

import chainlit as cl

###
from src.graphs.reviewer_graph import create_reviewer_graph
import chainlit as cl

checkpointer = InMemorySaver()
graph = create_reviewer_graph(checkpointer=checkpointer)

# question = "detailed statistics on cosmetics, toileteries and related items production in prodcom data for ireland"

# response = graph.invoke({"messages": [HumanMessage(content=question, name="user")]})

###

@cl.on_message
async def on_message(msg: cl.Message):
    config = {"configurable": {"thread_id": cl.context.session.id, "user_id": "aseem_1"}}
    print("XXXXXXXXXXXX")
    print("XXXXXXXXXXXX")
    print("XXXXXXXXXXXX")
    print("XXXXXXXXXXXX")
    print("XXXXXXXXXXXX")
    print(config)
    print("XXXXXXXXXXXX")
    print("XXXXXXXXXXXX")
    print("XXXXXXXXXXXX")
    print("XXXXXXXXXXXX")
    print("XXXXXXXXXXXX")

    cb = cl.LangchainCallbackHandler()
    final_answer = cl.Message(content="")
    
    for msg, metadata in graph.stream(
        {
            "messages": [HumanMessage(content=msg.content)]
        },
        stream_mode="messages",
        config=RunnableConfig(callbacks=[cb], **config)
    ):
        if (
            msg.content
            and not isinstance(msg, HumanMessage)
            and metadata["langgraph_node"] == "reviewer_agent"
        ):
            await final_answer.stream_token(msg.content)

    await final_answer.send()