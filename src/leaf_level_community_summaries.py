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
)-> list:
    """
    Generate and save summaries for each C3 community (leaf-level) in the knowledge graph.
    Each summary is saved as a JSON file in the output_dir.
    """
    non_useful_communities = []
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
        kg_data = prioritize_edges(
            kg, 
            community_id=community_id,
            label_community="C3_CommunityId"
        )
        entities_str, relationships_str = format_kg_output(kg_data)

        if not kg_data:
            print(f"⚠️ Skipping Community {community_id}: Insufficient data.")
            non_useful_communities.append(community_id)
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
        Output:
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]

        #TODO use documen database such a MongoDB
        try:
            filename = os.path.join(output_dir, f"C3_{community_id}.json")
            if not os.path.exists(filename):
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
                
                with open(filename, "w") as f:
                    json.dump(structured_summary, f, indent=2)

                print(f"✅ Saved structured summary to {filename}")
            else: 
                print(f"✅ Community Summary already esist for Community {community_id}")
        except Exception as e:
            print(f"❌ Error processing community {community_id}: {e}")
    return non_useful_communities