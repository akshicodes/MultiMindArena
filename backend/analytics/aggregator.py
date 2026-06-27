from collections import Counter
import re

from nltk.corpus import stopwords

from backend.analytics.sentiment import calculate_sentiment
from backend.database import db


STOP_WORDS = set(stopwords.words("english"))

AGGRESSIVE_WORDS = {
    "wrong",
    "ridiculous",
    "nonsense",
    "absurd",
    "stupid",
    "false",
    "never",
    "cannot",
    "terrible",
    "bad",
    "idiotic",
    "foolish",
    "useless"
}


def build_analytics(messages, keywords=None):

    message_counts = Counter()

    sentiment_totals = {}
    sentiment_counts = {}

    aggression_scores = {}
    win_scores = {}

    longest_streak = {}
    current_streak = {}

    all_words = []

    sentiment_timeline = []
    rolling_sentiment = []

    running_total = 0
    turn_index = 0

    positive_keywords = [
        "agree",
        "correct",
        "good point",
        "valid",
        "excellent",
        "strong argument"
    ]

    previous_sender = None

    for msg in messages:

        sender = msg["sender"]
        content = msg["content"]

        # --------------------
        # Longest Streak
        # --------------------
        if sender == previous_sender:

            current_streak[sender] = (
                current_streak.get(sender, 1) + 1
            )

        else:

            current_streak[sender] = 1

        previous_sender = sender

        longest_streak[sender] = max(
            longest_streak.get(sender, 0),
            current_streak[sender]
        )

        # --------------------
        # Message Count
        # --------------------
        message_counts[sender] += 1

        # --------------------
        # Win Predictor
        # --------------------
        win_scores[sender] = win_scores.get(sender, 0)

        content_lower = content.lower()

        for keyword in positive_keywords:
            if keyword in content_lower:
                win_scores[sender] += 1

        # --------------------
        # Sentiment
        # --------------------
        score = calculate_sentiment(content)

        sentiment_totals[sender] = (
            sentiment_totals.get(sender, 0)
            + score
        )

        sentiment_counts[sender] = (
            sentiment_counts.get(sender, 0)
            + 1
        )

        # --------------------
        # Sentiment Timeline
        # --------------------
        turn_index += 1

        sentiment_timeline.append({
            "turn": turn_index,
            "sender": sender,
            "sentiment": round(score, 3)
        })

        running_total += score

        rolling_sentiment.append({
            "turn": turn_index,
            "value": round(
                running_total / turn_index,
                3
            )
        })

        # --------------------
        # Aggression Index
        # --------------------
        contextual_agg = msg.get("contextual_aggression")
        if contextual_agg is not None:
            aggressive_count = contextual_agg * 10
        else:
            words = re.findall(
                r"\b[a-zA-Z]+\b",
                content.lower()
            )
            aggressive_count = sum(
                1
                for word in words
                if word in AGGRESSIVE_WORDS
            )

        aggression_scores[sender] = (
            aggression_scores.get(sender, 0)
            + aggressive_count
        )

        # --------------------
        # Word Cloud
        # --------------------
        filtered_words = [
            word
            for word in words
            if word not in STOP_WORDS
        ]

        all_words.extend(filtered_words)

    # --------------------
    # Average Sentiment
    # --------------------
    avg_sentiment = {}

    for sender in sentiment_totals:

        avg_sentiment[sender] = round(
            sentiment_totals[sender]
            / sentiment_counts[sender],
            3
        )

    # --------------------
    # Top Words
    # --------------------
    top_words = Counter(all_words).most_common(30)

    # --------------------
    # Topic Drift
    # --------------------
    if keywords:
        topic_keywords = {w.strip().lower() for w in keywords if w.strip()}
    else:
        topic_keywords = {
            "happiness",
            "measure",
            "scientific"
        }

    found_keywords = 0

    for word, count in top_words:

        if word in topic_keywords:
            found_keywords += 1

    topic_drift_score = round(
        1 - (
            found_keywords /
            max(len(topic_keywords), 1)
        ),
        2
    )

    analytics = {
        "message_counts": dict(message_counts),
        "avg_sentiment": avg_sentiment,
        "aggression_scores": aggression_scores,
        "win_score": win_scores,
        "longest_streak": longest_streak,
        "topic_drift_score": topic_drift_score,
        "sentiment_timeline": sentiment_timeline,
        "rolling_sentiment": rolling_sentiment,
        "top_words": [
            {
                "word": word,
                "count": count
            }
            for word, count in top_words
        ]
    }

    return analytics


async def generate_session_analytics(
    session_id: str
):

    session = await db.sessions.find_one({"session_id": session_id})
    keywords = None
    if session:
        keywords = session.get("keywords")

    messages = await db.messages.find(
        {"session_id": session_id}
    ).sort(
        "timestamp",
        1
    ).to_list(None)

    if not messages:
        return None

    analytics_data = build_analytics(
        messages,
        keywords=keywords
    )

    analytics_doc = {
        "session_id": session_id,
        **analytics_data
    }

    if session and "judge_decision" in session:
        analytics_doc["judge_decision"] = session["judge_decision"]

    await db.analytics.update_one(
        {
            "session_id": session_id
        },
        {
            "$set": analytics_doc
        },
        upsert=True
    )

    return analytics_doc