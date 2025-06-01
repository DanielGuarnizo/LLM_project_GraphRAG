from langchain_community.graphs import Neo4jGraph
from collections import defaultdict
from typing import List, Dict


class HierarchicalCommunityDetector:
    def __init__(self, kg: Neo4jGraph, kg_db_name: str):
        self.kg = kg
        self.kg_db_name = kg_db_name

    def run(self, query):
        return self.kg.query(query)

    def has_community_id(self, property_name: str) -> bool:
        check_query = f"""
        MATCH (n)
        WHERE n.{property_name} IS NOT NULL
        RETURN count(n) > 0 AS hasCommunityId
        """
        result = self.kg.query(check_query)
        return result and isinstance(result, list) and result[0].get("hasCommunityId", False)

    def graph_already_projected(self, graph_name: str) -> bool:
        cypher = """
        CALL gds.graph.list()
        """
        graphs = self.kg.query(query=cypher)
        return any(graph_name == graph.get("graphName") for graph in graphs)

    def run_leiden_on_graph(self, graph_name: str, property_name: str):
        if not self.has_community_id(property_name):
            print(f"\n▶ Running Leiden on {graph_name}, writing {property_name}...")
            self.run(f"""
            CALL gds.alpha.leiden.write('{graph_name}', {{writeProperty: '{property_name}'}})
            """)
        else:
            print(f"\n  Skipping Leiden on {graph_name}: {property_name} already exists.")

    def create_community_nodes_and_edges(self, level: str, prev_level: str):
        print(f"\n▶ Creating community nodes and edges for level {level}")
        self.run(f"""
        MATCH (n:{prev_level}_CommunityNode)
        WHERE n.{level}_CommunityId IS NOT NULL
        WITH DISTINCT n.{level}_CommunityId AS id
        MERGE (: {level}_CommunityNode {{id: id}})
        """)

        self.run(f"""
        MATCH (a:{prev_level}_CommunityNode)-[:{prev_level}_AGG_LINK]->(b:{prev_level}_CommunityNode)
        WHERE a.{level}_CommunityId IS NOT NULL AND b.{level}_CommunityId IS NOT NULL AND a.{level}_CommunityId <> b.{level}_CommunityId
        WITH a.{level}_CommunityId AS src, b.{level}_CommunityId AS tgt, count(*) AS weight
        MERGE (c1:{level}_CommunityNode {{id: src}})
        MERGE (c2:{level}_CommunityNode {{id: tgt}})
        MERGE (c1)-[r:{level}_AGG_LINK]->(c2)
        SET r.weight = weight
        """)

    def project_graph(self, graph_name: str, node_label: str, rel_type: str):
        if not self.graph_already_projected(graph_name=graph_name):
          print(f"\n▶ Creating projection from graph name: {graph_name}")
          self.run(f"""
            CALL gds.graph.project.cypher(
            '{graph_name}',
            'MATCH (n:{node_label}) RETURN id(n) AS id',
            'MATCH (n:{node_label})-[r:{rel_type}]->(m:{node_label}) RETURN id(n) AS source, id(m) AS target, r.weight AS weight'
            )
            """)
        else:
            print(f"\n▶ Graph '{graph_name}' already projected.")

    def detect_hierarchical_communities(self):
        base_projection_name = f"{self.kg_db_name}_projection"

        # C3 LEVEL
        if not self.graph_already_projected(base_projection_name):
            print("\n▶ Creating base projection from KG...")
            self.run(f"""
            CALL gds.graph.project(
              '{base_projection_name}',
              '*', '*'
            )
            """)
        else:
            print(f"\n▶ Base graph '{base_projection_name}' already projected.")

        self.run_leiden_on_graph(base_projection_name, "C3_CommunityId")

        # C2 LEVEL
        self.run("""
        MATCH (n)
        WHERE n.C3_CommunityId IS NOT NULL
        WITH DISTINCT n.C3_CommunityId AS id
        MERGE (:C3_CommunityNode {id: id})
        """)

        self.run("""
        MATCH (a)-[:RELATED_TO]->(b)
        WHERE a.C3_CommunityId IS NOT NULL AND b.C3_CommunityId IS NOT NULL AND a.C3_CommunityId <> b.C3_CommunityId
        WITH a.C3_CommunityId AS src, b.C3_CommunityId AS tgt, count(*) AS weight
        MERGE (c1:C3_CommunityNode {id: src})
        MERGE (c2:C3_CommunityNode {id: tgt})
        MERGE (c1)-[r:C3_AGG_LINK]->(c2)
        SET r.weight = weight
        """)
        self.project_graph("C3_graph", "C3_CommunityNode", "C3_AGG_LINK")
        self.run_leiden_on_graph("C3_graph", "C2_CommunityId")


        # C1 LEVEL
        self.create_community_nodes_and_edges("C2", "C3")
        self.project_graph("C2_graph", "C2_CommunityNode", "C2_AGG_LINK")
        self.run_leiden_on_graph("C2_graph", "C1_CommunityId")

        # C0 LEVEL
        self.create_community_nodes_and_edges("C1", "C2")
        self.project_graph("C1_graph", "C1_CommunityNode", "C1_AGG_LINK")
        self.run_leiden_on_graph("C1_graph", "C0_CommunityId")


        # Final GRAPH
        self.create_community_nodes_and_edges("C0", "C1")
        self.project_graph("C0_graph", "C0_CommunityNode", "C0_AGG_LINK")

        print("\n✅ Full C3 → C0 community hierarchy generated.")


    def build_community_hierarchy_flexible(self) -> List[Dict]:
        """
        Dynamically builds the community hierarchy from the available levels in the graph.
        Always starts from C3_CommunityNode and builds up if mappings (C2, C1, C0) exist.
        """

        print("🔍 Checking available community levels...")

        def level_exists(label: str, property: str) -> bool:
            query = f"""
            MATCH (n:{label})
            WHERE n.{property} IS NOT NULL
            RETURN count(n) > 0 AS exists
            """
            result = self.kg.query(query)
            return result and result[0].get("exists", False)

        # Level checks
        has_C2 = level_exists("C3_CommunityNode", "C2_CommunityId")
        has_C1 = level_exists("C2_CommunityNode", "C1_CommunityId")
        has_C0 = level_exists("C1_CommunityNode", "C0_CommunityId")

        print(f"✅ C2 Level: {'Yes' if has_C2 else 'No'}")
        print(f"✅ C1 Level: {'Yes' if has_C1 else 'No'}")
        print(f"✅ C0 Level: {'Yes' if has_C0 else 'No'}")

        # Start from C3 → C2
        C3_to_C2 = self.kg.query("""
            MATCH (n:C3_CommunityNode)
            RETURN n.id AS C3, n.C2_CommunityId AS C2
        """) if has_C2 else self.kg.query("""
            MATCH (n:C3_CommunityNode)
            RETURN n.id AS C3
        """)

        if not C3_to_C2:
            raise ValueError("❌ No C3_CommunityNode found — cannot build hierarchy.")

        # Organize C3 under C2 (or as roots if no C2)
        if has_C2:
            c2_to_c3s = defaultdict(list)
            for row in C3_to_C2:
                c2_to_c3s[row["C2"]].append(row["C3"])
        else:
            return [{"C3_CommunityId": row["C3"]} for row in C3_to_C2]

        # Organize C2 under C1 if available
        if has_C1:
            C2_to_C1 = self.kg.query("""
                MATCH (n:C2_CommunityNode)
                RETURN n.id AS C2, n.C1_CommunityId AS C1
            """)
            c1_to_c2s = defaultdict(list)
            for row in C2_to_C1:
                c1_to_c2s[row["C1"]].append({
                    "C2_CommunityId": row["C2"],
                    "children": c2_to_c3s[row["C2"]]
                })
        else:
            return [
                {"C2_CommunityId": c2_id, "children": c3_ids}
                for c2_id, c3_ids in c2_to_c3s.items()
            ]

        # Organize C1 under C0 if available
        if has_C0:
            C1_to_C0 = self.kg.query("""
                MATCH (n:C1_CommunityNode)
                RETURN n.id AS C1, n.C0_CommunityId AS C0
            """)
            c0_to_c1s = defaultdict(list)
            for row in C1_to_C0:
                c0_to_c1s[row["C0"]].append({
                    "C1_CommunityId": row["C1"],
                    "children": c1_to_c2s[row["C1"]]
                })
            return [
                {"C0_CommunityId": c0_id, "children": c1_nodes}
                for c0_id, c1_nodes in c0_to_c1s.items()
            ]
        else:
            return [
                {"C1_CommunityId": c1_id, "children": c1_to_c2s[c1_id]}
                for c1_id in c1_to_c2s
            ]


# Usage example:
# kg = Neo4jGraph(url=NEO4J_URI, username=NEO4J_USERNAME, password=NEO4J_PASSWORD, database="t20")
# detector = HierarchicalCommunityDetector(kg=kg, kg_db_name="t20")
# detector.detect_hierarchical_communities()
