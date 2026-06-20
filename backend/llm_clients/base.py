from abc import ABC, abstractmethod

class BaseLLMClient(ABC):

    @abstractmethod
    async def generate(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.8,
        max_tokens: int = 300
    ) -> str:
        pass

    @abstractmethod
    async def generate_stream(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.8,
        max_tokens: int = 300
    ):
        pass