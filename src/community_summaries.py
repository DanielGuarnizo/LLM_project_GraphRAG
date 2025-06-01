# from langchain_community.graphs import Neo4jGraph
# from langchain_openai import ChatOpenAI
# from langchain.prompts import PromptTemplate
# from langchain_core.messages import HumanMessage, SystemMessage

# from src.utils.community_summnaries_utils import prioritize_edges, format_kg_output

# def project_db_in_a_graph(
#     kg_db_name:str,
#     kg:Neo4jGraph
# ):
#     # Define Cypher
#     cypher = """
#     CALL gds.graph.list()
#     """

#     # get the graph_db already projected
#     graphs =  kg.query(query=cypher)
#     graphs_db = [graph["database"] for graph in graphs]

#     # project if needed the database in a graph
#     if kg_db_name in graphs_db:
#         print("There exist a Graph associated to the database")
        
#     else:
#         print("There is not a Graph associated to the database")
#         print("Creating Graph in memory")
#         labels = kg.query(query=
#             """
#             CALL db.labels() YIELD label
#             RETURN collect(label) AS allLabels;
#             """
#         )[0]["allLabels"]
        
#         relationships = kg.query(query=
#             """
#             CALL db.relationshipTypes() YIELD relationshipType
#             RETURN collect(relationshipType) AS allTypes;
#             """
#         )[0]["allTypes"]

#         project_query = f"""
#         CALL gds.graph.project(
#         '{kg_db_name}',
#         {labels},
#         {relationships}
#         )
#         """

#         # project the database in a graph 
#         kg.query(query=project_query)

#         print("Graph created succesfully")

#     return 


# def identify_communitiesin_kg(
#     kg_db_name: str,
#     kg: Neo4jGraph
# ):
#     # Step 1: Check if any node already has communityId property
#     check_query = """
#         MATCH (n)
#         WHERE exists(n.communityId)
#         RETURN count(n) > 0 AS hasCommunityId
#     """
#     result = kg.query(check_query)
    
#     # result is usually a list of dicts, get first record value
#     has_community_id = False
#     if result and isinstance(result, list):
#         has_community_id = result[0].get("hasCommunityId", False)
    
#     # Step 2: Only run Leiden if no communityId property found
#     if not has_community_id:
#         leiben_property_cypher = f"""
#             CALL gds.alpha.leiden.write(
#             '{kg_db_name}',
#             {{writeProperty: 'communityId' }}
#             )
#             YIELD communityCount, modularity;
#         """
#         kg.query(query=leiben_property_cypher)
#         return "Leiden algorithm executed: communities identified and written."
#     else:
#         return "Community property 'communityId' already exists; no action taken."

# def get_nodes_in_each_community(
#     kg:Neo4jGraph
# ):
#     community_nodes_cypher = """
#     MATCH (n)
#     WHERE exists(n.communityId)
#     RETURN n.communityId AS communityId, collect(id(n)) AS nodeIds
#     """
#     # Dictionary in which key are the community id and the values id a list of nodes id's that belong to such community
#     community_nodes = {res['communityId']: res['nodeIds'] for res in kg.query(community_nodes_cypher)}

#     return community_nodes


# def create_communities_to_kg(
#     kg:Neo4jGraph,
#     kg_db_name:str,
# ):

#     # Get entity relationship data to generate summary
#     #TODO iterate over all community_id getted from get_nodes_in_each_community
#     kg_data = prioritize_edges(kg, community_id=12)
#     entities_str, relationships_str = format_kg_output(kg_data)

#     if entities_str == None or relationships_str== None:
#         print("Community cannot be summaries for lack of information")
#         return 

#     # Print or write to file
#     print(entities_str)
#     print()
#     print(relationships_str)
    
#     # Define system and human prompt 
#     system_prompt = """
#     ---Role---
#     You are an AI assistant that helps a human analyst to perform general information discovery. Information
#     discovery is the process of identifying and assessing relevant information associated with certain
#     entities (e.g., organizations and individuals) within a network.
#     ---Goal---
#     Write a comprehensive report of a community, given a list of entities that belong to the community as well
#     as their relationships and optional associated claims. The report will be used to inform decision-makers
#     about information associated with the community and their potential impact. The content of this report
#     includes an overview of the community’s key entities, their legal compliance, technical capabilities,
#     reputation, and noteworthy claims.
#     ---Report Structure---
#     The report should include the following sections:
#     - TITLE: community’s name that represents its key entities - title should be short but specific. When
#     possible, include representative named entities in the title.
#     - SUMMARY: An executive summary of the community’s overall structure, how its entities are related to each
#     other, and significant information associated with its entities.
#     - IMPACT SEVERITY RATING: a float score between 0-10 that represents the severity of IMPACT posed by
#     entities within the community. IMPACT is the scored importance of a community.
#     - RATING EXPLANATION: Give a single sentence explanation of the IMPACT severity rating.
#     - DETAILED FINDINGS: A list of 5-10 key insights about the community. Each insight should have a short
#     summary followed by multiple paragraphs of explanatory text grounded according to the grounding rules
#     below. Be comprehensive.
#     Return output as a well-formed JSON-formatted string with the following format:
#     {{
#     "title": <report title>,
#     "summary": <executive summary>,
#     "rating": <impact severity rating>,
#     "rating explanation": <rating explanation>,
#     "findings": [
#     {{
#     "summary":<insight 1 summary>,
#     "explanation": <insight 1 explanation>
#     }},
#     {{
#     "summary":<insight 2 summary>,
#     "explanation": <insight 2 explanation>
#     }}
#     ]
#     }}

#     ---Grounding Rules---
#     Points supported by data should list their data references as follows:
#     "This is an example sentence supported by multiple data references [Data: <dataset name> (record ids);
#     <dataset name> (record ids)]."
#     Do not list more than 5 record ids in a single reference. Instead, list the top 5 most relevant record
#     ids and add "+more" to indicate that there are more.
#     For example:
#     "Person X is the owner of Company Y and subject to many allegations of wrongdoing [Data: Entities (5, 7); Relationships (23); Claims (7, 2, 34, 64, 46, +more)]."
#     Reports (1),
#     where 1, 5, 7, 23, 2, 34, 46, and 64 represent the id (not the index) of the relevant data record.
#     Do not include information where the supporting evidence for it is not provided.

#     ---Example---
#     Input:

#     Entities

#     id,entity,description
#     5,VERDANT OASIS PLAZA,Verdant Oasis Plaza is the location of the Unity March
#     6,HARMONY ASSEMBLY,Harmony Assembly is an organization that is holding a march at Verdant Oasis Plaza

#     Relationships

#     id,source_id,target_id,description
#     37,VERDANT OASIS PLAZA,UNITY MARCH,Verdant Oasis Plaza is the location of the Unity March
#     38,VERDANT OASIS PLAZA,HARMONY ASSEMBLY,Harmony Assembly is holding a march at Verdant Oasis Plaza
#     39,VERDANT OASIS PLAZA,UNITY MARCH,The Unity March is taking place at Verdant Oasis Plaza
#     40,VERDANT OASIS PLAZA,TRIBUNE SPOTLIGHT,Tribune Spotlight is reporting on the Unity march taking place at
#     Verdant Oasis Plaza
#     41,VERDANT OASIS PLAZA,BAILEY ASADI,Bailey Asadi is speaking at Verdant Oasis Plaza about the march
#     43,HARMONY ASSEMBLY,UNITY MARCH,Harmony Assembly is organizing the Unity March
#     Output:

#     {{
#     "title": "Verdant Oasis Plaza and Unity March",
#     "summary": "The community revolves around the Verdant Oasis Plaza, which is the location of the Unity
#     March. The plaza has relationships with the Harmony Assembly, Unity March, and Tribune Spotlight, all of
#     which are associated with the march event.",
#     "rating": 5.0,
#     "rating explanation": "The impact severity rating is moderate due to the potential for unrest or conflict
#     during the Unity March.",
#     "findings": [
#     {{
#     "summary": "Verdant Oasis Plaza as the central location",
#     "explanation": "Verdant Oasis Plaza is the central entity in this community, serving as the location for
#     the Unity March. This plaza is the common link between all other entities, suggesting its significance
#     in the community. The plaza’s association with the march could potentially lead to issues such as
#     public disorder or conflict, depending on the nature of the march and the reactions it provokes. [Data:
#     Entities (5), Relationships (37, 38, 39, 40, 41,+more)]"
#     }},
#     {{
#     "summary": "Harmony Assembly’s role in the community",
#     "explanation": "Harmony Assembly is another key entity in this community, being the organizer of the
#     march at Verdant Oasis Plaza. The nature of Harmony Assembly and its march could be a potential source of
#     threat, depending on their objectives and the reactions they provoke. The relationship between Harmony
#     Assembly and the plaza is crucial in understanding the dynamics of this community. [Data: Entities(6),
#     Relationships (38, 43)]"
#     }},
#     {{
#     "summary": "Unity March as a significant event",
#     "explanation": "The Unity March is a significant event taking place at Verdant Oasis Plaza. This event
#     is a key factor in the community’s dynamics and could be a potential source of threat, depending on the
#     nature of the march and the reactions it provokes. The relationship between the march and the plaza is
#     crucial in understanding the dynamics of this community. [Data: Relationships (39)]"
#     }},
#     {{
#     "summary": "Role of Tribune Spotlight", "explanation": "Tribune Spotlight is reporting on the Unity
#     March taking place in Verdant Oasis Plaza. This suggests that the event has attracted media attention,
#     which could amplify its impact on the community. The role of Tribune Spotlight could be significant in
#     shaping public perception of the event and the entities involved. [Data: Relationships (40)]"
#     }}
#     ]
#     }}
#     """

#     human_prompt = f"""
#     ---Real Data---
#     Use the following text for your answer. Do not make anything up in your answer.
#     Input:
#     {entities_str}

#     {relationships_str}

#     ...Report Structure and Grounding Rules Repeated...
#     Output:
#     """

#     messages = [
#         SystemMessage(
#             content=system_prompt
#         ),
#         HumanMessage(
#             content=human_prompt
#         )
#     ]

#     cs_llm = ChatOpenAI(model_name="o4-mini-2025-04-16")
#     return cs_llm.invoke(messages)





########################################
import os
import json
from typing import List
from langchain_community.graphs import Neo4jGraph
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from src.utils.community_summnaries_utils import prioritize_edges, format_kg_output
def create_leaf_level_community_summaries(
    kg: Neo4jGraph,
    kg_db_name: str,
):
    """
    Generate and save summaries for each C3 community (leaf-level) in the knowledge graph.
    Each summary is saved as a JSON file in the output_dir.
    """
    output_dir = f"./data/community_summaries/{kg_db_name}/C3/"
     # Create the directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True) 
    # exist_ok=True prevents an error if the directory already exists

    # Get all distinct C3 community IDs from the base graph
    community_ids = kg.query("""
        MATCH (n)
        WHERE n.C3_CommunityId IS NOT NULL
        RETURN DISTINCT n.C3_CommunityId AS community_id
    """)

    if not community_ids:
        print("❌ No C3_CommunityId found in graph.")
        return

    cs_llm = ChatOpenAI(model_name="o4-mini-2025-04-16")

    for row in community_ids:
        community_id = row["community_id"]
        print(f"\n▶ Summarizing C3 Community {community_id}...")

        # Extract KG subgraph
        kg_data = prioritize_edges(kg, community_id=community_id)
        entities_str, relationships_str = format_kg_output(kg_data)

        if not entities_str or not relationships_str:
            print(f"⚠️ Skipping Community {community_id}: Insufficient data.")
            continue

        # Prompts
        system_prompt = """
        ---Role---
        You are an AI assistant that helps a human analyst to perform general information discovery. Information
        discovery is the process of identifying and assessing relevant information associated with certain
        entities (e.g., organizations and individuals) within a network.
        ---Goal---
        Write a comprehensive report of a community, given a list of entities that belong to the community as well
        as their relationships and optional associated claims. The report will be used to inform decision-makers
        about information associated with the community and their potential impact. The content of this report
        includes an overview of the community’s key entities, their legal compliance, technical capabilities,
        reputation, and noteworthy claims.
        ---Report Structure---
        The report should include the following sections:
        - TITLE: community’s name that represents its key entities - title should be short but specific. When
        possible, include representative named entities in the title.
        - SUMMARY: An executive summary of the community’s overall structure, how its entities are related to each
        other, and significant information associated with its entities.
        - IMPACT SEVERITY RATING: a float score between 0-10 that represents the severity of IMPACT posed by
        entities within the community. IMPACT is the scored importance of a community.
        - RATING EXPLANATION: Give a single sentence explanation of the IMPACT severity rating.
        - DETAILED FINDINGS: A list of 5-10 key insights about the community. Each insight should have a short
        summary followed by multiple paragraphs of explanatory text grounded according to the grounding rules
        below. Be comprehensive.
        Return output as a well-formed JSON-formatted string with the following format:
        {{
        "title": <report title>,
        "summary": <executive summary>,
        "rating": <impact severity rating>,
        "rating explanation": <rating explanation>,
        "findings": [
        {{
        "summary":<insight 1 summary>,
        "explanation": <insight 1 explanation>
        }},
        {{
        "summary":<insight 2 summary>,
        "explanation": <insight 2 explanation>
        }}
        ]
        }}

        ---Grounding Rules---
        Points supported by data should list their data references as follows:
        "This is an example sentence supported by multiple data references [Data: <dataset name> (record ids);
        <dataset name> (record ids)]."
        Do not list more than 5 record ids in a single reference. Instead, list the top 5 most relevant record
        ids and add "+more" to indicate that there are more.
        For example:
        "Person X is the owner of Company Y and subject to many allegations of wrongdoing [Data: Entities (5, 7); Relationships (23); Claims (7, 2, 34, 64, 46, +more)]."
        Reports (1),
        where 1, 5, 7, 23, 2, 34, 46, and 64 represent the id (not the index) of the relevant data record.
        Do not include information where the supporting evidence for it is not provided.
        """

        human_prompt = f"""
        ---Real Data---
        Use the following text for your answer. Do not make anything up in your answer.
        Input:
        {entities_str}

        {relationships_str}

        ...Report Structure and Grounding Rules Repeated...
        Output:
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]

        #TODO use documen database such a MongoDB
        try:
            # LLM response
            response = cs_llm.invoke(messages)
            raw_content = response.content if hasattr(response, "content") else str(response)

            # Parse returned JSON (may need to strip whitespace or fix formatting if needed)
            summary_data = json.loads(raw_content)

            # Wrap in structured object
            structured_summary = {
                "community_id": f"C3_{community_id}",
                "tokens": len(raw_content.split()),  # simple token estimate
                "summary": summary_data
            }

            # Save to JSON file
            filename = os.path.join(output_dir, f"C3_{community_id}.json")
            with open(filename, "w") as f:
                json.dump(structured_summary, f, indent=2)

            print(f"✅ Saved structured summary to {filename}")

        except Exception as e:
            print(f"❌ Error processing community {community_id}: {e}")
