import os
from langchain_milvus import Milvus
from langchain_huggingface import HuggingFaceEmbeddings

embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def milvus_ingest_documents(
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

def provide_retriever_to_milvus_db(
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
