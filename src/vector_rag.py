from src.utils.vectorstore_utils import provide_retriever_to_milvus_db
from langchain_core.documents import Document
from typing import TypedDict
from src.abstract_rag_system import AbstractRAGSystem
# from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

class State(TypedDict):
    question: str
    context: list[Document]
    answer: str

class VectorRAG(AbstractRAGSystem):
    def __init__(self, milvus_db_path:str):
        super().__init__()
        self.retriever = provide_retriever_to_milvus_db(milvus_db_path=milvus_db_path)
        self.vector_rag_prompt_template = PromptTemplate(
            template="""
            You are an assistant for question-answering tasks. 
            Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that you don't know. 
            Use three sentences maximum and keep the answer concise:
            Question: {question} 
            Context: {context} 
            Answer: 
            """,
            input_variables=["question", "document"],
        )
    def format_docs(self, docs):
        return "\n\n".join(doc.page_content for doc in docs)

    def retrieve(self, state:State):
        retrieved_docs = self.retriever.invoke(state["question"])
        return {"context":retrieved_docs}

    def generate(self, state: State):
        docs_content = self.format_docs(state["context"])
        rag_prompt = self.vector_rag_prompt_template.format(
            question=state["question"],
            context=docs_content
        )
        response = self.qa_llm.invoke([
            HumanMessage(content=rag_prompt)
        ])
        return {"answer": response.content}
    
    
    def get(self):
        graph_builder = StateGraph(State).add_sequence([self.retrieve, self.generate])
        graph_builder.add_edge(START, "retrieve")
        graph_builder.add_edge("generate", END)
        graph = graph_builder.compile()
        return graph
