import json
import bm25s
import Stemmer
import pandas as pd
from google.genai import types
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings


class HybridRetrieval:
    def __init__(self, top_k_stage_1: int, top_k_stage_2: int):
        self.top_k_stage_1 = top_k_stage_1
        self.top_k_stage_2 = top_k_stage_2
        self._instantiate_stage_1()
        self._instantiate_stage_2()

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

        # return stage_1_results, stage_2_results, docs_with_scores
        records = {
            "id": ids,
            "stage_1_score": [stage_1_results[id] for id in ids],
            "stage_2_score": [stage_2_results.get(id, 0) for id in ids],
        }

        return pd.DataFrame(records)# , stage_1_results, stage_2_results