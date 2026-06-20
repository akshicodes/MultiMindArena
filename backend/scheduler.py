from __future__ import annotations

import random

from .participants import ParticipantProfile
from .state import SessionState


def build_histories(participants: list[ParticipantProfile], topic: str, attributed_to: str) -> dict[str, list[dict[str, str]]]:
    histories: dict[str, list[dict[str, str]]] = {}
    seed_message = {
        "role": "user",
        "content": f"Debate topic: {topic}",
        "name": attributed_to.replace(" ", "_"),
    }

    for participant in participants:
        histories[participant.name] = [
            {"role": "system", "content": participant.persona},
            dict(seed_message),
        ]

    return histories


def speaker_weight(participant: ParticipantProfile, state: SessionState) -> float:
    speaker_state = state.speaker_state[participant.name]
    weight = 1.0

    if speaker_state.last_turn_index >= 0:
        turns_since_last = state.turn_index - speaker_state.last_turn_index
        weight += min(max(turns_since_last, 1), 8) * 0.35
        if turns_since_last <= 1:
            weight *= 0.3
    else:
        weight += 1.0

    if speaker_state.interrupted:
        weight += 0.5

    if state.transcript and state.transcript[-1]["sender"] == participant.name:
        weight *= 0.2

    return max(weight, 0.05)


def choose_next_speaker(participants: list[ParticipantProfile], state: SessionState) -> ParticipantProfile:
    weights = [speaker_weight(participant, state) for participant in participants]
    return random.choices(participants, weights=weights, k=1)[0]