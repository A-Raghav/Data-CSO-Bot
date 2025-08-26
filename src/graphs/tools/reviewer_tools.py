import os
import pandas as pd
from pyjstat import pyjstat
from textwrap import dedent
from pyjstat import pyjstat
from typing import List, Annotated
from langgraph.types import Command
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.prebuilt import InjectedState
from langchain_core.tools import tool, InjectedToolCallId

from src.storage.json_stat_archive_db import JSONStatArchiveDB
from src.utils.analyse_table import create_table_analysis
from src.retrieval.hybrid_retrieval import HybridRetrieval
from src.models.structured_outputs import AnalysisPlanSubModel
from src.graphs.analyst_graph import analyst_graph
from src.graphs.llms.gemini import get_llm


retriever = HybridRetrieval(top_k_stage_1=200, top_k_stage_2=20)
cso_archive_reader = JSONStatArchiveDB(compression_level=12)
llm = get_llm(model="gemini-2.5-flash")

@tool("hybrid_retrieval_tool", parse_docstring=True)
def hybrid_retrieval_tool(
    user_prompt: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """
    Tool to invoke the hybrid retrieval and return relevant table IDs.
    
    Args:
        user_prompt (str): The user's question or prompt.

    Returns:
        Command: The command to update the chat with the relevant table IDs.
    """
    relevant_tables_ids = retriever.search(query=user_prompt)

    if not relevant_tables_ids:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content="No relevant tables found.",
                        tool_call_id=tool_call_id,
                        name="relevant_tables_metadata",
                    )
                ]
            }
        )
    else:

        csv_save_dir = "cache/"
        relevant_tables_metadata = []
        contexts_dict = {}


        for table_id in relevant_tables_ids:
            csv_fp = csv_save_dir + f"{table_id}.csv"

            # check if "<table_id>.csv" exists. If not, read the pyjstat-file from artifacts and save the DataFrame as "<table_id>.csv"
            if not os.path.exists(csv_fp):
                for _, ds, _ in cso_archive_reader.read("artifacts/cso_bkp/cso_archive/jsonstat_archive.sqlite", table_id=table_id, with_labels=True):
                    df: pd.DataFrame = pyjstat.from_json_stat(ds)[0]
                df.to_csv(csv_fp, index=False)
            else:
                df = pd.read_csv(csv_fp)
            
            context_list = create_table_analysis(df, table_id)
            contexts_dict[table_id] = "\n".join(context_list)
            
        system_message = dedent(
            """\
                # ROLE: I am a planner agent.

                # RETURN FORMAT (Pydantic):
                    - table_id: str = Field(description="The ID of the table.")
                    - analysis_plan: list[str] = Field(description="The low-level analysis plan for the table-ID. Contains a list of steps.")
                ```

                # INSTRUCTIONS:
                - Create a high-level plan for the data-analyst agent to carry out its analysis step-by-step.
                - Be concise, do not go over 3-4 steps.
            """
        )

        inputs = []
        for table_id in relevant_tables_ids:
            context = contexts_dict[table_id]
            human_message = f"Question : {user_prompt}\n\n Context:\n{context}"
            inputs.append((SystemMessage(content=system_message, name="planner_agent"), HumanMessage(content=human_message, name="user")))

        msgs = llm.with_structured_output(AnalysisPlanSubModel).batch(inputs)
        res_list = [msg.model_dump() for msg in msgs]

        # print(f"HYBRID_RETRIEVAL_TOOL: Planner agent created analysis plans for {len(res_list)} tables.")
        for res_dict in res_list:
            table_id = res_dict["table_id"]
            analysis_plan = res_dict["analysis_plan"]

            if table_id in relevant_tables_ids:
                relevant_tables_metadata.append(
                    {
                        "table_id": table_id,
                        "context": contexts_dict.get(table_id, ""),
                        "analysis_plan": analysis_plan
                    }
                )

        tool_message_list = []
        for relevant_table_metadata in relevant_tables_metadata:
            tool_message_list.append(f"Table ID: {relevant_table_metadata['table_id']}")
            tool_message_list.append(f"Context: {relevant_table_metadata['context']}")
            tool_message_list.append(f"Analysis Plan: {relevant_table_metadata['analysis_plan']}")
            tool_message_list.append("")

        tool_message = "\n".join(tool_message_list)

        return Command(
            update={
                "relevant_tables_metadata": relevant_tables_metadata,
                "messages": [
                    ToolMessage(
                        # content=tool_message,
                        content=f"Found {len(relevant_tables_ids)} relevant tables. The table-IDs are: {', '.join(relevant_tables_ids)}",
                        tool_call_id=tool_call_id,
                        name="relevant_tables_metadata"
                    )
                ]
            }
        )

@tool("data_analyst_tool", parse_docstring=True)
def data_analyst_tool(
    table_ids: List[str],
    # question: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
):
    """
    Tool to invoke the data analyst agent and return the final analysis.
    
    Args:
        table_ids (List[str]): A list containing table-IDs of the tables to analyze.
        state (dict): The current state of the conversation.
        tool_call_id (str): The ID of the tool call.

    Returns:
        Command: The command to update the chat with the data analyst's response.
    """
    question = state["question"]
    relevant_tables_metadata = state["relevant_tables_metadata"]
    reports_dict = state.get("reports", {})

    for relevant_table_metadata in relevant_tables_metadata:
        if relevant_table_metadata["table_id"] in table_ids:
            analysis_plan = "\n".join(relevant_table_metadata["analysis_plan"])
            context = relevant_table_metadata["context"]
            break
    
    batch = []

    for relevant_table_metadata in relevant_tables_metadata:
        table_id = relevant_table_metadata["table_id"]
        # print("XXX", table_id, table_ids)
        if table_id in table_ids:
            analysis_plan = "\n".join(relevant_table_metadata["analysis_plan"])
            context = relevant_table_metadata["context"]
            batch.append(
                {"table_id": table_id, "question": question, "context": context, "analysis_plan": analysis_plan}
            )

    responses = analyst_graph.batch(batch)

    content = []

    for i in range(len(responses)):
        table_id = batch[i]["table_id"]
        response = responses[i]
        reports_dict[table_id] = reports_dict.get(table_id, []) + response["report"]
        content.append(f"### Analysis for Table ID: {table_id}\n")
        content.append(response["messages"][-1].content)
        content.append("")

    content = "\n".join(content)

    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=content,
                    tool_call_id=tool_call_id,
                    name="data_analyst_tool",
                )
            ],
            "reports": reports_dict
        }
    )

@tool("provenance_tool", parse_docstring=True) #, return_direct=True)
def provenance_tool(
    table_id: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
):
    """
    Tool to retrieve the provenance information (analysis report containing low-level code used for generating analysis) for a specific table.

    Args:
        table_id (str): The ID of the table to retrieve provenance information for.
        state (dict): The current state of the conversation.
        tool_call_id (str): The ID of the tool call.

    Returns:
        Command: The command to update the chat with the provenance information.
    """
    report_text_list = []
    reports_dict = state.get("reports", {})
    report = reports_dict.get(table_id, [])

    for i, entry in enumerate(report):
        report_text_list.append(f"### Task {i+1}: {entry['task']}\n")
        report_text_list.append(f"**Code:**\n```python\n{entry['code']}\n```")
        report_text_list.append(f"**Output:**\n```python\n{entry['result']}\n```")
        report_text_list.append("")

    report_text = "\n".join(report_text_list)

    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=report_text,
                    tool_call_id=tool_call_id,
                    name="provenance_tool",
                )
            ]
        }
    )