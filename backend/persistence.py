from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi.encoders import jsonable_encoder

from backend.database import db

from .participants import ParticipantProfile
from .state import SessionState
from backend.analytics.sentiment import calculate_sentiment


async def ensure_session_record(state: SessionState, participants: list[ParticipantProfile]) -> None:
    existing = await db.sessions.find_one({"session_id": state.session_id})
    if existing is not None:
        return

    await db.sessions.insert_one(
        {
            "session_id": state.session_id,
            "topic": state.topic,
            "topic_attributed_to": state.topic_attributed_to,
            "started_at": state.created_at,
            "ended_at": None,
            "participants": [participant.name for participant in participants],
            "status": "active",
            "total_messages": 0,
            "persona_map": {participant.name: participant.persona for participant in participants},
        }
    )


async def persist_message(
    state: SessionState,
    speaker: str,
    content: str,
    api_latency_ms: int,
    msg_type: str,
    *,
    turn_index: int | None = None,
    tags: list[str] | None = None,
    addressed_to: str | None = None,
    sentiment: float = 0.0,
) -> dict[str, Any]:
    message_tags = tags or ["debate", "live"]

    sentiment = calculate_sentiment(content)
    print("SENTIMENT DEBUG:", sentiment)
    document: dict[str, Any] = {
        "message_id": str(uuid4()),
        "session_id": state.session_id,
        "sender": speaker,
        "content": content,
        "timestamp": datetime.utcnow(),
        "turn_index": turn_index if turn_index is not None else state.turn_index,
        "msg_type": msg_type,
        "sentiment": sentiment,
        "tags": message_tags,
        "addressed_to": addressed_to,
        "word_count": len(content.split()),
        "tokens_used": max(len(content.split()), 1),
        "api_latency_ms": api_latency_ms,
    }

    await db.messages.insert_one(jsonable_encoder(document))
    await db.sessions.update_one(
        {"session_id": state.session_id},
        {"$inc": {"total_messages": 1}, "$set": {"status": "active"}},
    )
    return document


async def persist_topic(state: SessionState) -> dict[str, Any]:
    topic_message = {
        "message_id": str(uuid4()),
        "session_id": state.session_id,
        "sender": state.topic_attributed_to,
        "content": state.topic,
        "timestamp": state.created_at,
        "turn_index": 0,
        "msg_type": "system",
        "sentiment": 0.0,
        "tags": ["topic", "seed"],
        "addressed_to": None,
        "word_count": len(state.topic.split()),
        "tokens_used": max(len(state.topic.split()), 1),
        "api_latency_ms": 0,
    }

    await db.messages.insert_one(jsonable_encoder(topic_message))
    await db.sessions.update_one(
        {"session_id": state.session_id},
        {"$inc": {"total_messages": 1}, "$set": {"status": "active"}},
    )
    return topic_message