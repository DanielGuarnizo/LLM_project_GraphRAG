
import os
import pickle
from langchain_neo4j import Neo4jGraph
from neo4j import GraphDatabase

from src.utils.config_utils import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE

driver = GraphDatabase.driver(uri=NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

def check_if_kg_db_exist(
    kg_db_name:str
):
    with driver.session(database="system") as session:
        neo4l_dbs = [record["name"] for record in session.run("SHOW DATABASES")]

        if kg_db_name in neo4l_dbs:
            return True
        else:
            return False
        
def initialize_session_kg_db(
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

        raise RuntimeError(f"Pikle exist then probably and error occurs during the creation of the db, most probably the name:") 
        
    

def create_kg_db_from_graph_documents(
    kg_db_name:str,
    graph_document_path:str
):
    # Check if KG DB already exists
    if check_if_kg_db_exist(kg_db_name=kg_db_name):
        return "Knowledge Graph already exists"
    try:
        # Load graph documents and create KG DB
        with open(graph_document_path, "rb") as f:
            graph_documents = pickle.load(f)

        with driver.session(database="system") as session:
            session.run(f"CREATE DATABASE {kg_db_name}")
        kg = Neo4jGraph(
            url=NEO4J_URI,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD,
            database=kg_db_name
        )
        kg.add_graph_documents(graph_documents, include_source=False)
        return "Knowledge Graph Database was created successfully"
    except Exception as e:
        raise RuntimeError(f"Error during Knowledge Graph creation: {str(e)}") from e

