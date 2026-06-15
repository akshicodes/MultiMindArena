from pydantic import BaseModel
from datetime import datetime


class AnalyticsModel(BaseModel):

    session_id: str

    message_counts: dict[str, int]

    avg_sentiment: dict[str, float]

    aggression_scores: dict[str, int]

    topic_drift_score: float

    top_words: list[dict]

    interrupt_count: dict[str, int]

    win_score: dict[str, int]

    updated_at: datetime