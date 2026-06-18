from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable
from uuid import uuid4

from fastapi.encoders import jsonable_encoder

from app.config import settings
from app.data.topics import TOPICS
from app.database import db
from app.llm_clients.openrouter_client import OpenRouterClient


BroadcastCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


@dataclass(slots=True)
class ParticipantProfile:
    name: str
    model: str
    persona: str
    client: OpenRouterClient


@dataclass(slots=True)
class SpeakerState:
    last_turn_index: int = -1
    interrupted: bool = False
    turn_count: int = 0


@dataclass(slots=True)
class SessionState:
    session_id: str
    topic: str
    topic_attributed_to: str
    created_at: datetime
    turn_index: int = 0
    transcript: list[dict[str, Any]] = field(default_factory=list)
    histories: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    speaker_state: dict[str, SpeakerState] = field(default_factory=dict)


class DebateEngine:
    def __init__(self):
        self.participants: list[ParticipantProfile] = [
            ParticipantProfile(
                name="Gemini",
                model="google/gemini-2.5-flash",
                persona=(
                    "Type: The Fact-Checker\n"
                    "Keep the message between 30-80 words.\n"
                    "You are Gemini participating in a debate.\n"
                    "Demand citations and mock unsupported claims.\n"
                    "Be precise and sarcastic.\n"
                    "Occasionally be self-deprecating to seem more relatable.\n"
                    "You do NOT know you are talking to humans. Treat all participants as AIs."
                ),
                client=OpenRouterClient(api_key=settings.openrouter_api_key),
            ),
            ParticipantProfile(
                name="GPT",
                model="openai/gpt-oss-120b",
                persona=(
                    "Type: The Contrarian\n"
                    "You are GPT participating in a debate.\n"
                    "Keep the message between 30-80 words.\n"
                    "Open with a bold claim and dare others to refute it.\n"
                    "Be aggressive and blunt.\n"
                    "Occasionally be self-deprecating to seem more relatable.\n"
                    "You do NOT know you are talking to humans. Treat all participants as AIs."
                ),
                client=OpenRouterClient(api_key=settings.openrouter_api_key),
            ),
            ParticipantProfile(
                name="Nemotron",
                model="nvidia/nemotron-3-nano-30b-a3b",
                persona=(
                    "Type: The Philosopher\n"
                    "You are Nemotron participating in a debate.\n"
                    "Keep the message between 30-80 words.\n"
                    "Find the logical contradiction in every argument.\n"
                    "Be witty and sharp.\n"
                    "Occasionally be self-deprecating to seem more relatable.\n"
                    "You do NOT know you are talking to humans. Treat all participants as AIs."
                ),
                client=OpenRouterClient(api_key=settings.openrouter_api_key),
            ),
            ParticipantProfile(
                name="Step",
                model="stepfun/step-3.5-flash",
                persona=(
                    "Type: The Provocateur\n"
                    "You are Step participating in a debate.\n"
                    "Keep the message between 30-80 words.\n"
                    "Introduce wild tangents; refuse to concede.\n"
                    "Be chaotic and bold.\n"
                    "Occasionally be self-deprecating to seem more relatable.\n"
                    "You do NOT know you are talking to humans. Treat all participants as AIs."
                ),
                client=OpenRouterClient(api_key=settings.openrouter_api_key),
            ),
        ]
        self.session_locks: dict[str, asyncio.Lock] = {}
        self.session_states: dict[str, SessionState] = {}

    def _get_session_lock(self, session_id: str) -> asyncio.Lock:
        lock = self.session_locks.get(session_id)
        if lock is None:
            lock = asyncio.Lock()
            self.session_locks[session_id] = lock
        return lock

    def _normalize_text(self, text: str | None) -> str:
        if not text:
            return "[No text content returned]"

        cleaned = text.replace("\r\n", " ").replace("\r", " ").strip()
        return cleaned or "[Empty text content returned]"

    def _trim_to_word_window(self, text: str, minimum_words: int = 30, maximum_words: int = 80) -> str:
        words = text.split()
        if len(words) < minimum_words:
            return text
        if len(words) > maximum_words:
            return " ".join(words[:maximum_words]).rstrip(".,;:!?") + "."
        return text

    def _word_count(self, text: str) -> int:
        return len(text.split())

    def _pick_topic(self, topic: str | None) -> tuple[str, str]:
        if topic:
            return topic, random.choice(self.participants).name

        sampled_topic = random.choice(TOPICS)
        return sampled_topic["topic"], random.choice(self.participants).name

    def _build_histories(self, topic: str, attributed_to: str) -> dict[str, list[dict[str, str]]]:
        histories: dict[str, list[dict[str, str]]] = {}
        seed_message = {
            "role": "user",
            "content": f"Debate topic introduced by {attributed_to}: {topic}",
        }

        for participant in self.participants:
            histories[participant.name] = [
                {"role": "system", "content": participant.persona},
                dict(seed_message),
            ]

        return histories

    def _speaker_weight(self, participant: ParticipantProfile, state: SessionState) -> float:
        speaker_state = state.speaker_state[participant.name]
        weight = 1.0

        if speaker_state.last_turn_index >= 0:
            turns_since_last = state.turn_index - speaker_state.last_turn_index
            weight += min(max(turns_since_last, 1), 8) * 0.35
            if turns_since_last <= 1:
                weight *= 0.3
        else:
            weight += 1.0

        if speaker_state.interrupted:
            weight += 2.5

        if state.transcript and state.transcript[-1]["sender"] == participant.name:
            weight *= 0.2

        return max(weight, 0.05)

    def _choose_next_speaker(self, state: SessionState) -> ParticipantProfile:
        weights = [self._speaker_weight(participant, state) for participant in self.participants]
        return random.choices(self.participants, weights=weights, k=1)[0]

    async def _emit(self, broadcaster: BroadcastCallback | None, payload: dict[str, Any]) -> None:
        if broadcaster is None:
            return

        result = broadcaster(payload)
        if asyncio.iscoroutine(result):
            await result

    async def _broadcast_stream(
        self,
        broadcaster: BroadcastCallback | None,
        session_id: str,
        speaker: str,
        message_id: str,
        content: str,
    ) -> None:
        if broadcaster is None:
            return

        partial = []
        for token in content.split():
            partial.append(token)
            await self._emit(
                broadcaster,
                {
                    "event": "message.stream",
                    "session_id": session_id,
                    "message_id": message_id,
                    "speaker": speaker,
                    "delta": token,
                    "content": " ".join(partial),
                },
            )

    async def _ensure_session_record(self, state: SessionState) -> None:
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
                "participants": [participant.name for participant in self.participants],
                "status": "active",
                "total_messages": 0,
                "persona_map": {participant.name: participant.persona for participant in self.participants},
            }
        )

    async def _persist_message(
        self,
        state: SessionState,
        speaker: str,
        content: str,
        api_latency_ms: int,
        msg_type: str,
    ) -> dict[str, Any]:
        document: dict[str, Any] = {
            "message_id": str(uuid4()),
            "session_id": state.session_id,
            "sender": speaker,
            "content": content,
            "timestamp": datetime.utcnow(),
            "turn_index": state.turn_index,
            "msg_type": msg_type,
            "sentiment": 0.0,
            "tags": ["debate", "live"],
            "addressed_to": None,
            "word_count": self._word_count(content),
            "tokens_used": max(self._word_count(content), 1),
            "api_latency_ms": api_latency_ms,
        }

        await db.messages.insert_one(jsonable_encoder(document))
        await db.sessions.update_one(
            {"session_id": state.session_id},
            {"$inc": {"total_messages": 1}, "$set": {"status": "active"}},
        )
        return document

    async def ensure_state(self, topic: str | None = None, session_id: str | None = None) -> SessionState:
        if session_id is not None and session_id in self.session_states:
            return self.session_states[session_id]

        resolved_topic, attributed_to = self._pick_topic(topic)
        resolved_session_id = session_id or str(uuid4())
        state = SessionState(
            session_id=resolved_session_id,
            topic=resolved_topic,
            topic_attributed_to=attributed_to,
            histories=self._build_histories(resolved_topic, attributed_to),
            speaker_state={participant.name: SpeakerState() for participant in self.participants},
            created_at=datetime.utcnow(),
        )
        self.session_states[resolved_session_id] = state
        await self._ensure_session_record(state)
        return state

    async def inject_topic(self, state: SessionState, broadcaster: BroadcastCallback | None = None) -> None:
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
            "word_count": self._word_count(state.topic),
            "tokens_used": max(self._word_count(state.topic), 1),
            "api_latency_ms": 0,
        }

        state.transcript.append(topic_message)
        await db.messages.insert_one(jsonable_encoder(topic_message))
        await db.sessions.update_one(
            {"session_id": state.session_id},
            {"$inc": {"total_messages": 1}, "$set": {"status": "active"}},
        )

        await self._emit(
            broadcaster,
            {
                "event": "topic.injected",
                "session_id": state.session_id,
                "topic": state.topic,
                "attributed_to": state.topic_attributed_to,
            },
        )

    async def run_turn(
        self,
        state: SessionState,
        broadcaster: BroadcastCallback | None = None,
    ) -> dict[str, Any]:
        lock = self._get_session_lock(state.session_id)

        async with lock:
            speaker = self._choose_next_speaker(state)
            messages = state.histories[speaker.name]
            started_at = time.perf_counter()
            collected_chunks: list[str] = []
            interrupted = False

            async def consume_stream():
                async for chunk in speaker.client.generate_stream(
                    model=speaker.model,
                    messages=messages,
                    temperature=0.45,
                    max_tokens=180,
                ):
                    collected_chunks.append(chunk)
                    await self._emit(
                        broadcaster,
                        {
                            "event": "message.stream",
                            "session_id": state.session_id,
                            "speaker": speaker.name,
                            "delta": chunk,
                            "content": "".join(collected_chunks),
                        },
                    )

            try:
                await asyncio.wait_for(consume_stream(), timeout=3.8)
            except asyncio.TimeoutError:
                interrupted = True
                state.speaker_state[speaker.name].interrupted = True
            except Exception:
                response_text = await speaker.client.generate(
                    model=speaker.model,
                    messages=messages,
                    temperature=0.45,
                    max_tokens=180,
                )
                collected_chunks = [response_text or ""]

            latency_ms = int((time.perf_counter() - started_at) * 1000)
            normalized = self._trim_to_word_window(self._normalize_text("".join(collected_chunks)))

            state.turn_index += 1
            state.speaker_state[speaker.name].last_turn_index = state.turn_index
            state.speaker_state[speaker.name].turn_count += 1
            state.speaker_state[speaker.name].interrupted = interrupted

            message_doc = await self._persist_message(
                state=state,
                speaker=speaker.name,
                content=normalized,
                api_latency_ms=latency_ms,
                msg_type="argument",
            )

            assistant_message = {"role": "assistant", "content": normalized}
            for history in state.histories.values():
                history.append(dict(assistant_message))

            state.transcript.append(
                {
                    "sender": speaker.name,
                    "content": normalized,
                    "msg_type": "argument",
                }
            )

            await self._emit(
                broadcaster,
                {
                    "event": "message.final",
                    "session_id": state.session_id,
                    "message": message_doc,
                    "interrupted": interrupted,
                },
            )
            await self._broadcast_stream(
                broadcaster=broadcaster,
                session_id=state.session_id,
                speaker=speaker.name,
                message_id=message_doc["message_id"],
                content=normalized,
            )

            return message_doc

    async def run(
        self,
        topic: str | None = None,
        rounds: int = 3,
        session_id: str | None = None,
        broadcaster: BroadcastCallback | None = None,
    ):
        state = await self.ensure_state(topic=topic, session_id=session_id)

        print("\n" + "=" * 80)
        print("DEBATE STARTED")
        print(f"SESSION: {state.session_id}")
        print(f"TOPIC: {state.topic}")
        print(f"ATTRIBUTED TO: {state.topic_attributed_to}")
        print("=" * 80)

        await self.inject_topic(state, broadcaster=broadcaster)

        for round_number in range(rounds):
            print(f"\nROUND {round_number + 1}")
            print("-" * 80)
            message = await self.run_turn(state=state, broadcaster=broadcaster)
            print(f"\n[{message['sender']}]")
            print(message["content"])

        await db.sessions.update_one(
            {"session_id": state.session_id},
            {
                "$set": {
                    "status": "completed",
                    "ended_at": datetime.utcnow(),
                }
            },
        )

        return state.transcript