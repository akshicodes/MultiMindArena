from .database import db

async def create_indexes():

    # Sessions Collection
    await db.sessions.create_index(
        "session_id",
        unique=True
    )

    await db.sessions.create_index(
        "started_at",
        expireAfterSeconds=604800
    )

    # Messages Collection

    await db.messages.create_index(
        "message_id",
        unique=True
    )

    await db.messages.create_index(
        "session_id"
    )

    await db.messages.create_index(
        "timestamp"
    )

    await db.messages.create_index(
        [
            ("session_id", 1),
            ("timestamp", 1)
        ]
    )

    print("Indexes created successfully")

    # Analytics Collection

    await db.analytics.create_index(
    "session_id",
    unique=True
)
    
    # Topics Collection

    await db.topics.create_index(
    "topic"
)
    
    # LLM Configs

    await db.llm_configs.create_index(
    "provider"
)

    await db.llm_configs.create_index(
    "model_name"
)