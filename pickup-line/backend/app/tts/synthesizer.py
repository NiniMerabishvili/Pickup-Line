from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Any

from app.stt.transcriber import load_local_env


class TTSUnavailableError(RuntimeError):
    """Raised when TTS cannot run in the current environment."""


class TTSTimeoutError(RuntimeError):
    """Raised when TTS takes too long for the demo."""


@dataclass(frozen=True)
class TTSResult:
    audio_bytes: bytes
    model: str
    voice: str
    response_format: str


class OpenAITTSSynthesizer:
    """OpenAI text-to-speech adapter for moderator responses."""

    def __init__(
        self,
        model: str | None = None,
        voice: str | None = None,
        response_format: str | None = None,
    ) -> None:
        load_local_env()
        self.model = model or os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
        self.voice = voice or os.getenv("OPENAI_TTS_VOICE", "coral")
        self.response_format = response_format or os.getenv("OPENAI_TTS_FORMAT", "mp3")
        self.timeout_seconds = float(os.getenv("OPENAI_TTS_TIMEOUT_SECONDS", "30"))
        self.instructions = os.getenv(
            "OPENAI_TTS_INSTRUCTIONS",
            "Speak like a warm, concise, neutral user research moderator.",
        )

    def synthesize(self, text: str) -> TTSResult:
        cleaned_text = " ".join(text.strip().split())
        if not cleaned_text:
            return TTSResult(
                audio_bytes=b"",
                model=self.model,
                voice=self.voice,
                response_format=self.response_format,
            )

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise TTSUnavailableError("OPENAI_API_KEY is not set.")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise TTSUnavailableError("The openai package is not installed.") from exc

        client = OpenAI(api_key=api_key, timeout=self.timeout_seconds)
        response = _run_with_timeout(
            lambda: client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=cleaned_text,
                instructions=self.instructions,
                response_format=self.response_format,
            ),
            timeout_seconds=self.timeout_seconds + 5,
        )

        audio_bytes = _read_audio_bytes(response)
        return TTSResult(
            audio_bytes=audio_bytes,
            model=self.model,
            voice=self.voice,
            response_format=self.response_format,
        )


def _read_audio_bytes(response: Any) -> bytes:
    if hasattr(response, "read"):
        return response.read()
    if hasattr(response, "content"):
        return response.content
    if isinstance(response, bytes):
        return response
    raise TTSUnavailableError("OpenAI TTS response did not contain readable audio bytes.")


def _run_with_timeout(operation: Any, timeout_seconds: float) -> Any:
    result: dict[str, Any] = {}

    def target() -> None:
        try:
            result["value"] = operation()
        except Exception as exc:  # pragma: no cover - exact SDK exceptions vary.
            result["error"] = exc

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout_seconds)

    if thread.is_alive():
        raise TTSTimeoutError(f"TTS timed out after {timeout_seconds:.0f} seconds.")

    if "error" in result:
        raise result["error"]

    return result.get("value")
