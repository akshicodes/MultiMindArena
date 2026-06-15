import asyncio

from database import db
from indexes import create_indexes
from ..data.topics import TOPICS



async def seed_topics():

    existing_topics = await db.topics.count_documents({})

    print(f"Current topic count: {existing_topics}")

    if existing_topics >= 60:
        print("Topics already seeded.")
        return

    await db.topics.insert_many(TOPICS)

    new_count = await db.topics.count_documents({})

    print(f"New topic count: {new_count}")

    print(f"{len(TOPICS)} topics inserted.")


async def main():

    await create_indexes()
    await seed_topics()

    print("Database setup complete.")


if __name__ == "__main__":
    asyncio.run(main())