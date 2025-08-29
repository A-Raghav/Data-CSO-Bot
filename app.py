import os
import time
import asyncio
import chainlit as cl
from dotenv import load_dotenv
from typing import Literal, Dict, Optional

from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import MessagesState
from langgraph.graph import END, StateGraph, START
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, AIMessageChunk
from langgraph.store.redis.aio import AsyncRedisStore
from langgraph.checkpoint.redis.aio import AsyncRedisSaver

from src.graphs.reviewer_graph import create_reviewer_graph

load_dotenv()

# Get Redis connection from environment or use default for local development
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")

        
async def run_app():
    async with (
        AsyncRedisStore.from_conn_string(redis_url) as store,
        AsyncRedisSaver.from_conn_string(redis_url) as checkpointer,
    ):
        await store.setup()
        await checkpointer.asetup()

        
        print("Building graph...")
        graph = create_reviewer_graph(
            store=store,
            checkpointer=checkpointer,
        )
        print("Graph Built.")
        
        
        @cl.oauth_callback
        def oauth_callback(
            provider_id: str,
            token: str,
            raw_user_data: Dict[str, str],
            default_user: cl.User,
        ) -> Optional[cl.User]:
            return default_user
        
        # Reset Chat button action handler
        @cl.action_callback("reset_chat")
        async def reset_chat(action):
            """Function that gets called when the Reset Chat button is pressed"""
            await cl.Message(content="Resetting chat... Please wait.", author="system").send()
            
            # Delete the thread from the checkpointer
            try:
                thread_id = cl.user_session.get("user").identifier
                await checkpointer.adelete_thread(thread_id=thread_id)
                print("Chat thread has been reset successfully")
            except Exception as e:
                print(f"Error resetting chat thread: {e}")
    
        @cl.set_starters
        async def set_starters():
            return [
                cl.Starter(
                    label="Unemployment rates in Ireland",
                    message="Show me detailed statistics on unemployment rates in Ireland for the last 5 years.",
                    icon="public/starters/jobs.svg",
                ),
                cl.Starter(
                    label="Population growth trends",
                    message="What's the population growth trend in Dublin compared to other cities?",
                    icon="public/starters/population.svg",
                ),
                cl.Starter(
                    label="Ireland renewable-energy mix (shares & totals)",
                    message="Give me the breakdown of renewable energy resources as a percentage share and absolute numbers in recent years in Ireland.",
                    icon="public/starters/energy.svg",
                    command="code",
                ),
                cl.Starter(
                    label="Impact of inflation on spending",
                    message="How has inflation affected consumer spending in the past year?",
                    icon="/public/starters/inflation.svg",
                )
            ]
            
        # Define your header settings
        @cl.on_chat_start
        async def on_chat_start():
            # Check if there's an existing conversation state to restore
            config = {"configurable": {"thread_id": cl.user_session.get("user").identifier}}
            existing_state = await graph.aget_state(config)
            
            # Only restore messages if there are actual past messages
            if existing_state and "messages" in existing_state.values and existing_state.values["messages"]:
                # Add the Reset Chat button element in a restoring previous conversation message, if the chat-session is not new
                # Create and add Reset Chat button to the header (top-left, aligned with Readme)
                reset_chat_element = cl.CustomElement(name="ResetChatButton")
                await cl.Message(
                    content="*Restoring previous conversation...*", 
                    elements=[reset_chat_element],
                    author="Assistant"
                ).send()

                for past_msg in existing_state.values.get("messages", []):
                    if isinstance(past_msg, HumanMessage):
                        msg = cl.Message(content=past_msg.content, type="user_message")
                        await msg.send()
                    elif isinstance(past_msg, AIMessage) and past_msg.content:
                        msg = cl.Message(content=past_msg.content, type="assistant_message")
                        await msg.send()
        @cl.on_message
        async def on_message(message: cl.Message):
            msg = cl.Message(content="")
            pls_wait_msg = cl.Message(content="*Please wait while I process your request...*", author="assistant_message")
            await pls_wait_msg.send()

            config = {"configurable": {"thread_id": cl.user_session.get("user").identifier}}

            # Add the Reset Chat button if this is the first message
            existing_state = await graph.aget_state(config)
            if existing_state and existing_state.values.get("messages", []) == []:
                reset_chat_element = cl.CustomElement(name="ResetChatButton")
                reset_msg = cl.Message(
                    content="",
                    elements=[reset_chat_element],
                    author="Assistant"
                )
                await reset_msg.send()                

            async for chunk, metadata in graph.astream(
                input={"messages": [HumanMessage(content=message.content, name="user")]},
                stream_mode="messages",
                config=config
            ):
                if chunk.content and metadata["langgraph_node"] == "reviewer_agent" and isinstance(chunk, AIMessageChunk):
                    await msg.stream_token(chunk.content)

            await msg.send()
            await pls_wait_msg.remove()
        
asyncio.run(run_app())
