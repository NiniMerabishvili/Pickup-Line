"""Speech-to-text adapters."""

from app.stt.transcriber import (
    OpenAITranscriber,
    TranscriptionResult,
    TranscriptionTimeoutError,
    TranscriptionUnavailableError,
)

__all__ = [
    "OpenAITranscriber",
    "TranscriptionResult",
    "TranscriptionTimeoutError",
    "TranscriptionUnavailableError",
]
