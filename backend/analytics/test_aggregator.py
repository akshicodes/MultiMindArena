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

print(result)