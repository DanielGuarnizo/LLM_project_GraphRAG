import os
import json
from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

class GlobalQuestionGenerator:
    def __init__(
        self, 
        model: str,
        output_path: str
    ):
        self.llm = ChatOpenAI(model_name=model)
        self.output_path = output_path

    def generate_personas(self, corpus_description: str, k: int) -> List[str]:

        system_prompt = "You are an expert in user modeling and evaluation design."
    
        human_prompt = f"""
        Given the following corpus description, generate {k} distinct personas who would be interested in using a system built on this corpus. Each persona should:
        - Reflect a realistic professional or academic role (e.g., "AI Research Scientist", "Policy Analyst").
        - Have a clear information need or goal related to this corpus (e.g., designing agent systems, auditing safety).
        - Be relevant to the research themes (LLMs, agents, prompt engineering, etc.).

        Corpus:
        {corpus_description}
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        response = self.llm.invoke(messages)
        return self.parse_list(response.content)[:k]  # ensure only k personas

    def generate_tasks(self, persona: str, n: int) -> List[str]:

        system_prompt = "You are helping design task evaluations for a knowledge-based system."

        human_prompt = f"""
        Given the following user persona, list {n} specific tasks this user would want to perform using insights from the corpus. Focus on meaningful goals, such as reviewing strategies, comparing approaches, or assessing risks.

        Persona:
        {persona}
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        response = self.llm.invoke(messages)
        return self.parse_list(response.content)[:n]  # ensure only n tasks

    def generate_questions(self, persona: str, task: str, m: int) -> List[str]:

        system_prompt = "You are generating high-level evaluation questions for global sensemaking over an AI research corpus."

        human_prompt = f"""
        For the given user and task, write {m} questions that require broad understanding of the entire corpus. These questions should:
        - Encourage synthesis and comparison across multiple documents.
        - Avoid requiring retrieval of specific facts from one paper.
        - Explore overarching patterns, strategies, implications, or comparisons.

        Persona:
        {persona}

        Task:
        {task}
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        response = self.llm.invoke(messages)
        return self.parse_list(response.content)[:m]  # ensure only m questions

    def parse_list(self, text: str) -> List[str]:
        """
        Parses a numbered or bulleted list returned by the LLM.
        """
        lines = text.strip().split("\n")
        return [line.strip(" -0123456789.").strip() for line in lines if line.strip()]

    def save_questions(self, questions):
        os.makedirs(self.output_path, exist_ok=True)
        questions_file = os.path.join(self.output_path, "global_sensemaking_questions.json")
        with open(questions_file, "w") as f:
            json.dump(questions, f, indent=2)

        print(f"✅ Saved {len(questions)} persona-task blocks to {questions_file}")

    def run(self, corpus_description: str, k: int, n: int, m: int) -> List[Dict]:
        personas = self.generate_personas(corpus_description, k)
        results = []
        total_steps = k * n * m
        current_step = 0

        print(f"🚀 Starting global question generation...")
        print(f"📦 Target: {k} personas × {n} tasks × {m} questions = {total_steps} total questions")

        for i, persona in enumerate(personas):
            print(f"\n👤 Generating tasks for Persona {i+1}/{k}...")
            tasks = self.generate_tasks(persona, n)

            for j, task in enumerate(tasks):
                print(f"   📌 Generating {m} questions for Task {j+1}/{n}...")
                questions = self.generate_questions(persona, task, m)
                current_step += len(questions)
                print(f"     ✅ Progress: {current_step}/{total_steps} questions generated")

                results.append({
                    "persona": persona,
                    "task": task,
                    "questions": questions
                })

        print("\n💾 Saving generated questions...")
        self.save_questions(questions=results)
        print("✅ All questions saved successfully.")
        return results