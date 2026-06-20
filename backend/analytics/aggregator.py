from collections import Counter
from backend.analytics.sentiment import calculate_sentiment


def build_analytics(messages):

    message_counts = Counter()

    sentiment_totals = {}
    sentiment_counts = {}

    all_words = []

    for msg in messages:

        sender = msg["sender"]

        message_counts[sender] += 1

        score = calculate_sentiment(
            msg["content"]
        )

        sentiment_totals[sender] = (
            sentiment_totals.get(sender, 0)
            + score
        )

        sentiment_counts[sender] = (
            sentiment_counts.get(sender, 0)
            + 1
        )

        all_words.extend(
            msg["content"].lower().split()
        )

    avg_sentiment = {}

    for sender in sentiment_totals:

        avg_sentiment[sender] = round(
            sentiment_totals[sender]
            / sentiment_counts[sender],
            3
        )

    top_words = Counter(all_words).most_common(30)

    return {
        "message_counts": dict(message_counts),
        "avg_sentiment": avg_sentiment,
        "top_words": [
            {
                "word": word,
                "count": count
            }
            for word, count in top_words
        ]
    }