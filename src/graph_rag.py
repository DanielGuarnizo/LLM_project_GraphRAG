from src.utils.knowledge_graph_utils import initialize_session_kg_db
from langchain_core.documents import Document
from typing import TypedDict
from src.abstract_rag_system import AbstractRAGSystem
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_neo4j import GraphCypherQAChain
from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    question: str
    graph_context: str
    answer: str

class GraphRAG(AbstractRAGSystem):
    def __init__(self, kg_db_name:str):
        super().__init__()
        self.kg = initialize_session_kg_db(kg_db_name=kg_db_name)
        self.cypher_llm = ChatOpenAI(model="gpt-4o", temperature=0)
        # self.cypher_prompt = PromptTemplate(
        #     template="""
        #     You are an expert at generating Cypher queries for Neo4j.
        #     Use the following schema to generate a Cypher query that answers the given question.
        #     Make the query flexible by using case-insensitive matching and partial string matching where appropriate.
        #     Use OR when matching multiple relevant concepts to increase recall.
        #     Search both paper titles and summaries to find relevant results.

        #     Schema:
        #     {schema}

        #     Question: {question}

        #     Cypher Query:""",
        #     input_variables=["schema", "question"],
        # )
        self.cypher_prompt = PromptTemplate(
            template="""
            You are an expert Cypher agent designed to answer questions by generating correct Cypher queries for a Neo4j graph.

            The Neo4j graph contains the following node labels:
            - Document
            - Paper
            - Author
            - Method
            - Topic
            - Finding
            - Dataset
            - Institution
            - Task

            Each node has some properties. The important ones are:
            - Paper: id, title, summary, url
            - Author: id, title, summary
            - Method: id, title, summary
            - Topic: id, title, summary
            - Dataset: id, title, summary, url
            - Institution: id, title, url
            - Task: id, title, summary
            - Finding: id, title, summary
            - Document: id, title, url, text, text_content, summary

            The graph also contains the following relationship types:
            - MENTIONS
            - AUTHORED
            - USES_METHOD
            - DISCUSSES
            - RELATED_TO
            - ADDRESSES_TASK
            - AFFILIATED_WITH
            - USES_DATASET
            - REPORTS

            These relationships connect nodes in the following intuitive ways:
            - (Author)-[:AUTHORED]->(Paper)
            - (Paper)-[:USES_METHOD]->(Method)
            - (Paper)-[:USES_DATASET]->(Dataset)
            - (Paper)-[:REPORTS]->(Finding)
            - (Paper)-[:DISCUSSES]->(Topic)
            - (Paper)-[:ADDRESSES_TASK]->(Task)
            - (Author)-[:AFFILIATED_WITH]->(Institution)
            - (Document)-[:MENTIONS]->(Method|Topic|Dataset|Paper|Author)

            Use these facts to generate Cypher queries that can answer user questions. Always limit the number of returned results to 10 unless the user asks for more.

            If a user question cannot be answered with the graph structure, return "No relevant Cypher query possible."

            Return only the Cypher query without explanations.

            Question: {question}
            """,
            input_variables=["question"]
        )
        self.qa_prompt = PromptTemplate(
            template="""You are an assistant for question-answering tasks. 
            Use the following Cypher query results to answer the question. If you don't know the answer, just say that you don't know. 
            Use three sentences maximum and keep the answer concise. If topic information is not available, focus on the paper titles.
            
            Question: {question} 
            Cypher Query: {query}
            Query Results: {context} 
            
            Answer:""",
            input_variables=["question", "query", "context"],
        )
        self.graph_rag_prompt_template = PromptTemplate(
            template="""You are an assistant for question-answering tasks. 
            Use the following pieces of retrieved context from a graph database to answer the question. If you don't know the answer, just say that you don't know. 
            Use three sentences maximum and keep the answer concise:
            Question: {question} 
            Graph Context: {graph_context}
            Answer: 
            """,
            input_variables=["question", "graph_context"],
        )
    def graph_search(self, state:State):
        # Set up Graph RAG Chain
        graph_rag_chain = GraphCypherQAChain.from_llm(
            cypher_llm=self.cypher_llm,                  # LLM used to generate the Cypher query from the user's question
            qa_llm=self.qa_llm,                      # LLM used to turn the Cypher result into a natural language answer
            validate_cypher=True,           # LLM validates the generated Cypher query before execution
            graph=self.kg,                        # Your Neo4j graph object (from langchain_neo4j or similar)
            verbose=True,                    # Logs intermediate steps for debugging
            return_intermediate_steps=True, # Allows inspection of Cypher queries + raw results
            return_direct=True,              # Skip LLM answering step and return Cypher results directly
            allow_dangerous_requests=True,                 
            cypher_prompt=self.cypher_prompt,    # Custom prompt to guide Cypher generation
            qa_prompt=self.qa_prompt,            # Custom prompt to guide final answer generation
        )
        generation = graph_rag_chain.invoke({"query": state["question"]})
        graph_context = generation.get("result", "")[0] if isinstance(generation, list) else generation.get("result", "")
        return {"graph_context":graph_context}
    
    def generate(self, state: State):
        graph_context = state["graph_context"]
        rag_prompt = self.graph_rag_prompt_template.format(
            question=state["question"],
            graph_context=graph_context
        )
        response = self.qa_llm.invoke([
            HumanMessage(content=rag_prompt)
        ])
        return {"answer": response.content}
    
    def get(self):
        graph_builder = StateGraph(State).add_sequence([self.graph_search, self.generate])
        graph_builder.add_edge(START, "graph_search")
        graph_builder.add_edge("generate", END)
        graph = graph_builder.compile()
        return graph