"""Text-to-speech adapters."""

from app.tts.synthesizer import (
    OpenAITTSSynthesizer,
    TTSResult,
    TTSTimeoutError,
    TTSUnavailableError,
)

__all__ = [
    "OpenAITTSSynthesizer",
    "TTSResult",
    "TTSTimeoutError",
    "TTSUnavailableError",
]
