# import os
# import json
# from typing import List, Dict, Optional
# from langchain_openai import ChatOpenAI
# from src.rag_pipeline import RAGPipeline
# from langchain.schema import HumanMessage, SystemMessage


# class SensemakingEvaluator:
#     def __init__(
#         self,
#         question_path: str,
#         output_path: str,
#         rag_pipeline: RAGPipeline,  
#         eval_model: str,
#         criteria: Optional[List[str]] = None
#     ):
#         self.question_path = question_path
#         self.output_path = output_path
#         self.pipeline = rag_pipeline
#         self.llm = ChatOpenAI(model_name=eval_model)
#         self.criteria = criteria or ["comprehensiveness", "diversity", "empowerment"]

#     def load_questions(self) -> List[Dict]:
#         with open(self.question_path, "r") as f:
#             return json.load(f)

#     def generate_answers(self, question: str) -> Dict[str, str]:
#         return {
#             "1": self.pipeline.vector_rag.invoke({"question": question})["answer"],
#             "2": self.pipeline.graph_rag.invoke({"question": question})["answer"]
#         }

#     def judge_pairwise_answer(self, query: str, answer_1: str, answer_2: str) -> str:
        
#         CRITERIA = { 
#         "comprehensiveness": "How much detail does the answer provide to cover all the aspects and details of the question? A comprehensive answer should be thorough and complete, without being redundant or irrelevant. For example, if the question is ’What are the benefits and drawbacks of nuclear energy?’, a comprehensive answer would provide both the positive and negative aspects of nuclear energy, such as its efficiency, environmental impact, safety, cost, etc. A comprehensive answer should not leave out any important points or provide irrelevant information. For example, an incomplete answer would only provide the benefits of nuclear energy without describing the drawbacks, or a redundant answer would repeat the same information multiple times.",
#         "diversity": "How varied and rich is the answer in providing different perspectives and insights on the question? A diverse answer should be multi-faceted and multi-dimensional, offering different viewpoints and angles on the question. For example, if the question is ’What are the causes and effects of climate change?’, a diverse answer would provide different causes and effects of climate change, such as greenhouse gas emissions, deforestation, natural disasters, biodiversity loss, etc. A diverse answer should also provide different sources and evidence to support the answer. For example, a single-source answer would only cite one source or evidence, or a biased answer would only provide one perspective or opinion.",
#         "directness": "How specifically and clearly does the answer address the question? A direct answer should provide a clear and concise answer to the question. For example, if the question is ’What is the capital of France?’, a direct answer would be ’Paris’. A direct answer should not provide any irrelevant or unnecessary information that does not answer the question. For example, an indirect answer would be ’The capital of France is located on the river Seine’.",
#         "empowerment": "How well does the answer help the reader understand and make informed judgements about the topic without being misled or making fallacious assumptions. Evaluate each answer on the quality of answer as it relates to clearly explaining and providing reasoning and sources behind the claims in the nswer."
#         }

        
#         system_prompt = f"""
#         ---Role---
#         You are a helpful assistant responsible for grading two answers to a question that are provided by two
#         different people.
#         ---Goal---
#         Given a question and two answers (Answer 1 and Answer 2), assess which answer is better according to
#         the following measure:
#         {CRITERIA}
#         Your assessment should include two parts:
#         - Winner: either 1 (if Answer 1 is better) and 2 (if Answer 2 is better) or 0 if they are fundamentally
#         similar and the differences are immaterial.
#         - Reasoning: a short explanation of why you chose the winner with respect to the measure described above.
#         Format your response as a JSON object with the following structure:
#         {{
#         "winner": <1, 2, or 0>,
#         "reasoning": "Answer 1 is better because <your reasoning>."
#         }}


#         """

#         human_prompt = f"""
#         ---Question---
#         {query}
#         ---Answer 1---
#         {answer_1}
#         ---Answer 2---
#         {answer_2}
#         Output:
#         """

#         messages = [
#             SystemMessage(content=system_prompt),
#             HumanMessage(content=human_prompt)
#         ]

#         try:
#             response = self.llm.invoke(messages)
#             return response.content if hasattr(response, "content") else str(response)
#         except Exception as e:
#             return f"⚠️ LLM evaluation error: {e}"

#     def evaluate(self):
#         os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
#         data = self.load_questions()

#         with open(self.output_path, "w") as out_file:
#             q_count = sum(len(d["questions"]) for d in data)
#             current_q = 0

#             for entry in data:
#                 persona = entry.get("persona", "Unknown")
#                 task = entry.get("task", "Unknown")
#                 for question in entry.get("questions", []):
#                     current_q += 1
#                     print(f"🔍 Evaluating Q{current_q}/{q_count}")

#                     try:
#                         answers = self.generate_answers(question)
#                     except Exception as e:
#                         print(f"❌ RAG error: {e}")
#                         continue

#                     judgment = self.judge_pairwise_answer(question, answers["1"], answers["2"])

#                     out_file.write("=" * 80 + "\n")
#                     out_file.write(f"Q{current_q}: {question}\n")
#                     out_file.write(f"Persona: {persona}\n")
#                     out_file.write(f"Task: {task}\n\n")
#                     out_file.write("Answer 1 (Vector RAG):\n")
#                     out_file.write(answers["1"] + "\n\n")
#                     out_file.write("Answer 2 (Graph RAG):\n")
#                     out_file.write(answers["2"] + "\n\n")
#                     out_file.write("🧠 Judgment:\n")
#                     out_file.write(judgment + "\n\n")
#                     out_file.flush()

#         print(f"\n✅ All evaluations saved to {self.output_path}")

import os
import json
from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from src.rag_pipeline import RAGPipeline


class SensemakingEvaluator:
    def __init__(
        self,
        question_path: str,
        output_path: str,
        rag_pipeline: RAGPipeline,
        eval_model: str,
        criteria: Optional[List[str]] = None
    ):
        self.question_path = question_path
        self.output_path = output_path
        self.pipeline = rag_pipeline
        self.llm = ChatOpenAI(model_name=eval_model)
        self.criteria = criteria or ["comprehensiveness", "diversity", "empowerment"]

    def load_questions(self) -> List[Dict]:
        with open(self.question_path, "r") as f:
            return json.load(f)

    def generate_answers(self, question: str) -> Dict[str, str]:
        return {
            "1": self.pipeline.vector_rag.invoke({"question": question})["answer"],
            "2": self.pipeline.graph_rag.invoke({"question": question})["answer"]
        }

    def judge_pairwise_answer(self, query: str, answer_1: str, answer_2: str) -> str:
        CRITERIA = {
            "comprehensiveness": "How much detail does the answer provide to cover all aspects of the question?",
            "diversity": "How varied is the answer in perspectives and insights?",
            "empowerment": "How well does the answer help the reader make informed judgments?"
        }

        system_prompt = f"""
        ---Role---
        You are a helpful assistant responsible for grading two answers to a question from different RAG systems.

        ---Goal---
        Given a question and two answers (Answer 1 and Answer 2), assess which is better using these criteria:
        {json.dumps(CRITERIA, indent=2)}

        Your response should include:
        - "winner": either 1, 2, or 0 if both are equally good
        - "reasoning": a short justification

        Format:
        {{
        "winner": 1|2|0,
        "reasoning": "..."
        }}
                """

        human_prompt = f"""
        ### Question
        {query}

        ### Answer 1 (Vector RAG)
        {answer_1}

        ### Answer 2 (Graph RAG)
        {answer_2}

        Evaluate now:
        """

        messages = [
            SystemMessage(content=system_prompt.strip()),
            HumanMessage(content=human_prompt.strip())
        ]

        try:
            response = self.llm.invoke(messages)
            return response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            return f"⚠️ LLM evaluation error: {e}"

    def evaluate(self):
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        data = self.load_questions()
        q_count = sum(len(d["questions"]) for d in data)
        current_q = 0

        with open(self.output_path, "w") as out_file:
            out_file.write("# 🧠 Global Sensemaking Evaluation Report\n\n")

            for entry in data:
                persona = entry.get("persona", "Unknown Persona")
                task = entry.get("task", "Unknown Task")

                for question in entry.get("questions", []):
                    current_q += 1
                    print(f"🔍 Evaluating Q{current_q}/{q_count}")

                    try:
                        answers = self.generate_answers(question)
                    except Exception as e:
                        print(f"❌ RAG error: {e}")
                        continue

                    judgment = self.judge_pairwise_answer(question, answers["1"], answers["2"])

                    out_file.write(f"## ❓ Question {current_q}\n")
                    out_file.write(f"**Persona:** {persona}\n\n")
                    out_file.write(f"**Task:** {task}\n\n")
                    out_file.write(f"### 🗣 Question:\n{question}\n\n")
                    out_file.write(f"### 🧪 Answer 1 (Vector RAG)\n{answers['1']}\n\n")
                    out_file.write(f"### 🧪 Answer 2 (Graph RAG)\n{answers['2']}\n\n")
                    out_file.write(f"### 🧠 Judgment:\n```json\n{judgment}\n```\n\n")
                    out_file.write("---\n\n")
                    out_file.flush()

        print(f"\n✅ All evaluations saved to: {self.output_path}")