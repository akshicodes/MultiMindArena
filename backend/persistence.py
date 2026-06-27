from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi.encoders import jsonable_encoder

from backend.database import db

from .participants import ParticipantProfile
from .state import SessionState
from backend.analytics.sentiment import calculate_sentiment, analyze_contextual_tone


import re
from backend.llm_clients.openrouter_client import OpenRouterClient
from backend.config import settings


async def extract_topic_keywords(topic: str) -> list[str]:
    # Default fallback in case LLM call fails
    default_keywords = [w.strip(",.!?").lower() for w in topic.split() if len(w) > 4][:5]
    if not default_keywords:
        default_keywords = ["happiness", "measure", "scientific"]

    try:
        client = OpenRouterClient(api_key=settings.openrouter_api_key)
        prompt = f"Extract 5 single lowercase nouns/adjectives representing the core theme of the topic: '{topic}'."
        messages = [
            {
                "role": "system",
                "content": "You are a precise keyword extraction assistant. Respond ONLY with a comma-separated list of the 5 keywords, e.g. 'keyword1, keyword2, keyword3, keyword4, keyword5'. Do not output any preamble, markdown, or extra characters."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        response = await client.generate(
            model="google/gemini-2.5-flash",
            messages=messages,
            temperature=0.1,
            max_tokens=20
        )
        words = [w.strip().lower() for w in response.split(",")]
        clean_words = []
        for w in words:
            match = re.findall(r"\b[a-zA-Z0-9_-]+\b", w)
            if match:
                clean_words.extend(match)
        if clean_words:
            return clean_words[:7]
    except Exception as e:
        print(f"Error extracting topic keywords: {e}")
    
    return default_keywords


async def ensure_session_record(state: SessionState, participants: list[ParticipantProfile]) -> None:
    existing = await db.sessions.find_one({"session_id": state.session_id})
    if existing is not None:
        return

    keywords = await extract_topic_keywords(state.topic)

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
            "keywords": keywords,
        }
    )


async def persist_message(
    state: SessionState,
    speaker: str,
    content: str,
    api_latency_ms: int,
    msg_type: str,
    *,
    message_id: str | None = None,
    turn_index: int | None = None,
    tags: list[str] | None = None,
    addressed_to: str | None = None,
    sentiment: float = 0.0,
) -> dict[str, Any]:
    message_tags = tags or ["debate", "live"]

    vader_sentiment = calculate_sentiment(content)
    contextual_sentiment = vader_sentiment
    contextual_aggression = 0.0

    try:
        tone = await analyze_contextual_tone(content)
        if tone:
            contextual_sentiment = tone.get("sentiment", vader_sentiment)
            contextual_aggression = tone.get("aggression", 0.0)
    except Exception as e:
        print(f"Failed to calculate contextual tone: {e}")

    document: dict[str, Any] = {
        "message_id": message_id or str(uuid4()),
        "session_id": state.session_id,
        "sender": speaker,
        "content": content,
        "timestamp": datetime.utcnow(),
        "turn_index": turn_index if turn_index is not None else state.turn_index,
        "msg_type": msg_type,
        "sentiment": contextual_sentiment,
        "contextual_aggression": contextual_aggression,
        "tags": message_tags,
        "addressed_to": addressed_to,
        "word_count": len(content.split()),
        "tokens_used": max(len(content.split()), 1),
        "api_latency_ms": api_latency_ms,
    }

    print("DOCUMENT SENTIMENT:", document["sentiment"])

    print("FULL DOCUMENT:")
    print(document)

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