# from analytics.aggregator import build_analytics
from backend.analytics.aggregator import build_analytics


messages = [
    {
        "sender": "Gemini",
        "content": "I love this idea"
    },
    {
        "sender": "GPT",
        "content": "This argument is terrible"
    },
    {
        "sender": "Gemini",
        "content": "The debate is interesting"
    }
]

result = build_analytics(messages)
print("Standard Drift:", result["topic_drift_score"])
assert result["topic_drift_score"] == 1.0

result_dynamic = build_analytics(messages, keywords=["idea", "interesting"])
print("Dynamic Drift (with matching words):", result_dynamic["topic_drift_score"])
assert result_dynamic["topic_drift_score"] == 0.0

print("All tests passed successfully!")