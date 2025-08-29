import gc
import json
import bm25s
import Stemmer
import pandas as pd
from google.genai import types
from pydantic import BaseModel, Field
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from src.graphs.llms.gemini import get_llm


class TableSelectionSubclass(BaseModel):
    table_id: str = Field(description="Table ID.")
    explanation: str = Field(description="Concise 1-liner explanation behind why this table is relevant.")


class TableSelection(BaseModel):
    relevant_tables: list[TableSelectionSubclass] = Field(description="List of relevant tables with explanations.")


class HybridRetrieval:
    def __init__(self, top_k_stage_1: int, top_k_stage_2: int):
        self.top_k_stage_1 = top_k_stage_1
        self.top_k_stage_2 = top_k_stage_2
        self._instantiate_stage_1()
        self._instantiate_stage_2()
        self._instantiate_stage_3()

    def _instantiate_stage_1(self):
        self.stemmer = Stemmer.Stemmer("english")
        self.retriever = bm25s.BM25.load("artifacts/bm25", load_corpus=True)
        with open("artifacts/bm25/corpus.jsonl", "r") as f:
            self.corpus = [json.loads(line) for line in f]

    def _instantiate_stage_2(self):
        embeddings = GoogleGenerativeAIEmbeddings(
            model="gemini-embedding-001",
            task_type="semantic_similarity",
            config=types.EmbedContentConfig(
                    output_dimensionality=3072,
                    task_type="SEMANTIC_SIMILARITY",
                )
        )
        self.vector_store = FAISS.load_local(
            folder_path="artifacts/cso_smry/faiss_index",
            embeddings=embeddings,
            allow_dangerous_deserialization=True
        )
    
    def _instantiate_stage_3(self):
        self.llm = get_llm(model="gemini-2.5-flash-lite")

    def _create_context(self, table_ids: list) -> str:
        context = []
        for table_id in table_ids:
            doc = self.vector_store.docstore.search(table_id)
            sample_questions_str = "\n  - ".join(doc.metadata["sample_questions"])
            text_chunk_list = [
                f"**Table ID**: {doc.id}",
                f"**Table Name (and Category)**: {doc.metadata['table_name']} ({doc.metadata['subject']}: {doc.metadata['product']})",
                f"**Table Summary**: {doc.metadata['description']}",
                f"**Fields**: {', '.join(doc.metadata['columns'])}",
                f"**Statistics**: {', '.join(doc.metadata['statistics_units'])}",
                f"**Sample Questions**:",
                f"  - {sample_questions_str}"
            ]
            text_chunk = "\n".join(text_chunk_list)
            context.append(text_chunk)
        return "\n\n".join(context)

    def search(self, query: str):
        # Stage 1: Lexical Search
        query_tokens = bm25s.tokenize(query, stemmer=self.stemmer)
        docs, scores = self.retriever.retrieve(query_tokens, k=self.top_k_stage_1, corpus=self.corpus)
        stage_1_results = {
            doc["id"] : float(score) for doc, score in zip(docs[0], scores[0])
        }

        # Stage 2: Semantic Search
        very_high_integer = 10000000 # total number of docs is ~80K, 10M limit set.
        docs_with_scores = self.vector_store.similarity_search_with_score(
            query,
            fetch_k=very_high_integer,
            k=very_high_integer,
            # k=self.top_k_stage_2,
            filter=lambda x: x["id"] in stage_1_results
        )
        stage_2_results = {
            doc.metadata["id"]: float(score) for doc, score in docs_with_scores
        }

        # Convert to pandas dataframe
        ids = list(stage_1_results.keys())

        records = {
            "id": ids,
            "stage_1_score": [stage_1_results[id] for id in ids],
            "stage_2_score": [stage_2_results.get(id, 0) for id in ids],
        }
        df = pd.DataFrame(records)
        top_20_relevant_ids = df.sort_values(by="stage_2_score", ascending=True)[:20]["id"].tolist()
        
        del df
        gc.collect()

        if not top_20_relevant_ids:
            return []

        # Stage 3: LLM based relevant-table selection
        context = self._create_context(top_20_relevant_ids)
        prompt_list = [
            "#GOAL: Given the following tables context, select up to 5 of the possible relevant tables based on the question asked.",
            "",
            "# TABLE CONTEXT:",
            context,
            "",
            "# QUESTION: " + query,
        ]
        prompt = "\n".join(prompt_list)
        response = self.llm.with_structured_output(TableSelection).invoke(prompt)
        response_dict = response.model_dump()
        relevant_tables_ids = [
            item["table_id"] for item in response_dict["relevant_tables"]
        ]

        return relevant_tables_ids