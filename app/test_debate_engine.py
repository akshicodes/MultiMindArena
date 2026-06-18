
import asyncio

from app.debate_engine import DebateEngine


async def main():

    engine = DebateEngine()

    await engine.run(
        topic="Should AI replace teachers?",
        rounds=3
    )


if __name__ == "__main__":
    asyncio.run(main())