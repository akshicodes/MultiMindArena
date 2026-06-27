import json
import re
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from backend.llm_clients.openrouter_client import OpenRouterClient
from backend.config import settings

analyzer = SentimentIntensityAnalyzer()

def calculate_sentiment(text: str) -> float:
    """
    Returns sentiment score between -1 and +1
    """
    return analyzer.polarity_scores(text)["compound"]


async def analyze_contextual_tone(text: str) -> dict | None:
    try:
        client = OpenRouterClient(api_key=settings.openrouter_api_key)
        prompt = f"""
Analyze the tone of the following statement from a debate:
"{text}"

Grade it on:
1. Sentiment: Score from -1.0 (very negative/hostile) to +1.0 (very positive/agreeable/supportive).
2. Aggression: Score from 0.0 (perfectly polite and constructive) to 1.0 (highly aggressive, toxic, insulting, patronizing, or passive-aggressive).

Respond ONLY with a valid raw JSON object matching this schema:
{{
  "sentiment": 0.25,
  "aggression": 0.4
}}
Do not include any markdown formatting, code blocks, or extra text.
"""
        messages = [
            {
                "role": "system",
                "content": "You are a precise linguistic analysis assistant. Respond ONLY with valid raw JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        response = await client.generate(
            model="google/gemini-2.5-flash",
            messages=messages,
            temperature=0.1,
            max_tokens=40
        )
        
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n", "", cleaned)
            cleaned = re.sub(r"\n```$", "", cleaned)
            cleaned = cleaned.strip()
            
        return json.loads(cleaned)
    except Exception as e:
        print(f"Error in analyze_contextual_tone: {e}")
        return None