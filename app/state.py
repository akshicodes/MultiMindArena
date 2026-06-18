from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


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
    pending_direct_response_to: str | None = None
    transcript: list[dict[str, Any]] = field(default_factory=list)
    histories: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    speaker_state: dict[str, SpeakerState] = field(default_factory=dict)