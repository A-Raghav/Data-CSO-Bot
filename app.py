import chainlit as cl
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langchain.schema.runnable.config import RunnableConfig

from src.graphs.reviewer_graph import create_reviewer_graph


checkpointer = InMemorySaver()
graph = create_reviewer_graph(checkpointer=checkpointer)

@cl.on_message
async def on_message(msg: cl.Message):
    config = {"configurable": {"thread_id": cl.context.session.id, "user_id": "aseem_1"}}

    cb = cl.LangchainCallbackHandler()
    final_answer = cl.Message(content="")
    
    for msg, metadata in graph.stream(
        {
            "messages": [HumanMessage(content=msg.content)]
        },
        stream_mode="messages",
        config=RunnableConfig(
            # callbacks=[cb],
            **config)
    ):
        if (
            msg.content
            and not isinstance(msg, HumanMessage)
            and metadata["langgraph_node"] == "reviewer_agent"
        ):
            await final_answer.stream_token(msg.content)

    await final_answer.send()