from src.rag_pipeline import RAGPipeline

def main(config):
    pipeline = RAGPipeline(config=config)
    pipeline.initialize()

    print("Type your question or 'exit()' to quit.")

    while True:
        question = input("Question: ")
        if question.strip() == "exit()":
            print("Exiting.")
            break
        
        vector_answer = pipeline.vector_rag.invoke({"question": question})["answer"]
        graph_answer = pipeline.graph_rag.invoke({"question": question})["answer"]

        print("\n\n\n")
        print("====================== Vector RAG ======================")
        print(vector_answer)

        print("\n\n\n")

        print("====================== Grapb RAG ======================")
        print(graph_answer)
        print("\n\n\n")

if __name__ == "__main__":

    # t20documentsgraph
    # t20_config_load = {
    #     "mode": "load",
    #     "kg_db_name": "t20documentsgraph"
    # }

    # t20_improved
    # t20_improved_load = {
    #     "mode": "load",
    #     "kg_db_name": "t20improved",
    # }


    # t60_improved
    # t60_improved_load = {
    #     "mode": "load",
    #     "kg_db_name": "t60improved",
    # }

    # t20fulltext_load = {
    #     "mode": "load",
    #     "kg_db_name": "t20fulltext",
    # }
    
    t20_load = {
        "mode": "load",
        "kg_db_name": "t20",
        "summary_dir":"/Users/danielguarnizo/workspace/Master/LLMs/GraphRAG/data/community_summaries/t20/C3",
    }



    main(t20_load)