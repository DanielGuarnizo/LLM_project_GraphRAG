from langchain_community.graphs import Neo4jGraph

# def get_community_entities(
#     kg:Neo4jGraph, 
#     community_id
# ):
#     """
#     Fetches entities belonging to a specific community and returns them in the format:
#     id, entity, description
#     """
#     # entity_query = f"""
#     # MATCH (n)
#     # WHERE n.communityId = {community_id}
#     # RETURN n.id AS id, n.name AS entity, n.description AS description
#     # ORDER BY id
#     # """

#     entity_query = f"""
#     MATCH (n)
#     WHERE n.communityId = {community_id}
#     WITH id(n) AS id,
#         labels(n)[0] AS entity,  
#         [key IN keys(n) WHERE key <> 'communityId' | key + ": " + toString(n[key])] AS props
#     RETURN id,
#         entity,
#         apoc.text.join(props, ", ") AS description
#     ORDER BY id
#     """

#     result = kg.query(entity_query)
#     header = "id,entity,description"
#     rows = [f"{r['id']},{r['entity']},{r['description']}" for r in result]
#     return f"{header}\n" + "\n".join(rows)


# def get_community_relationships(kg, community_id):
#     """
#     Fetches relationships between entities in a specific community and returns them in the format:
#     id, source, target, description
#     """

#     rel_query = f"""
#     MATCH (source)-[r]->(target)
#     WHERE source.communityId = {community_id} AND target.communityId = {community_id}
#     WITH id(r) AS id,
#         labels(source)[0] AS source,
#         labels(target)[0] AS target,
#         type(r) AS relType,
#         [key IN keys(r) | key + ": " + toString(r[key])] AS props
#     RETURN id,
#         source,
#         target,
#         CASE 
#             WHEN size(props) > 0 THEN apoc.text.join(props, ", ")
#             ELSE relType
#         END AS description
#     ORDER BY id
#     """
#     result = kg.query(rel_query)
#     header = "id,source,target,description"
#     rows = [f"{r['id']},{r['source']},{r['target']},{r['description']}" for r in result]
#     return f"{header}\n" + "\n".join(rows)


# def get_community_data_for_prompt(kg, community_id):
#     """
#     Combines entity and relationship CSV sections into a single prompt-ready input block.
#     """
#     entities_csv = get_community_entities(kg, community_id)
#     relationships_csv = get_community_relationships(kg, community_id)

#     return f"""Entities\n{entities_csv}\nRelationships\n{relationships_csv}"""



################################################################################################################################################

#TODO MMAKE  SURE TO TRUCATE THE INPUT FOR THE CONTEXT WINDOW UP TO 6000 TOKENS 


def prioritize_edges(kg:Neo4jGraph, community_id):
    """
    Returns a list of prioritized edges in the format:
    (edge_id, source_id, source_label, source_description, target_id, targer_label, target_description, edge_description)
    sorted by combined degree of source and target nodes (descending).
    """
    query = f"""
    MATCH (source)-[r]->(target)
    WHERE source.communityId = {community_id} AND target.communityId = {community_id}
    WITH r, source, target,
         (size((source)--()) + size((target)--())) AS combined_degree
    ORDER BY combined_degree DESC
    WITH id(r) AS edge_id,
         id(source) AS source_id,
         id(target) AS target_id,
         labels(source)[0] AS source_label,
         labels(target)[0] AS target_label,
         [k IN keys(source) WHERE k <> 'communityId' | toString(source[k])] AS source_props,
         [k IN keys(target) WHERE k <> 'communityId' | toString(target[k])] AS target_props,
         [k IN keys(r) | toString(r[k])] AS edge_props,
         type(r) AS rel_type
    RETURN edge_id,
           source_id,
           source_label,
           apoc.text.join(source_props, ", ") AS source_description,
           target_id,
           target_label,
           apoc.text.join(target_props, ", ") AS target_description,
           CASE WHEN size(edge_props) > 0 THEN apoc.text.join(edge_props, ", ") ELSE rel_type END AS edge_description
    """

    query = f"""
    MATCH (source)-[r]->(target)
    WHERE source.communityId = {community_id} AND target.communityId = {community_id}
    WITH r, source, target,
        (degree(source) + degree(target)) AS combined_degree
    ORDER BY combined_degree DESC
    WITH id(r) AS edge_id,
        id(source) AS source_id,
        id(target) AS target_id,
        labels(source)[0] AS source_label,
        labels(target)[0] AS target_label,
        [k IN keys(source) WHERE k <> 'communityId' | toString(source[k])] AS source_props,
        [k IN keys(target) WHERE k <> 'communityId' | toString(target[k])] AS target_props,
        [k IN keys(r) | toString(r[k])] AS edge_props,
        type(r) AS rel_type
    RETURN edge_id,
        source_id,
        source_label,
        apoc.text.join(source_props, ", ") AS source_description,
        target_id,
        target_label,
        apoc.text.join(target_props, ", ") AS target_description,
        CASE WHEN size(edge_props) > 0 THEN apoc.text.join(edge_props, ", ") ELSE rel_type END AS edge_description
    """
    return kg.query(query)


from collections import OrderedDict

def format_kg_output(kg_data):
    entities = OrderedDict()
    relationships = []

    for item in kg_data:
        # Add source entity
        if item["source_id"] not in entities:
            entities[item["source_id"]] = {
                "id": item["source_id"],
                "entity": item['source_label'],
                "description": item["source_description"]
            }
        # Add target entity
        if item["target_id"] not in entities:
            entities[item["target_id"]] = {
                "id": item["target_id"],
                "entity": item['target_label'],
                "description": item["target_description"]
            }
        # Add relationship
        relationships.append({
            "id": item["edge_id"],
            "source": item["source_id"],
            "target": item["target_id"],
            "description": item["edge_description"]
        })

    # Build CSV strings
    entities_csv = "Entities\nid,entity,description\n" + "\n".join(
        f"{v['id']},{v['entity']},{v['description']}" for v in entities.values()
    )
    relationships_csv = "Relationships\nid,source_id,target_id,description\n" + "\n".join(
        f"{r['id']},{r['source']},{r['target']},{r['description']}" for r in relationships
    )

    return entities_csv, relationships_csv
