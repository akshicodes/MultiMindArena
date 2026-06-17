from openai import AsyncOpenAI
from ..config import settings
from .base import BaseLLMClient


class OpenRouterClient(BaseLLMClient):

    def __init__(self, api_key: str):

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1"
        )

    async def generate(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.8,
        max_tokens: int = 300
    ) -> str:

        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return response.choices[0].message.content