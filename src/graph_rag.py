from src.utils.knowledge_graph_utils import initialize_session_kg_db
from langchain_core.documents import Document
from typing import TypedDict
from src.abstract_rag_system import AbstractRAGSystem
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_neo4j import GraphCypherQAChain
from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from src.global_query_answerer import GlobalQueryAnswerer


class State(TypedDict):
    question: str
    answer: str

class GraphRAG(AbstractRAGSystem):
    def __init__(
        self, 
        kg_db_name:str,
        summary_dir:str
    ):
        super().__init__()
        self.kg = initialize_session_kg_db(kg_db_name=kg_db_name)
        # initialize GraphRAG
        self.community_anwer = GlobalQueryAnswerer(
            summary_dir=summary_dir,
        )


    def generate(self, state: State):
        question = state["question"]

        response = self.community_anwer.answer_query(query=question)
        return {"answer": response}
    
    def get(self):
        graph_builder = StateGraph(State).add_sequence([self.generate])
        graph_builder.add_edge(START, "generate")
        graph_builder.add_edge("generate", END)
        graph = graph_builder.compile()
        return graph