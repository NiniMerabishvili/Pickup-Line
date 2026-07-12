from __future__ import annotations

import io
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def load_local_env() -> None:
    """Load backend/.env when present, while still allowing real env vars to win."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    load_dotenv(BACKEND_ROOT / ".env", override=False)


class TranscriptionUnavailableError(RuntimeError):
    """Raised when live transcription cannot run in the current environment."""


class TranscriptionTimeoutError(RuntimeError):
    """Raised when the transcription request takes too long for the demo."""


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    model: str
    duration_hint_seconds: float | None = None


class OpenAITranscriber:
    """OpenAI audio transcription adapter.

    The project prompt mentions Whisper API. OpenAI's current speech-to-text docs
    support `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`, and `whisper-1`.
    The default here uses the current higher-quality transcription model while
    leaving the model configurable for Whisper compatibility.
    """

    def __init__(self, model: str | None = None) -> None:
        load_local_env()
        self.model = model or os.getenv("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-transcribe")
        self.timeout_seconds = float(os.getenv("OPENAI_TRANSCRIBE_TIMEOUT_SECONDS", "30"))

    def transcribe(self, audio_bytes: bytes, filename: str = "participant_audio.webm") -> TranscriptionResult:
        if not audio_bytes:
            return TranscriptionResult(text="", model=self.model)

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise TranscriptionUnavailableError("OPENAI_API_KEY is not set.")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise TranscriptionUnavailableError("The openai package is not installed.") from exc

        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = filename

        client = OpenAI(api_key=api_key, timeout=self.timeout_seconds)
        transcription = _run_with_timeout(
            lambda: client.audio.transcriptions.create(
                model=self.model,
                file=audio_file,
            ),
            timeout_seconds=self.timeout_seconds + 5,
        )

        text = getattr(transcription, "text", "")
        return TranscriptionResult(text=text.strip(), model=self.model)


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
        raise TranscriptionTimeoutError(
            f"Transcription timed out after {timeout_seconds:.0f} seconds."
        )

    if "error" in result:
        raise result["error"]

    return result.get("value")
