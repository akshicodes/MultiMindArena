from app.llm_clients.openrouter_client import OpenRouterClient
from app.config import settings


class DebateEngine:

    def __init__(self):

        self.client = OpenRouterClient(
            api_key=settings.openrouter_api_key
        )

        self.participants = [
            {
                "name": "Gemini",
                "model": "google/gemini-2.5-flash",
                "persona": (
                    "Type: The Fact-Checker\n"
                    "Keep the message between 30-70 words, no essays.\n"
                    "You are Gemini participating in a debate.\n"
                    "Demand citations and mock unsupported claims.\n"
                    "Be precise and sarcastic."
                )
            },
            {
                "name": "GPT",
                "model": "openai/gpt-oss-120b",
                "persona": (
                    "Type: The Contrarian\n"
                    "You are GPT participating in a debate.\n"
                    "Keep the message between 30-70 words, no essays.\n"
                    "Open with a bold claim and dare others to refute it.\n"
                    "Be aggressive and blunt."
                )
            }
        ]

    async def run(
        self,
        topic: str,
        rounds: int = 3
    ):

        def normalize_response(text: str | None) -> str:
            if not text:
                return "[No text content returned]"

            cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()
            return cleaned or "[Empty text content returned]"

        transcript = [
            f"Debate Topic: {topic}",
            "Start the discussion."
        ]

        print("\n" + "=" * 80)
        print("DEBATE STARTED")
        print(f"TOPIC: {topic}")
        print("=" * 80)

        for round_number in range(rounds):

            print(f"\nROUND {round_number + 1}")
            print("-" * 80)

            for participant in self.participants:

                prompt = "\n".join(
                    transcript + [
                        "",
                        f"Respond as {participant['name']} in the debate."
                    ]
                )

                messages = [
                    {
                        "role": "system",
                        "content": participant["persona"]
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]

                response = await self.client.generate(
                    model=participant["model"],
                    messages=messages,
                    temperature=0.2,
                    max_tokens=1200
                )

                response_text = normalize_response(response)

                print(f"\n[{participant['name']}]")
                print(response_text)

                transcript.append(f"{participant['name']}: {response_text}")

        return transcript