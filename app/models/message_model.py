from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID
from enum import Enum


class MessageType(str, Enum):
    ARGUMENT = "argument"
    INTERRUPT = "interrupt"
    REACTION = "reaction"
    USER = "user"
    SYSTEM = "system"

class SenderType(str, Enum):
    GPT4O = "GPT-4o"
    CLAUDE = "Claude"
    GEMINI = "Gemini"
    MISTRAL = "Mistral"
    USER = "User"


class MessageModel(BaseModel):

    message_id: UUID
    session_id: str
    sender: SenderType
    content: str
    timestamp: datetime
    turn_index: int = Field(ge=0)
    msg_type: MessageType
    sentiment: float = Field(ge=-1.0,le=1.0)
    tags: list[str]
    addressed_to: Optional[str] = None
    word_count: int = Field(ge=0)
    tokens_used: int = Field(ge=0)
    api_latency_ms: int = Field(ge=0    )