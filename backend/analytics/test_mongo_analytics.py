import asyncio

from backend.analytics.aggregator import (
    generate_session_analytics
)

SESSION_ID = "3a2e7b82-bbe4-4e12-b7c8-6039dd749f5b"


async def main():

    result = await generate_session_analytics(
        SESSION_ID
    )

    print(result)


asyncio.run(main())