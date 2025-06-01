from abc import ABC
from langchain_openai import ChatOpenAI

class AbstractRAGSystem(ABC):
    def __init__(
            self
        ):
        super().__init__()
        self.qa_llm = ChatOpenAI(
            model="gpt-4o",
            temperature=1
        )
