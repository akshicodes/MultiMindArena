from __future__ import annotations

import asyncio
import random
import sys
import time
from datetime import datetime
from typing import Any, Awaitable, Callable
from uuid import uuid4

from backend.data.topics import TOPICS
from backend.database import db

from .participants import ParticipantProfile, build_default_participants
from .persistence import ensure_session_record, persist_message, persist_topic
from .scheduler import build_histories, choose_next_speaker
from .state import SessionState, SpeakerState

from backend.analytics.aggregator import (
    generate_session_analytics
)
from backend.analytics.referee import evaluate_debate_with_llm


BroadcastCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


def safe_print(*args, **kwargs) -> None:
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        try:
            encoding = sys.stdout.encoding or "utf-8"
            safe_args = [
                str(arg).encode(encoding, errors="replace").decode(encoding, errors="replace")
                for arg in args
            ]
            print(*safe_args, **kwargs)
        except Exception:
            pass


class DebateEngine:
    def __init__(self):
        self.participants: list[ParticipantProfile] = build_default_participants()
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

    def _trim_to_word_window(self, text: str, minimum_words: int = 5, maximum_words: int = 40) -> str:
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
            return topic, "User"

        sampled_topic = random.choice(TOPICS)
        return sampled_topic["topic"], "User"

    def _resolve_participant_name(self, name: str | None) -> str | None:
        if not name:
            return None

        normalized = name.strip().lower()
        for participant in self.participants:
            if participant.name.lower() == normalized:
                return participant.name
        return None

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

    async def ensure_state(self, topic: str | None = None, session_id: str | None = None) -> SessionState:
        if session_id is not None and session_id in self.session_states:
            return self.session_states[session_id]

        resolved_topic, attributed_to = self._pick_topic(topic)
        resolved_session_id = session_id or str(uuid4())
        state = SessionState(
            session_id=resolved_session_id,
            topic=resolved_topic,
            topic_attributed_to=attributed_to,
            histories=build_histories(self.participants, resolved_topic, attributed_to),
            speaker_state={participant.name: SpeakerState() for participant in self.participants},
            created_at=datetime.utcnow(),
        )
        self.session_states[resolved_session_id] = state
        await ensure_session_record(state, self.participants)
        return state

    async def inject_topic(self, state: SessionState, broadcaster: BroadcastCallback | None = None) -> None:
        topic_message = await persist_topic(state)
        state.transcript.append(topic_message)

        await self._emit(
            broadcaster,
            {
                "event": "topic.injected",
                "session_id": state.session_id,
                "topic": state.topic,
                "attributed_to": state.topic_attributed_to,
            },
        )

    async def inject_user_message(
        self,
        state: SessionState,
        content: str,
        addressed_to: str | None = None,
        tags: list[str] | None = None,
        sentiment: float = 0.0,
        api_latency_ms: int = 0,
        broadcaster: BroadcastCallback | None = None,
    ) -> dict[str, Any]:
        clean_content = content.strip()
        if not clean_content:
            raise ValueError("User message cannot be empty")

        turn_index = len(state.transcript) + 1
        message_doc = await persist_message(
            state=state,
            speaker="User",
            content=clean_content,
            api_latency_ms=api_latency_ms,
            msg_type="user",
            turn_index=turn_index,
            tags=tags or ["user", "live"],
            addressed_to=addressed_to,
            sentiment=sentiment,
        )
        state.transcript.append(message_doc)

        user_history_entry = {
            "role": "user",
            "content": clean_content,
            "name": "User",
        }
        resolved_target = self._resolve_participant_name(addressed_to)
        if resolved_target:
            user_history_entry["name"] = resolved_target
            state.pending_direct_response_to = resolved_target
        else:
            state.pending_direct_response_to = None

        for participant in self.participants:
            state.histories[participant.name].append(dict(user_history_entry))
            state.speaker_state[participant.name].interrupted = True

        await self._emit(
            broadcaster,
            {
                "event": "message.final",
                "session_id": state.session_id,
                "message": message_doc,
                "interrupted": False,
            },
        )

        return message_doc

    async def run_turn(
        self,
        state: SessionState,
        speaker_name: str | None = None,
        broadcaster: BroadcastCallback | None = None,
    ) -> dict[str, Any]:
        lock = self._get_session_lock(state.session_id)

        async with lock:
            direct_target = state.pending_direct_response_to
            if direct_target:
                speaker = next((p for p in self.participants if p.name == direct_target), None)
                state.pending_direct_response_to = None
                if speaker is None:
                    speaker = choose_next_speaker(self.participants, state)
            elif speaker_name:
                speaker = next((p for p in self.participants if p.name == speaker_name), None)
                if not speaker:
                    speaker = choose_next_speaker(self.participants, state)
            else:
                speaker = choose_next_speaker(self.participants, state)

            state.speaker_state[speaker.name].interrupted = False

            message_id = str(uuid4())
            await self._emit(
                broadcaster,
                {
                    "event": "speaker.thinking",
                    "session_id": state.session_id,
                    "message_id": message_id,
                    "speaker": speaker.name,
                },
            )
            messages = state.histories[speaker.name]
            started_at = time.perf_counter()
            collected_chunks: list[str] = []
            interrupted = False

            async def consume_stream():
                async for chunk in speaker.client.generate_stream(
                    model=speaker.model,
                    messages=messages,
                    temperature=0.45,
                    max_tokens=120,
                ):
                    collected_chunks.append(chunk)
                    await self._emit(
                        broadcaster,
                        {
                            "event": "message.stream",
                            "session_id": state.session_id,
                            "message_id": message_id,
                            "speaker": speaker.name,
                            "delta": chunk,
                            "content": "".join(collected_chunks),
                        },
                    )

            try:
                await asyncio.wait_for(consume_stream(), timeout=12.0)
            except (asyncio.TimeoutError, Exception) as e:
                interrupted = True
                state.speaker_state[speaker.name].interrupted = True
                safe_print(f"Stream exception for {speaker.name}: {e}")

            if not collected_chunks or (interrupted and len("".join(collected_chunks).split()) < 10):
                try:
                    response_text = await speaker.client.generate(
                        model=speaker.model,
                        messages=messages,
                        temperature=0.45,
                        max_tokens=120,
                    )
                    if response_text:
                        collected_chunks = [response_text]
                except Exception as fallback_err:
                    collected_chunks = [f"[Error generating content: {fallback_err}]"]

            latency_ms = int((time.perf_counter() - started_at) * 1000)
            normalized = self._trim_to_word_window(self._normalize_text("".join(collected_chunks)))

            state.turn_index += 1
            state.speaker_state[speaker.name].last_turn_index = state.turn_index
            state.speaker_state[speaker.name].turn_count += 1
            state.speaker_state[speaker.name].interrupted = interrupted

            message_doc = await persist_message(
                state=state,
                speaker=speaker.name,
                content=normalized,
                api_latency_ms=latency_ms,
                msg_type="argument",
                message_id=message_id,
            )

            for participant in self.participants:
                if participant.name == speaker.name:
                    state.histories[participant.name].append({"role": "assistant", "content": normalized})
                else:
                    state.histories[participant.name].append(
                        {
                            "role": "user",
                            "content": normalized,
                            "name": speaker.name,
                        }
                    )

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

            return message_doc

    async def run(
        self,
        topic: str | None = None,
        rounds: int = 3,
        session_id: str | None = None,
        broadcaster: BroadcastCallback | None = None,
    ):
        state = await self.ensure_state(topic=topic, session_id=session_id)

        safe_print("\n" + "=" * 80)
        safe_print("DEBATE STARTED")
        safe_print(f"SESSION: {state.session_id}")
        safe_print(f"TOPIC: {state.topic}")
        safe_print(f"ATTRIBUTED TO: {state.topic_attributed_to}")
        safe_print("=" * 80)

        await self.inject_topic(state, broadcaster=broadcaster)

        for round_number in range(rounds):
            safe_print(f"\nROUND {round_number + 1}")
            safe_print("-" * 80)

            for participant in self.participants:
                message = await self.run_turn(
                    state=state,
                    speaker_name=participant.name,
                    broadcaster=broadcaster,
                )

                safe_print(f"\n[{message['sender']}]")
                safe_print(message["content"])

            # Generate analytics after EACH ROUND
            await generate_session_analytics(
                state.session_id
            )

            safe_print(
                f"Analytics updated for round {round_number + 1}"
            )

        # Debate finished
        await db.sessions.update_one(
            {"session_id": state.session_id},
            {
                "$set": {
                    "status": "completed",
                    "ended_at": datetime.utcnow(),
                }
            },
        )

        # Run LLM-as-a-judge referee evaluation
        try:
            judge_decision = await evaluate_debate_with_llm(state)
            if judge_decision:
                await db.sessions.update_one(
                    {"session_id": state.session_id},
                    {"$set": {"judge_decision": judge_decision}}
                )
        except Exception as e:
            safe_print(f"Error running LLM-as-a-judge: {e}")

        # Final analytics update
        await generate_session_analytics(
            state.session_id
        )

        safe_print(
            f"Analytics generated for session "
            f"{state.session_id}"
        )

        # Notify frontend that the debate has ended so it can refresh history
        await self._emit(
            broadcaster,
            {
                "event": "debate.ended",
                "session_id": state.session_id,
            },
        )

        return state.transcript