import json
import re
from backend.llm_clients.openrouter_client import OpenRouterClient
from backend.config import settings
from backend.state import SessionState

async def evaluate_debate_with_llm(state: SessionState) -> dict | None:
    # Build transcript text
    transcript_text = ""
    for msg in state.transcript:
        # Ignore system topic seed messages or metadata
        if msg.get("msg_type") == "system" or msg.get("tags") == ["topic", "seed"]:
            continue
        sender = msg.get("sender") or msg.get("speaker") or "System"
        content = msg.get("content") or ""
        transcript_text += f"{sender}: {content}\n\n"

    if not transcript_text.strip():
        return None

    try:
        client = OpenRouterClient(api_key=settings.openrouter_api_key)
        prompt = f"""
You are an expert academic debate referee and judge. Analyze the following debate transcript on the topic: "{state.topic}" and evaluate each participant.

Debate Transcript:
{transcript_text}

For each participant, provide:
1. Logical consistency (score 1-10 and brief reasoning)
2. Rebuttal effectiveness (score 1-10 and brief reasoning)
3. Persuasiveness (score 1-10 and brief reasoning)
4. Evidence/rhetorical style (score 1-10 and brief reasoning)

Finally, provide a "Judge Decision Summary" announcing the winner and summarizing the key reasons for the decision.

Your output must be structured as valid JSON with the following schema:
{{
  "evaluations": [
    {{
      "participant": "Participant Name",
      "logical_consistency": {{ "score": 8, "reasoning": "..." }},
      "rebuttal_effectiveness": {{ "score": 7, "reasoning": "..." }},
      "persuasiveness": {{ "score": 8, "reasoning": "..." }},
      "evidence_rhetorical_style": {{ "score": 9, "reasoning": "..." }}
    }}
  ],
  "winner": "Winner Participant Name or Tie",
  "decision_summary": "..."
}}

Ensure that you return ONLY valid raw JSON. Do not include markdown code blocks, backticks, or any preamble.
"""
        messages = [
            {
                "role": "system",
                "content": "You are a precise debate referee. Respond ONLY with valid raw JSON matching the requested schema."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        response = await client.generate(
            model="google/gemini-2.5-flash",
            messages=messages,
            temperature=0.2,
            max_tokens=800
        )
        
        # Clean response if LLM enclosed it in ```json ... ```
        cleaned_response = response.strip()
        if cleaned_response.startswith("```"):
            cleaned_response = re.sub(r"^```(?:json)?\n", "", cleaned_response)
            cleaned_response = re.sub(r"\n```$", "", cleaned_response)
            cleaned_response = cleaned_response.strip()

        return json.loads(cleaned_response)
    except Exception as e:
        print(f"Error evaluating debate: {e}")
        return None
