from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID
from enum import Enum


class SessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class SessionModel(BaseModel):

    session_id: UUID

    topic: str

    topic_attributed_to: str

    started_at: datetime

    ended_at: Optional[datetime] = None

    participants: list[str]

    status: SessionStatus

    total_messages: int = Field(
        default=0,
        ge=0
    )

    persona_map: dict[str, str]