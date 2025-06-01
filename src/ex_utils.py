
from dotenv import load_dotenv
import os
from langchain.globals import set_verbose, set_debug
import arxiv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_milvus import Milvus
from langchain_huggingface import HuggingFaceEmbeddings
from neo4j import GraphDatabase
# from langchain_community.graphs import Neo4jGraph
from langchain_neo4j import Neo4jGraph
import pickle
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_openai import ChatOpenAI
from typing import List, Tuple, Union


set_debug(False)
set_verbose(False)

# set up needed variables 
load_dotenv('.env', override=True)
NEO4J_URI = os.getenv('NEO4J_URI')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')
NEO4J_DATABASE = os.getenv('NEO4J_DATABASE')

driver = GraphDatabase.driver(uri=NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

###
def _fetch_and_split_documents(
    search_query: str,
    max_results: int = 20
):
    # Fetch papers from arXiv
    client = arxiv.Client()
    search = arxiv.Search(
        query=search_query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
    )
    results = client.results(search)

    # Collect document summaries
    docs = []
    for result in results:
        docs.append({
            "title": result.title,
            "summary": result.summary,
            "url": result.entry_id
        })

    # Split summaries into chunks
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=500, chunk_overlap=50
    )
    doc_splits = text_splitter.create_documents(
        [doc["summary"] for doc in docs], metadatas=docs
    )

    print(f"Number of papers: {len(docs)}")
    print(f"Number of chunks: {len(doc_splits)}")
    return doc_splits

##
def _milvus_ingest_documents(
    doc_splits,
    milvus_db_path:str,
    collection_name:str = "rag_milvus"
):
    print("Milvus DB not found. Ingesting provided documents...")

    # 🔍 Print embedding dimension from a sample
    sample_text = doc_splits[0].page_content if hasattr(doc_splits[0], "page_content") else str(doc_splits[0])
    sample_embedding = embedding_model.embed_query(sample_text)
    print(f"Embedding dimension: {len(sample_embedding)}")


    vectorstore = Milvus.from_documents(
        documents=doc_splits,
        collection_name=collection_name,
        embedding=embedding_model,
        connection_args={"uri": milvus_db_path},
    )
    return 

def _provide_retriever_to_milvus_db(
    milvus_db_path:str,
    collection_name:str = "rag_milvus"
):
    if os.path.exists(milvus_db_path):
        print("Milvus DB exists. Connecting to existing database...")
        vectorstore = Milvus(
            embedding_function=embedding_model,
            collection_name=collection_name,
            connection_args={"uri": milvus_db_path},
        )
        retriever = vectorstore.as_retriever()
        return retriever
    else:
        raise FileNotFoundError(f"Milvus DB path does not exist: {milvus_db_path}")


###
def _check_if_kg_db_exist(
    kg_db_name:str
):
    with driver.session(database="system") as session:
        neo4l_dbs = [record["name"] for record in session.run("SHOW DATABASES")]

        if kg_db_name in neo4l_dbs:
            return True
        else:
            return False
        
def _create_kg_db_from_graph_documents(
    kg_db_name:str,
    graph_documents:list
):
    try:
        with driver.session(database="system") as session:
            session.run(f"CREATE DATABASE {kg_db_name}")
        kg = Neo4jGraph(
            url=NEO4J_URI,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD,
            database=kg_db_name
        )
        kg.add_graph_documents(graph_documents)
        return "Knowledge Graph Database was created successfully"
    except Exception as e:
        raise RuntimeError(f"Error during Knowledge Graph creation: {str(e)}") from e

def _initialize_session_kg_db(
    kg_db_name:str
):
    if check_if_kg_db_exist(kg_db_name=kg_db_name):
        kg = Neo4jGraph(
            url=NEO4J_URI,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD,
            database=kg_db_name
        )
        return kg
    elif os.path.exists(f"./data/graph_documents/{kg_db_name}.pkl"):
        print("Pikle exist then probably and error occurs during the creation of the db, most probably the name ")
        build_kg_from_graph_documents(
            graph_document_path=f"./data/graph_documents/{kg_db_name}.pkl",
            kg_db_name=kg_db_name
        )
        return initialize_session_kg_db(kg_db_name=kg_db_name)
        
    
def _build_kg_from_graph_documents(
    graph_document_path: str,
    kg_db_name: str
) -> str:
    # Check if KG DB already exists
    if check_if_kg_db_exist(kg_db_name=kg_db_name):
        return "Knowledge Graph already exists"
    
    try:
        # Load graph documents and create KG DB
        with open(graph_document_path, "rb") as f:
            graph_documents = pickle.load(f)
            success = create_kg_db_from_graph_documents(
                kg_db_name=kg_db_name,
                graph_documents=graph_documents
            )
        
        # Return success status based on return value of `create_kg_db_from_graph_documents`
        if success:
            return "Knowledge Graph created successfully"
        else:
            raise RuntimeError("Knowledge Graph creation failed")

    except Exception as e:
        raise RuntimeError(f"Error during Knowledge Graph creation: {str(e)}") from e


def _compute_graph_documents_given_query(
    langchain_project_name: str,
    arxiv_query: str,
    max_results: int,
    milvus_db_path: str,
    graph_document_path: str,
    allowed_nodes: List[str] = [],
    allowed_relationships: Union[List[str], List[Tuple[str, str, str]]] = [],
    node_properties: Union[bool, List[str]] = False,
):
    # Specify the project to clear reading in langchain smith 
    os.environ["LANGCHAIN_PROJECT"] = langchain_project_name

    # Check if graph_documents already exist
    if os.path.exists(graph_document_path):
        return "Graph Document already exist"
    else:
        # Extract data given the query and process it 
        doc_splits = _fetch_and_split_documents(search_query=arxiv_query, max_results=max_results)

        # check if milvus db already exist
        if not os.path.exists(milvus_db_path):
            # if not exist then ingest documents
            _milvus_ingest_documents(
                doc_splits,
                milvus_db_path=milvus_db_path,
            )

        # initialize model that will build up the kg from the documents splitted
        graph_llm = ChatOpenAI(temperature=0, model_name="gpt-4o")
        graph_transformer = LLMGraphTransformer(
            llm=graph_llm,
            allowed_nodes=allowed_nodes,
            node_properties=node_properties,
            allowed_relationships=allowed_relationships,
        )

        #! actual action, note that this cost money
        print("🧠 Converting documents into graph structure... This might take a while ⏳")
        graph_documents = graph_transformer.convert_to_graph_documents(doc_splits)
        print("✅ Graph conversion completed!")

        # Save graph_documents for future retrieval 
        with open(graph_document_path, "wb") as f:
            pickle.dump(graph_documents, f)

    return f"Graph Document created and saved in {graph_document_path}"



if __name__ == "__main__":
    # kg_db_name = "t30documentsgraph"
    # arxiv_query = (
    #     "('large language model' OR 'prompt engineering') "
    #     "OR ('multi-agent' OR 'agent-based') "
    #     "OR ('theory of mind' OR 'cognitive modeling' OR 'belief modeling')"
    # )
    # graph_document_path = f"./data/graph_documents/{kg_db_name}.pkl"
    # milvus_db_path = f"./data/milvus_dbs/milvus_{kg_db_name}.db"
    # status = compute_graph_documents_given_query(
    #     langchain_project_name= f"Graph RAG: {kg_db_name}",
    #     arxiv_query=arxiv_query,
    #     max_results=30,
    #     milvus_db_path=milvus_db_path,
    #     allowed_nodes=["Paper", "Author", "Topic", "Method", "Dataset"],
    #     node_properties=["title", "summary", "url", "published"],
    #     allowed_relationships= [
    #             "AUTHORED",
    #             "DISCUSSES",
    #             "RELATED_TO",
    #             "USES_METHOD",
    #             "USES_DATASET"
    #         ]
    # )
    # print(status)
    # kg = build_kg_from_graph_documents(
    #     graph_document_path=graph_document_path,
    #     kg_db_name=kg_db_name
    # )
    
    
    # kg_db_name = "t20documentsgraph"
    # arxiv_query = "agent OR 'large language model' OR 'prompt engineering'"
    # graph_document_path = f"./data/graph_documents/{kg_db_name}.pkl"
    # milvus_db_path = f"./data/milvus_dbs/milvus_{kg_db_name}.db"
    # status = compute_graph_documents_given_query(
    #     langchain_project_name= f"Graph RAG: {kg_db_name}",
    #     arxiv_query=arxiv_query,
    #     max_results=20,
    #     milvus_db_path=milvus_db_path,
    #     graph_document_path=graph_document_path,
    #     allowed_nodes=["Paper", "Author", "Topic"],
    #     node_properties=["title", "summary", "url"],
    #     allowed_relationships= ["AUTHORED", "DISCUSSES", "RELATED_TO"]
    # )
    # print(status)
    # kg = build_kg_from_graph_documents(
    #     graph_document_path=graph_document_path,
    #     kg_db_name=kg_db_name
    # )
    
    # ## t40 
    # kg_db_name = "t40documentsgraph"
    # arxiv_query = (
    #     "('large language model' OR 'prompt engineering') "
    #     "OR ('multi-agent' OR 'agent-based') "
    #     "OR ('theory of mind' OR 'cognitive modeling' OR 'belief modeling')"
    # )
    # max_results = 40

    # allowed_nodes = ["Paper", "Author", "Topic", "Method", "Dataset"]

    # node_properties=[
    #     "title", "summary", "url", "published",  # for Paper
    #     "name", "affiliation",                  # for Author
    #     "description"                           # for Method, Dataset
    # ]
    # allowed_relationships=[
    #     "AUTHORED", "DISCUSSES", "RELATED_TO", "USES_METHOD", "USES_DATASET"
    # ]
    
    print("Finish")