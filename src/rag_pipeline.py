import os
from src.vector_rag import VectorRAG
from src.graph_rag import GraphRAG
from src.graph_documents import compute_graph_documents_given_query
from src.utils.knowledge_graph_utils import create_kg_db_from_graph_documents

class RAGPipeline:
    def __init__(self, config: dict):
        self.config = config
        self.mode = config["mode"]
        self.milvus_db_path = f"./data/milvus_dbs/milvus_{config['kg_db_name']}.db"
        self.graph_document_path = f"./data/graph_documents/{config['kg_db_name']}.pkl"
        self.graph_rag = None
        self.vector_rag = None

    def initialize(self):

        if self.mode == "load":
            if not (os.path.exists(self.milvus_db_path) or os.path.exists(self.graph_document_path)):
                raise FileNotFoundError(f"Milvus DB path or Graph Documents path does not exist, RAG pipele should have mode = 'create' and neede parameters to be created")
        
        if self.mode == "create":
            if not (os.path.exists(self.milvus_db_path) and os.path.exists(self.graph_document_path)):
                status = compute_graph_documents_given_query(
                    langchain_project_name= f"Graph RAG: {self.config['kg_db_name']}",
                    arxiv_query=self.config["arxiv_query"],
                    max_results=self.config["max_results"],
                    milvus_db_path=self.milvus_db_path,
                    graph_document_path= self.graph_document_path,
                    allowed_nodes=self.config["allowed_nodes"],
                    node_properties=self.config["node_properties"],
                    allowed_relationships=self.config["allowed_relationships"],
                    relationship_properties=self.config["relationship_properties"],
                    full_text=self.config["full_text"]
                )
                print(status)

                status = create_kg_db_from_graph_documents(
                    graph_document_path=self.graph_document_path,
                    kg_db_name=self.config["kg_db_name"]
                )
                print(status)
            else:
                print(f"Data already exist with name {self.config['kg_db_name']}")

        self.vector_rag = VectorRAG( 
            milvus_db_path=self.milvus_db_path
        ).get()

        self.graph_rag = GraphRAG(
            kg_db_name=self.config["kg_db_name"],
            summary_dir=self.config['summary_dir']
        ).get()

        