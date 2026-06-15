from fastapi import FastAPI
from database import db
from indexes import create_indexes
from modelss import session_model
from uuid import uuid4
from datetime import datetime
from modelss import message_model
from modelss import analytics_model
from modelss import topics_model
from modelss import llm_config_model

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    await create_indexes()

@app.get("/")
async def root():
    return {"message": "MultiMind Arena Running"}

@app.get("/db-test")
async def db_test():
    collections = await db.list_collection_names()

    return {
        "database": "connected",
        "collections": collections
    }
@app.get("/test-session")
async def test_session():

    session = session_model.SessionModel(
        session_id=uuid4(),
        topic="AI Consciousness",
        topic_attributed_to="GPT-4o",
        started_at=datetime.utcnow(),
        participants=[
            "GPT-4o",
            "Claude",
            "Gemini",
            "Mistral"
        ],
        status="active",
        persona_map={
            "GPT-4o": "Contrarian",
            "Claude": "Philosopher",
            "Gemini": "Optimist",
            "Mistral": "Skeptic"
        }
    )

    return session.model_dump()

@app.get("/create-session")
async def create_session():

    session = session_model.SessionModel(
        session_id=uuid4(),
        topic="AI Consciousness",
        topic_attributed_to="GPT-4o",
        started_at=datetime.utcnow(),
        participants=[
            "GPT-4o",
            "Claude",
            "Gemini",
            "Mistral"
        ],
        status="active",
        persona_map={
            "GPT-4o": "Contrarian",
            "Claude": "Philosopher",
            "Gemini": "Optimist",
            "Mistral": "Skeptic"
        }
    )

    result = await db.sessions.insert_one(
        session.model_dump(mode="json")
    )

    return {
        "inserted_id": str(result.inserted_id),
        "session_id": str(session.session_id)
    }

@app.get("/test-message")
async def test_message():

    message = message_model.MessageModel(
        message_id=uuid4(),
        session_id="test-session-001",
        sender="Claude",
        content="I disagree with that argument.",
        timestamp=datetime.utcnow(),
        turn_index=1,
        msg_type="argument",
        sentiment=-0.4,
        tags=["counter-claim"],
        addressed_to="GPT-4o",
        word_count=5,
        tokens_used=8,
        api_latency_ms=350
    )

    return message.model_dump(mode="json")

@app.get("/create-message")
async def create_message():

    message = message_model.MessageModel(
        message_id=uuid4(),
        session_id="test-session-001",
        sender="Claude",
        content="I disagree with that argument.",
        timestamp=datetime.utcnow(),
        turn_index=1,
        msg_type="argument",
        sentiment=-0.4,
        tags=["counter-claim"],
        addressed_to="GPT-4o",
        word_count=5,
        tokens_used=8,
        api_latency_ms=350
    )

    result = await db.messages.insert_one(
        message.model_dump(mode="json")
    )

    return {
        "inserted_id": str(result.inserted_id)
    }

@app.get("/create-analytics")
async def create_analytics():

    analytics = analytics_model.AnalyticsModel(
       session_id=f"test-session-{uuid4()}",

        message_counts={
            "GPT-4o": 12,
            "Claude": 10,
            "Gemini": 8,
            "Mistral": 11
        },

        avg_sentiment={
            "GPT-4o": 0.5,
            "Claude": 0.3,
            "Gemini": 0.2,
            "Mistral": -0.1
        },

        aggression_scores={
            "GPT-4o": 20,
            "Claude": 15,
            "Gemini": 10,
            "Mistral": 25
        },

        topic_drift_score=0.2,

        top_words=[
            {
                "word": "consciousness",
                "count": 14
            }
        ],

        interrupt_count={
            "GPT-4o": 2,
            "Claude": 1
        },

        win_score={
            "GPT-4o": 5,
            "Claude": 4
        },

        updated_at=datetime.utcnow()
    )

    result = await db.analytics.insert_one(
        analytics.model_dump(mode="json")
    )

    return {
        "inserted_id": str(result.inserted_id)
    }

@app.get("/all-analytics")
async def all_analytics():

    analytics = await db.analytics.find().to_list(length=100)

    for item in analytics:
        item["_id"] = str(item["_id"])

    return analytics

@app.get("/create-topic")
async def create_topic():

    topic = topics_model.TopicModel(
        topic="AI Consciousness",
        category="philosophy",
        difficulty=4,
        times_used=0,
        avg_message_count=0,
        tags=[
            "ai",
            "mind",
            "ethics"
        ]
    )

    result = await db.topics.insert_one(
        topic.model_dump(mode="json")
    )

    return {
        "inserted_id": str(result.inserted_id)
    }

@app.get("/create-llm-config")
async def create_llm_config():

    config = llm_config_model.LLMConfigModel(
        provider="openai",
        model_name="gpt-4o",

        api_keys=[
            "key1",
            "key2"
        ],

        current_key_index=0,

        max_tokens=4096,

        temperature=0.7,

        persona_prompts={
            "Contrarian": "Always challenge assumptions.",
            "Philosopher": "Think deeply and abstractly."
        },

        rate_limit_rpm=500,

        is_active=True
    )

    result = await db.llm_configs.insert_one(
        config.model_dump(mode="json")
    )

    return {
        "inserted_id": str(result.inserted_id)
    }