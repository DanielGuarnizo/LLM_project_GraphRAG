from langchain_community.graphs import Neo4jGraph


#TODO MMAKE  SURE TO TRUCATE THE INPUT FOR THE CONTEXT WINDOW UP TO 6000 TOKENS 

def prioritize_edges(
        kg:Neo4jGraph,
        community_id: int, 
        label_community: str):
    """
    Returns a list of prioritized edges in the format:
    (edge_id, source_id, source_label, source_description, target_id, targer_label, target_description, edge_description)
    sorted by combined degree of source and target nodes (descending).
    """

    query = f"""
    MATCH (source)-[r]->(target)
    WHERE source.{label_community} = {community_id} AND target.{label_community} = {community_id}
    WITH r, source, target,
        (size([()-->(source) | 1]) + size([()<--(source) | 1]) +
        size([()-->(target) | 1]) + size([()<--(target) | 1])) AS combined_degree
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

    # query = f"""
    # MATCH (source)-[r]->(target)
    # WHERE source.communityId = {community_id} AND target.communityId = {community_id}
    # WITH r, source, target,
    #     (size([()-->(source) | 1]) + size([()<--(source) | 1]) +
    #     size([()-->(target) | 1]) + size([()<--(target) | 1])) AS combined_degree
    # ORDER BY combined_degree DESC
    # WITH id(r) AS edge_id,
    #     id(source) AS source_id,
    #     id(target) AS target_id,
    #     labels(source)[0] AS source_label,
    #     labels(target)[0] AS target_label,
    #     [k IN keys(source) WHERE k <> 'communityId' | toString(source[k])] AS source_props,
    #     [k IN keys(target) WHERE k <> 'communityId' | toString(target[k])] AS target_props,
    #     [k IN keys(r) | toString(r[k])] AS edge_props,
    #     type(r) AS rel_type
    # RETURN edge_id,
    #     source_id,
    #     source_label,
    #     apoc.text.join(source_props, ", ") AS source_description,
    #     target_id,
    #     target_label,
    #     apoc.text.join(target_props, ", ") AS target_description,
    #     CASE WHEN size(edge_props) > 0 THEN apoc.text.join(edge_props, ", ") ELSE rel_type END AS edge_description
    # """
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
