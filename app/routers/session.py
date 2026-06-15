from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from ..database import db
from ..models import analytics_model, message_model, session_model

router = APIRouter(prefix="/sessions", tags=["sessions"])
class UserMessagePayload(BaseModel):
    content: str
    addressed_to: Optional[str] = None
    tags: Optional[list[str]] = None
    sentiment: Optional[float] = Field(default=0.0, ge=-1.0, le=1.0)
    api_latency_ms: Optional[int] = Field(default=0, ge=0)


@router.post("/", status_code=201)
async def create_session(session: session_model.SessionModel):
    result = await db.sessions.insert_one(jsonable_encoder(session))
    return {"inserted_id": str(result.inserted_id), "session_id": str(session.session_id)}


@router.get("/{session_id}")
async def get_session(session_id: UUID):
    session = await db.sessions.find_one({"session_id": str(session_id)})
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    session["_id"] = str(session["_id"])
    return session


@router.delete("/{session_id}")
async def end_session(session_id: UUID):
    update = {
        "$set": {
            "status": session_model.SessionStatus.COMPLETED.value,
            "ended_at": datetime.utcnow()
        }
    }
    result = await db.sessions.update_one({"session_id": str(session_id)}, update)
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": str(session_id), "status": "completed"}


@router.get("/{session_id}/messages")
async def get_session_messages(
    session_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
):
    skip = (page - 1) * limit
    cursor = db.messages.find({"session_id": str(session_id)}).sort("timestamp", 1).skip(skip).limit(limit)
    messages = await cursor.to_list(length=limit)
    for message in messages:
        message["_id"] = str(message["_id"])
    return {"page": page, "limit": limit, "messages": messages}


@router.get("/{session_id}/analytics")
async def get_session_analytics(session_id: UUID):
    analytics = await db.analytics.find_one({"session_id": str(session_id)})
    if analytics is None:
        raise HTTPException(status_code=404, detail="Analytics not found for session")
    analytics["_id"] = str(analytics["_id"])
    return analytics


@router.post("/{session_id}/user-message", status_code=201)
async def inject_user_message(session_id: UUID, payload: UserMessagePayload):
    session = await db.sessions.find_one({"session_id": str(session_id)})
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("status") != session_model.SessionStatus.ACTIVE.value:
        raise HTTPException(status_code=400, detail="Session is not active")

    turn_index = await db.messages.count_documents({"session_id": str(session_id)}) + 1
    tags = payload.tags or []

    user_message = message_model.MessageModel(
        message_id=uuid4(),
        session_id=str(session_id),
        sender=message_model.SenderType.USER,
        content=payload.content,
        timestamp=datetime.utcnow(),
        turn_index=turn_index,
        msg_type=message_model.MessageType.USER,
        sentiment=payload.sentiment,
        tags=tags,
        addressed_to=payload.addressed_to,
        word_count=len(payload.content.split()),
        tokens_used=max(len(payload.content.split()), 1),
        api_latency_ms=payload.api_latency_ms or 0,
    )

    result = await db.messages.insert_one(jsonable_encoder(user_message))
    return {"inserted_id": str(result.inserted_id), "message_id": str(user_message.message_id)}
