import asyncio
from datetime import datetime
import tempfile
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..config import settings
from ..database import db
from ..debate_engine import DebateEngine
from ..models import analytics_model, message_model, session_model
from ..realtime import session_connection_manager
from ..tts_service import TTSRequestPayload, TTSService

router = APIRouter(prefix="/sessions", tags=["sessions"])
debate_engine = DebateEngine()
tts_service = TTSService()


class UserMessagePayload(BaseModel):
    content: str
    addressed_to: Optional[str] = None
    tags: Optional[list[str]] = None
    sentiment: Optional[float] = Field(default=0.0, ge=-1.0, le=1.0)
    api_latency_ms: Optional[int] = Field(default=0, ge=0)


class StartDebatePayload(BaseModel):
    topic: Optional[str] = None
    rounds: int = Field(default=3, ge=1, le=12)


@router.post("/", status_code=201)
async def create_session(session: session_model.SessionModel):
    result = await db.sessions.insert_one(jsonable_encoder(session))
    return {"inserted_id": str(result.inserted_id), "session_id": str(session.session_id)}


@router.post("/start")
async def start_debate(payload: StartDebatePayload):
    if not payload.topic or not payload.topic.strip():
        raise HTTPException(status_code=422, detail="A debate topic is required to start.")
    state = await debate_engine.ensure_state(topic=payload.topic.strip())

    return {
        "session_id": state.session_id,
        "topic": state.topic,
        "topic_attributed_to": state.topic_attributed_to,
        "rounds": payload.rounds,
        "ws_url": f"/sessions/{state.session_id}/ws",
    }


@router.post("/{session_id}/run")
async def run_debate(session_id: UUID, payload: StartDebatePayload):
    session_key = str(session_id)
    state = debate_engine.session_states.get(session_key)
    if state is None:
        topic = payload.topic
        if not topic:
            session = await db.sessions.find_one({"session_id": session_key})
            if session:
                topic = session.get("topic")
        state = await debate_engine.ensure_state(topic=topic, session_id=session_key)

    async def broadcaster(payload: dict):
        await session_connection_manager.broadcast(state.session_id, payload)

    asyncio.create_task(
        debate_engine.run(
            topic=state.topic,
            rounds=payload.rounds,
            session_id=state.session_id,
            broadcaster=broadcaster,
        )
    )

    return {
        "session_id": state.session_id,
        "status": "started",
        "rounds": payload.rounds,
    }
@router.get("")
async def list_sessions():

    cursor = (
        db.sessions
        .find(
            {},
            {
                "_id": 0,
                "session_id": 1,
                "topic": 1,
                "started_at": 1,
                "ended_at": 1,
                "status": 1,
                "total_messages": 1,
            },
        )
        .sort("started_at", -1)
    )

    return await cursor.to_list(length=100)


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

    session_key = str(session_id)
    state = debate_engine.session_states.get(session_key)
    if state is None:
        state = await debate_engine.ensure_state(topic=session["topic"], session_id=session_key)

    async def broadcaster(payload: dict):
        await session_connection_manager.broadcast(state.session_id, payload)

    user_message = await debate_engine.inject_user_message(
        state=state,
        content=payload.content,
        addressed_to=payload.addressed_to,
        tags=payload.tags,
        sentiment=payload.sentiment or 0.0,
        api_latency_ms=payload.api_latency_ms or 0,
        broadcaster=broadcaster,
    )

    return {"inserted_id": str(user_message["message_id"]), "message": user_message}


@router.post("/tts")
async def generate_tts(payload: TTSRequestPayload):
    try:
        result = await tts_service.generate(
            text=payload.text,
            speaker=payload.speaker,
            provider=payload.provider,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/tts/audio/{filename}")
async def get_tts_audio(filename: str):
    audio_path = Path(tempfile.gettempdir()) / "debate_tts_temp" / filename
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(audio_path, media_type="audio/mpeg")


@router.delete("/tts/audio/{filename}")
async def delete_tts_audio(filename: str):
    audio_path = Path(tempfile.gettempdir()) / "debate_tts_temp" / filename
    if audio_path.exists():
        try:
            audio_path.unlink()
            return {"status": "deleted"}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
    raise HTTPException(status_code=404, detail="File not found")


async def periodic_cleanup():
    while True:
        try:
            tts_service.cleanup_old_files(max_age_seconds=300)
        except Exception as e:
            print(f"Error in periodic cleanup: {e}")
        await asyncio.sleep(60)


@router.on_event("startup")
async def startup_event():
    asyncio.create_task(periodic_cleanup())


@router.websocket("/{session_id}/ws")
async def session_ws(websocket: WebSocket, session_id: UUID):
    await session_connection_manager.connect(str(session_id), websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await session_connection_manager.disconnect(str(session_id), websocket)
