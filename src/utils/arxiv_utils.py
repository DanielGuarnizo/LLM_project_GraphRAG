import arxiv
from langchain.text_splitter import RecursiveCharacterTextSplitter

def fetch_and_split_documents(
    search_query: str,
    max_results: int = 20
):
    # Fetch papers from arXiv
    client = arxiv.Client()
    search = arxiv.Search(
        query=search_query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
    )
    results = client.results(search)

    # Collect document summaries
    docs = []
    for result in results:
        docs.append({
            "title": result.title,
            "summary": result.summary,
            "url": result.entry_id
        })

    # Split summaries into chunks
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=500, chunk_overlap=50
    )
    doc_splits = text_splitter.create_documents(
        [doc["summary"] for doc in docs], metadatas=docs
    )

    print(f"Number of papers: {len(docs)}")
    print(f"Number of chunks: {len(doc_splits)}")
    return doc_splits
