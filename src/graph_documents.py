import os
import pickle
from typing import List, Tuple, Union
from langchain_openai import ChatOpenAI
from langchain_experimental.graph_transformers import LLMGraphTransformer
from src.utils.fetch_and_split_documents import fetch_and_split_documents_fulltext, fetch_and_split_documents
from src.utils.vectorstore_utils import milvus_ingest_documents


def compute_graph_documents_given_query(
    langchain_project_name: str,
    arxiv_query: str,
    max_results: int,
    milvus_db_path: str,
    graph_document_path: str,
    allowed_nodes: List[str] = [],
    allowed_relationships: Union[List[str], List[Tuple[str, str, str]]] = [],
    node_properties: Union[bool, List[str]] = False,
    relationship_properties: Union[bool, List[str]] = False,
    full_text:  bool = False
):
    # Specify the project to clear reading in langchain smith 
    os.environ["LANGCHAIN_PROJECT"] = langchain_project_name

    # Check if graph_documents already exist
    if os.path.exists(graph_document_path):
        return "Graph Document already exist"
    else:
        # Extract data given the query and process it 
        if full_text:
            folder_name = os.path.splitext(os.path.basename(graph_document_path))[0]
            doc_splits = fetch_and_split_documents_fulltext(search_query=arxiv_query, max_results=max_results, folder_name=folder_name)
        else:
            doc_splits = fetch_and_split_documents(search_query=arxiv_query, max_results=max_results)

        # check if milvus db already exist
        if not os.path.exists(milvus_db_path):
            # if not exist then ingest documents
            milvus_ingest_documents(
                doc_splits,
                milvus_db_path=milvus_db_path,
            )

        # initialize model that will build up the kg from the documents splitted
        graph_llm = ChatOpenAI(model_name="o4-mini-2025-04-16")
        graph_transformer = LLMGraphTransformer(
            llm=graph_llm,
            allowed_nodes=allowed_nodes,
            node_properties=node_properties,
            allowed_relationships=allowed_relationships,
            relationship_properties=relationship_properties
        )

        #! actual action, note that this cost money
        print("🧠 Converting documents into graph structure... This might take a while ⏳")
        graph_documents = graph_transformer.convert_to_graph_documents(doc_splits)
        print("✅ Graph conversion completed!")

        # Save graph_documents for future retrieval 
        with open(graph_document_path, "wb") as f:
            pickle.dump(graph_documents, f)

    return f"Graph Document created and saved in {graph_document_path}"

