from pydantic import BaseModel, Field
from enum import Enum


class TopicCategory(str, Enum):
    PHILOSOPHY = "philosophy"
    TECH = "tech"
    SOCIETY = "society"
    SCIENCE = "science"
    POP_CULTURE = "pop-culture"


class TopicModel(BaseModel):

    topic: str

    category: TopicCategory

    difficulty: int = Field(
        ge=1,
        le=5
    )

    times_used: int = Field(
        default=0,
        ge=0
    )

    avg_message_count: float = Field(
        default=0,
        ge=0
    )

    tags: list[str]