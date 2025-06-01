
import os
import openai
from py2neo import Graph, Node, Relationship
from typing import List, Dict

openai.api_key = os.getenv("OPENAI_API_KEY")

# === Connect to Neo4j ===
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = os.getenv("NEO4J_PASSWORD")
graphdb = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

# === Step 3.1.1: Document chunking ===
def chunk_text(text: str, max_tokens: int = 600) -> List[str]:
    words = text.split()
    return [" ".join(words[i:i+max_tokens]) for i in range(0, len(words), max_tokens)]

# === Step 3.1.2: Extract Entities, Relationships, Claims ===
def extract_kg_elements(chunk: str) -> Dict:
    prompt = f"""
    Extract entities, relationships, and claims from the following text:
    TEXT:
    {chunk}

    Return JSON with lists of 'entities' (with descriptions), 'relationships' (source, target, description), and 'claims'.
    """
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return eval(response['choices'][0]['message']['content'])

# === Step 3.1.3: Insert into Neo4j Graph ===
def insert_into_neo4j(kg_elements: Dict):
    tx = graphdb.begin()
    nodes = {}
    for entity in kg_elements['entities']:
        node = Node("Entity", name=entity['name'], description=entity['description'])
        tx.merge(node, "Entity", "name")
        nodes[entity['name']] = node

    for rel in kg_elements['relationships']:
        source = nodes.get(rel['source'])
        target = nodes.get(rel['target'])
        if source and target:
            r = Relationship(source, "RELATED_TO", target, description=rel['description'])
            tx.merge(r)

    for claim in kg_elements['claims']:
        claim_node = Node("Claim", text=claim)
        tx.create(claim_node)
    tx.commit()

# === Step 3.1.5 and 3.1.6: Summarize Communities and Generate Answer ===
def summarize_and_answer(question: str, num_nodes: int = 20) -> str:
    query = f"""
    MATCH (e:Entity)-[r]->(e2:Entity)
    RETURN e.name AS source, e.description AS source_desc, 
           e2.name AS target, e2.description AS target_desc, 
           r.description AS rel_desc
    LIMIT {num_nodes}
    """
    data = graphdb.run(query).data()
    elements = [
        f"{row['source']}: {row['source_desc']}; {row['target']}: {row['target_desc']}; Relation: {row['rel_desc']}"
        for row in data
    ]
    prompt = f"""
    Given the following knowledge graph relationships, answer the question:
    {question}

    CONTEXT:
    {elements}
    """
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response['choices'][0]['message']['content']

# === Example Usage ===
if __name__ == "__main__":
    text = """NeoChip’s (NC) shares surged in their first week of trading on the NewTech Exchange. However, market analysts caution that the chipmaker’s public debut may not reflect trends for other technology IPOs. NeoChip, previously a private entity, was acquired by Quantum Systems in 2016. The innovative semiconductor firm specializes in low-power processors for wearables and IoT devices."""
    chunks = chunk_text(text)
    for chunk in chunks:
        elements = extract_kg_elements(chunk)
        insert_into_neo4j(elements)
    answer = summarize_and_answer("What is the relationship between NeoChip and Quantum Systems?")
    print("\nGenerated Answer:\n", answer)

