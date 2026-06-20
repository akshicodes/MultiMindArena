import asyncio

from backend.llm_clients.openrouter_client import OpenRouterClient
from backend.config import settings


async def main():

    client = OpenRouterClient(
        api_key=settings.openrouter_api_key
    )

    response = await client.generate(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "user",
                "content": "Introduce yourself in one sentence."
            }
        ]
    )

    print("\nResponse:")
    print(response)


if __name__ == "__main__":
    asyncio.run(main())