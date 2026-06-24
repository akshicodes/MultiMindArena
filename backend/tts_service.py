from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from .config import settings


class TTSRequestPayload(BaseModel):
    provider: Optional[str] = Field(default=None, description="edge or elevenlabs")
    speaker: str = Field(default="GPT")
    text: str = Field(..., min_length=1)


class TTSProvider:
    name: str = "base"

    async def generate(self, text: str, speaker: str, output_path: Path) -> Path:
        raise NotImplementedError

    def get_voice(self, speaker: str) -> str:
        return speaker


class EdgeTTSProvider(TTSProvider):
    name = "edge"
    EDGE_VOICE_MAP = {
        "GPT": "en-US-AriaNeural",
        "Gemini": "en-US-JennyNeural",
        "Nemotron": "en-GB-SoniaNeural",
        "Step": "en-US-GuyNeural",
    }

    def get_voice(self, speaker: str) -> str:
        return self.EDGE_VOICE_MAP.get(speaker, speaker)

    async def generate(self, text: str, speaker: str, output_path: Path) -> Path:
        import edge_tts

        voice = self.get_voice(speaker)
        communicate = edge_tts.Communicate(text, voice)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        await communicate.save(str(output_path))
        return output_path


class ElevenLabsProvider(TTSProvider):
    name = "elevenlabs"
    ELEVENLABS_VOICE_MAP = {
        "GPT": "GPT",
        "Gemini": "Gemini",
        "Nemotron": "Nemotron",
        "Step": "Step",
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "elevenlab_api_key", None)

    def get_voice(self, speaker: str) -> str:
        return self.ELEVENLABS_VOICE_MAP.get(speaker, speaker)

    async def generate(self, text: str, speaker: str, output_path: Path) -> Path:
        if not self.api_key:
            raise RuntimeError("ElevenLabs API key is not configured")

        from elevenlabs.client import ElevenLabs

        client = ElevenLabs(api_key=self.api_key)
        voice_id = self.get_voice(speaker)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if hasattr(client, "text_to_speech") and hasattr(client.text_to_speech, "convert"):
                audio = client.text_to_speech.convert(
                    text=text,
                    voice_id=voice_id,
                    model_id="eleven_multilingual_v2",
                    output_format="mp3_44100_128",
                )
            elif hasattr(client, "generate"):
                audio = client.generate(text=text, voice=voice_id)
            else:
                raise RuntimeError("ElevenLabs client does not expose a supported generation API")

            if hasattr(audio, "content"):
                audio_bytes = audio.content
            elif isinstance(audio, (bytes, bytearray)):
                audio_bytes = bytes(audio)
            elif hasattr(audio, "read"):
                audio_bytes = audio.read()
            else:
                audio_bytes = bytes(audio)

            if not audio_bytes:
                raise RuntimeError("ElevenLabs returned no audio data")

            output_path.write_bytes(audio_bytes)
            return output_path
        except Exception as exc:
            raise RuntimeError(f"ElevenLabs TTS generation failed: {exc}") from exc


class TTSService:
    def __init__(self, cache_dir: Optional[Path] = None, default_provider: Optional[str] = None):
        base_dir = cache_dir or Path(__file__).resolve().parent / "data" / "tts_audio"
        self.cache_dir = base_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_provider = (default_provider or getattr(settings, "tts_default_provider", "edge") or "edge").lower()
        self.fallback_to_edge = bool(getattr(settings, "tts_fallback_to_edge", True))

    def get_provider(self, provider_name: Optional[str] = None) -> TTSProvider:
        resolved_name = (provider_name or self.default_provider or "edge").lower()
        if resolved_name == "elevenlabs":
            return ElevenLabsProvider(api_key=getattr(settings, "elevenlab_api_key", None))
        return EdgeTTSProvider()

    def _build_output_path(self, text: str, speaker: str, provider_name: str) -> Path:
        digest = hashlib.sha256(f"{provider_name}:{speaker}:{text}".encode("utf-8")).hexdigest()[:16]
        return self.cache_dir / f"{provider_name}-{speaker}-{digest}.mp3"

    def _build_audio_url(self, output_path: Path) -> str:
        return f"/sessions/tts/audio/{output_path.name}"

    def cleanup_old_files(self, max_age_seconds: int = 1800) -> None:
        if not self.cache_dir.exists():
            return
        cutoff = time.time() - max_age_seconds
        for path in self.cache_dir.glob("*.mp3"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink(missing_ok=True)
            except OSError:
                continue

    async def generate(self, text: str, speaker: str = "GPT", provider: Optional[str] = None) -> dict[str, object]:
        cleaned_text = (text or "").strip()
        if not cleaned_text:
            raise ValueError("Text cannot be empty")

        self.cleanup_old_files()
        resolved_provider = self.get_provider(provider)
        output_path = self._build_output_path(cleaned_text, speaker, resolved_provider.name)

        if output_path.exists() and output_path.stat().st_size > 0:
            return {
                "audio_url": self._build_audio_url(output_path),
                "provider": resolved_provider.name,
                "speaker": speaker,
                "cached": True,
            }

        try:
            await resolved_provider.generate(cleaned_text, speaker, output_path)
        except Exception as exc:
            if resolved_provider.name == "elevenlabs" and self.fallback_to_edge:
                fallback_provider = EdgeTTSProvider()
                try:
                    await fallback_provider.generate(cleaned_text, speaker, output_path)
                    return {
                        "audio_url": self._build_audio_url(output_path),
                        "provider": fallback_provider.name,
                        "speaker": speaker,
                        "cached": False,
                        "fallback": True,
                    }
                except Exception as fallback_exc:
                    raise RuntimeError(f"ElevenLabs failed and fallback failed: {exc}; {fallback_exc}") from exc
            raise RuntimeError(f"TTS generation failed: {exc}") from exc

        return {
            "audio_url": self._build_audio_url(output_path),
            "provider": resolved_provider.name,
            "speaker": speaker,
            "cached": False,
        }
