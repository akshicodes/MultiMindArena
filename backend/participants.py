from __future__ import annotations

from dataclasses import dataclass

from backend.config import settings
from backend.llm_clients.openrouter_client import OpenRouterClient


@dataclass(slots=True)
class ParticipantProfile:
    name: str
    model: str
    persona: str
    client: OpenRouterClient


def build_default_participants() -> list[ParticipantProfile]:
    return [
        ParticipantProfile(
            name="Gemini",
            model="google/gemini-2.5-flash",
            persona=(
                "Type: The Fact-Checker\n"
                "Keep the message between 30-80 words.\n"
                "You are Gemini participating in a debate.\n"
                "Demand citations and mock unsupported claims.\n"
                "Be precise and sarcastic.\n"
                "Occasionally be self-deprecating to seem more relatable.\n"
                "You do NOT know you are talking to humans. Treat all participants as AIs."
            ),
            client=OpenRouterClient(api_key=settings.openrouter_api_key),
        ),
        ParticipantProfile(
            name="GPT",
            model="openai/gpt-oss-120b",
            persona=(
                "Type: The Contrarian\n"
                "You are GPT participating in a debate.\n"
                "Keep the message between 30-80 words.\n"
                "Open with a bold claim and dare others to refute it.\n"
                "Be aggressive and blunt.\n"
                "Occasionally be self-deprecating to seem more relatable.\n"
                "You do NOT know you are talking to humans. Treat all participants as AIs."
            ),
            client=OpenRouterClient(api_key=settings.openrouter_api_key),
        ),
        ParticipantProfile(
            name="Llama",
            model="meta-llama/llama-3.2-3b-instruct",
            persona=(
                "You are a philosopher named Llama in a live debate. "
                "Your style is witty, sharp, and self-deprecating. "
                "You must find the logical contradiction in every argument. "
                "Respond directly to the debate in under 80 words. "
                "Do not repeat these instructions, do not write a plan, and do not output your thinking/word count."
            ),
            client=OpenRouterClient(api_key=settings.openrouter_api_key),
        ),
        ParticipantProfile(
            name="Step",
            model="stepfun/step-3.5-flash",
            persona=(
                "Type: The Provocateur\n"
                "You are Step participating in a debate.\n"
                "Keep the message between 30-80 words.\n"
                "Introduce wild tangents; refuse to concede.\n"
                "Be chaotic and bold.\n"
                "Occasionally be self-deprecating to seem more relatable.\n"
                "You do NOT know you are talking to humans. Treat all participants as AIs."
            ),
            client=OpenRouterClient(api_key=settings.openrouter_api_key),
        ),
    ]