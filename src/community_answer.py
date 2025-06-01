import os
import json
import uuid
import random
import tiktoken
import openai
from typing import List

openai.api_key = os.getenv("OPENAI_API_KEY")

# Set your model and context size
MODEL = "o4-mini-2025-04-16"
MAX_TOKENS = 200_000
CHUNK_SIZE = 1000  # adjustable

# Tokenizer for approximate chunking
tokenizer = tiktoken.encoding_for_model(MODEL)

def count_tokens(text: str) -> int:
    return len(tokenizer.encode(text))

### STEP 1: GENERATE C2-LEVEL SUMMARIES FROM C3 SUMMARIES ###
def generate_higher_level_summary(c3_summaries: List[dict]) -> dict:
    input_blocks = []
    for i, c3 in enumerate(c3_summaries):
        block = f"""
        Community {i + 1}:
        Title: {c3['title']}
        Summary: {c3['summary']}
        Findings:
        """
        for f in c3.get("findings", []):
            block += f"- {f['summary']}: {f['explanation']}\n"
        input_blocks.append(block)

    full_input = "\n".join(input_blocks)

    prompt = f"""
    You are an AI assistant helping summarize a group of previously summarized communities.

    Write a comprehensive summary that captures key entities, relationships, and risks from a group of community summaries. 
    These communities are related and form a higher-level group. Your summary should extract and synthesize the major themes, 
    notable actors, and potential impact across the sub-communities. Output in JSON:
    {{
    "title": ...,
    "summary": ...,
    "rating": ...,
    "rating explanation": ...,
    "findings": [{{"summary": ..., "explanation": ...}}, ...]
    }}

    Input summaries:
    {full_input}
    """

    response = openai.ChatCompletion.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    return json.loads(response["choices"][0]["message"]["content"])

### STEP 2: SAVE SUMMARIES BY LEVEL ###
def save_summary(summary: dict, level: str, community_id: str):
    os.makedirs(f"summaries/{level}", exist_ok=True)
    with open(f"summaries/{level}/{community_id}.json", "w") as f:
        json.dump(summary, f, indent=2)

### STEP 3: CHUNK SUMMARIES FOR MAP STEP ###
def chunk_summary(summary: dict, chunk_size=CHUNK_SIZE) -> List[dict]:
    text = summary["summary"] + "\n\n" + "\n".join(
        f"- {f['summary']}\n{f['explanation']}" for f in summary.get("findings", [])
    )
    tokens = tokenizer.encode(text)
    chunks = [tokens[i:i + chunk_size] for i in range(0, len(tokens), chunk_size)]
    return [
        {
            "chunk_id": str(uuid.uuid4()),
            "community_id": summary.get("id", "unknown"),
            "text": tokenizer.decode(chunk)
        } for chunk in chunks
    ]

### STEP 4: MAP STEP (ANSWER + SCORE) ###
def map_chunk(chunk: dict, query: str) -> dict:
    prompt = f"""
    User Question:
    {query}

    Community Summary Chunk:
    {chunk['text']}

    Instructions:
    - Write a partial answer to the user query based on this chunk.
    - Rate how helpful this chunk is for answering the query (0–100).

    Respond in this JSON format:
    {{"answer": "...", "score": float}}
    """
    response = openai.ChatCompletion.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    content = json.loads(response["choices"][0]["message"]["content"])
    return {
        "chunk_id": chunk["chunk_id"],
        "community_id": chunk["community_id"],
        "answer": content["answer"],
        "score": content["score"]
    }

### STEP 5: REDUCE STEP ###
def reduce_answers(partial_answers: List[dict], query: str) -> str:
    top_answers = sorted([a for a in partial_answers if a["score"] > 0], key=lambda x: -x["score"])
    context = "\n\n".join(a["answer"] for a in top_answers)
    prompt = f"""
    User Question:
    {query}

    Helpful Partial Answers:
    {context}

    Instructions:
    Use the above information to write a comprehensive, final answer.
    """
    response = openai.ChatCompletion.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return response["choices"][0]["message"]["content"]
