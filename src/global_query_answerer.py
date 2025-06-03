import os
import json
import random
from typing import List, Dict
from langchain_openai import ChatOpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain.schema import HumanMessage, SystemMessage

class GlobalQueryAnswerer:
    def __init__(
        self,
        summary_dir: str,  # e.g., /path/to/community_summaries/t20/C2
        model_name: str =  "o4-mini-2025-04-16",
        max_tokens: int = 8000
    ):
        self.llm = ChatOpenAI(model_name=model_name)
        self.max_tokens = max_tokens
        self.summary_dir = summary_dir

    def load_summaries(self) -> List[Dict]:
        summaries = []
        for fname in os.listdir(self.summary_dir):
            if fname.endswith(".json"):
                path = os.path.join(self.summary_dir, fname)
                with open(path) as f:
                    data = json.load(f)
                    content = data.get("summary", data)
                    if isinstance(content, dict):
                        text = content.get("summary", "")
                        findings = content.get("findings", [])
                        findings_text = "\n".join(f"- {f['summary']}" for f in findings)
                        doc = f"{text}\n\nKey Findings:\n{findings_text}"
                    else:
                        doc = str(content)

                    summaries.append({
                        "text": doc,
                        "tokens": data.get("tokens", len(doc.split())),
                        "id": data.get("community_id", fname.replace(".json", ""))
                    })
        return summaries

    def prepare_chunks(self, summaries: List[Dict], chunk_token_limit: int) -> List[str]:
        random.shuffle(summaries)
        chunks = []
        current_chunk = []
        current_tokens = 0

        for summary in summaries:
            if current_tokens + summary["tokens"] > chunk_token_limit:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [summary["text"]]
                current_tokens = summary["tokens"]
            else:
                current_chunk.append(summary["text"])
                current_tokens += summary["tokens"]

        return current_chunk 

    def map_answers(self, query: str, chunks: List[str]) -> List[Dict]:
        """
        Map step: generate partial answers and scores for each chunk in parallel.
        """
        partial_answers = []
        max_workers = len(chunks)

        def process_chunk(chunk: str) -> List[Dict]:
            
            system_prompt = """
            ---Role---
            You are a helpful assistant responding to questions about data in the chunk provided.
            ---Goal---
            Generate a response of the target format that responds to the user’s question, summarize
            all relevant information in the input chunk appropriate for the format, and
            incorporate any relevant general knowledge.
            If you don’t know the answer, just say so. Do not make anything up.
            The response shall preserve the original meaning and use of modal verbs such as "shall", "may" or "will".
            Points supported by data should list the relevant reports as references as follows:
            "This is an example sentence supported by data references [Data: Reports (report ids)]"
            Do not list more than 5 record ids in a single reference. Instead, list the top 5 most relevant record
            ids and add "+more" to indicate that there are more.
            For example:
            "Person X is the owner of Company Y and subject to many allegations of wrongdoing [Data: 7, 64, 46, 34, +more)]. He is also CEO of company X [Data: Reports (1, 3)]"
            Reports (2,
            where 1, 2, 3, 7, 34, 46, and 64 represent the id (not the index) of the relevant data report in the
            provided chunk.

            Do not include information where the supporting evidence for it is not provided.

            Respond with a partial answer to the query and a helpfulness score (0-100).
            """
            human_prompt = f"""
            ---Query--
            {query}
            ---Analyst Reports---
            {chunk}
            Output:
            """

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]

            try:
                result = self.llm.invoke(messages)
                content = result.content if hasattr(result, "content") else str(result)
                score = self.extract_score(content)
                if score > 0:
                    return {"score": score, "text": content}
            except Exception as e:
                print(f"❌ LLM error on chunk: {e}")
            return None

        # Adjust max_workers to control concurrency (e.g., 4, 8, or more)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_chunk, chunk) for chunk in chunks]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    partial_answers.append(result)

        return partial_answers
    
    def extract_score(self, text: str) -> int:
        # Expecting score in format: "Helpfulness Score: 75" or similar
        import re
        match = re.search(r"(\d{1,3})", text)
        if match:
            return min(int(match.group(1)), 100)
        return 0

    def reduce_to_final_answer(self, answers: List[Dict]) -> str:
        selected_texts = []
        total_tokens = 0
        for ans in answers:
            token_count = len(ans["text"].split())
            if total_tokens + token_count > self.max_tokens:
                break
            selected_texts.append(ans["text"])
            total_tokens += token_count

        final_input = "\n\n".join(selected_texts)

        system_prompt = """
        ---Role---
        You are a helpful assistant responding to questions about a dataset by synthesizing perspectives from
        multiple analysts.
        ---Goal---
        Generate a response of the target format that responds to the user’s question, summarize
        all the reports from multiple analysts who focused on different parts of the dataset, and incorporate any
        relevant general knowledge.
        Note that the analysts’ reports provided below are ranked in the **descending order of helpfulness**.
        If you don’t know the answer, just say so. Do not make anything up.
        The final response should remove all irrelevant information from the analysts’ reports and merge the
        cleaned information into a comprehensive answer that provides explanations of all the key points and
        implications appropriate for the response length and format.
        Add sections and commentary to the response as appropriate for the length and format. Style the response
        in markdown.
        The response shall preserve the original meaning and use of modal verbs such as "shall", "may" or "will".
        The response should also preserve all the data references previously included in the analysts’ reports,

        but do not mention the roles of multiple analysts in the analysis process.
        Do not list more than 5 record ids in a single reference. Instead, list the top 5 most relevant record
        ids and add "+more" to indicate that there are more.
        For example:
        "Person X is the owner of Company Y and subject to many allegations of wrongdoing [Data: 7, 34, 46, 64, +more)]. He is also CEO of company X [Data: Reports (1, 3)]"
        Reports (2,
        where 1, 2, 3, 7, 34, 46, and 64 represent the id (not the index) of the relevant data record.
        Do not include information where the supporting evidence for it is not provided.

        """
        human_prompt = f"""
        ---Analyst Reports---
        {final_input}
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        response = self.llm.invoke(messages)
        return response.content if hasattr(response, "content") else str(response)

    def answer_query(self, query: str, chunk_token_limit: int = 12000):
        summaries = self.load_summaries()
        chunks = self.prepare_chunks(summaries, chunk_token_limit)
        print(f"🧩 Prepared {len(chunks)} summary chunks.")
        partial_answers = self.map_answers(query, chunks)
        print(f"✅ Collected {len(partial_answers)} helpful answers.")
        final_answer = self.reduce_to_final_answer(partial_answers)
        return final_answer
