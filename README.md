***

# Graph-Based Retrieval-Augmented Generation (GraphRAG) for Query-Focused Summarization

**A Vertical Review and Replication Study**

**Authors:** Veronica Di Gennaro & Daniel Yezid Guarnizo Orjuela  
**Institution:** Politecnico di Milano  
**Date:** May 2025

---

## 📖 Overview

This repository contains the implementation of a **Graph Retrieval-Augmented Generation (GraphRAG)** system, designed to replicate and adapt the approach proposed by Microsoft Research in *"From Local to Global: A GraphRAG Approach to Query-Focused Summarization"*.

While traditional RAG systems rely on vector similarity, they often struggle with "global sensemaking" tasks—queries that require synthesizing information across an entire dataset rather than retrieving a specific fact. This project implements a pipeline that constructs a hierarchical Knowledge Graph (KG) from scientific papers (ArXiv), performs community detection, and generates hierarchical summaries to answer complex, query-focused questions.

### Key Objectives
1.  **Replication:** Implement the GraphRAG pipeline (Indexing, Graph Construction, Community Detection, Global Search).
2.  **Adaptation:** Tailor the system to process scientific summaries from ArXiv rather than general news/podcasts, optimizing for cost and token usage using `o4-mini`.
3.  **Evaluation:** Compare the performance of GraphRAG vs. traditional Vector RAG using an "LLM-as-a-judge" methodology.

---

## 🏗️ Architecture

The system implements a dual-pipeline approach to compare methodologies:

1.  **Vector RAG Pipeline:**
    *   **Storage:** Milvus Vector Database.
    *   **Retrieval:** Semantic similarity search via embeddings.
    *   **Generation:** Standard context-stuffing into the LLM.

2.  **GraphRAG Pipeline:**
    *   **Extraction:** Uses `LLMGraphTransformer` to extract entities and relationships from text chunks.
    *   **Storage:** Neo4j Graph Database.
    *   **Community Detection:** Applies the **Leiden/Louvain algorithm** to detect hierarchical communities (Leaf C3 $\to$ Higher C2 $\to$ ...).
    *   **Summarization:** Generates community-specific summaries bottom-up.
    *   **Global Search:** Uses a Map-Reduce approach to synthesize answers from community summaries.

---

## 📂 Project Structure

```text
.
├── data/                       # Stores local data, graph pickles, and summaries
├── src/
│   ├── main.py                 # Entry point for the application
│   ├── rag_pipeline.py         # Orchestrator for Vector and Graph pipelines
│   ├── vector_rag.py           # Implementation of baseline Vector RAG
│   ├── graph_rag.py            # Implementation of Graph RAG
│   ├── graph_documents.py      # Document fetching, splitting, and graph conversion
│   ├── hierarchical_community_detector.py  # Neo4j community detection logic
│   ├── leaf_level_community_summaries.py   # Summarization for C3 (leaf) nodes
│   ├── higher_level_community_summaries.py # Recursive summarization for C2+ nodes
│   ├── global_query_answerer.py            # Map-Reduce logic for global QA
│   ├── global_question_generator.py        # Generates evaluation questions
│   ├── sensemaking_evaluator.py            # LLM-as-a-judge evaluation script
│   ├── abstract_rag_system.py  # Base class for RAG systems
│   └── utils/                  # Utilities for Config, Neo4j, Milvus, and ArXiv
└── README.md
```

---

## ⚙️ Prerequisites & Installation

### 1. Environment Setup
Ensure you have Python 3.9+ installed.

```bash
git clone <your-repo-url>
cd <your-repo-name>
pip install -r requirements.txt
```

### 2. External Services
You need access to the following services (local or cloud):
*   **Neo4j:** For the Knowledge Graph.
*   **Milvus:** For the Vector Store.
*   **OpenAI API:** For embeddings and LLM generation (`gpt-4o` / `o4-mini`).

### 3. Configuration
Create a `.env` file in the root directory:

```env
OPENAI_API_KEY=sk-...
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j
```

---

## 🚀 Usage

The system is controlled via `src/main.py`. You can configure the pipeline parameters in the `config` dictionary within the script.

### Running the Pipeline
To start the interactive Question-Answering loop:

```bash
python -m src.main
```

### Configuration Modes (`src/main.py`)
You can toggle between **Creating** a new graph or **Loading** an existing one by modifying the config dict:

**1. Create Mode (Ingest Data & Build Graph):**
```python
config = {
    "mode": "create",
    "kg_db_name": "my_research_graph",
    "arxiv_query": "agent large language model", # Topic to fetch
    "max_results": 20,
    "allowed_nodes": ["Concept", "Model", "Metric"], # Graph Schema
    "allowed_relationships": ["RELATED_TO", "COMPARES_WITH"],
    "summary_dir": "./data/community_summaries/..."
    # ...
}
```

**2. Load Mode (Query Existing Graph):**
```python
config = {
    "mode": "load",
    "kg_db_name": "my_research_graph",
    "summary_dir": "./data/community_summaries/my_research_graph/C3"
}
```

---

## 📊 Evaluation Methodology

We implemented an **LLM-as-a-Judge** evaluator (`src/sensemaking_evaluator.py`) to blindly compare answers from Vector RAG and Graph RAG based on four criteria:

1.  **Comprehensiveness:** Does it cover all aspects?
2.  **Diversity:** Does it provide varied perspectives?
3.  **Empowerment:** Does it help the reader make informed judgments?
4.  **Directness:** Is the answer concise and specific?

To generate evaluation questions without bias, we used the `GlobalQuestionGenerator` to create personas (e.g., "AI Researcher") and tasks based on the corpus description.

### Summary of Results
*   **GraphRAG** consistently outperformed Vector RAG in **Comprehensiveness**, **Diversity**, and **Empowerment**, particularly for queries requiring high-level understanding of the entire corpus (e.g., "Compare coordination architectures across all papers").
*   **Vector RAG** occasionally performed better on **Directness** or when the query utilized specific terminology not captured well by the graph schema.

*(Detailed results and tables can be found in the project report PDF).*

---

## 🛠️ Technologies Used

*   **LangChain & LangGraph:** Orchestration and state management.
*   **Neo4j & Graph Data Science (GDS):** Graph storage and Leiden/Louvain community detection.
*   **Milvus:** Vector database for baseline comparison.
*   **OpenAI:** `o4-mini-2025-04-16` for cost-effective processing and `gpt-4o` for evaluation.
*   **ArXiv API:** Data source.

---

## 📄 License
This project is developed for academic purposes at Politecnico di Milano.

---

*For a detailed theoretical explanation, please refer to the accompanying PDF report.*