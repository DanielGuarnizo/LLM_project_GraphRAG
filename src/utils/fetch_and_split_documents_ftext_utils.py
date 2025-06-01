import arxiv
import pymupdf  # PyMuPDF
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import tempfile
import requests


def download_pdf(url, save_path):
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    if not os.path.exists(save_path):
        response = requests.get(url)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
        return False
    return True


def extract_text_from_pdf(pdf_path):
    text = ""
    with pymupdf.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text


def fetch_and_split_documents_fulltext(
        search_query: str, 
        folder_name:str,
        max_results: int = 20
):
    client = arxiv.Client()
    search = arxiv.Search(
        query=search_query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
    )
    results = client.results(search)

    docs = []
    temp_dir = tempfile.mkdtemp()

    for result in results:
        pdf_url = result.pdf_url
        title = result.title
        summary = result.summary
        url = result.entry_id

        # Download and extract text
        pdf_path = f"./data/documents/{folder_name}/{title[:50].replace(' ', '_')}.pdf"
        if download_pdf(pdf_url, pdf_path):
            try:
                full_text = extract_text_from_pdf(pdf_path)
            except Exception as e:
                print(f"[!] Failed to parse PDF: {title}")
                full_text = summary  # fallback
        else:
            print(f"[!] Failed to download PDF: {title}")
            full_text = summary  # fallback

        docs.append({
            "title": title,
            "summary": summary,
            "url": url,
            "text_content": full_text
        })

    # Split full texts
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=1000, chunk_overlap=200
    )
    doc_splits = text_splitter.create_documents(
        [doc["text_content"] for doc in docs],
        metadatas=docs
    )

    print(f" Number of papers: {len(docs)}")
    print(f" Number of chunks: {len(doc_splits)}")
    return doc_splits