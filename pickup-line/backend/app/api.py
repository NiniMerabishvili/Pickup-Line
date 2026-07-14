from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.agent import ResearchModerator, load_interview_script
from app.agent.models import AgentResponse, TranscriptEntry
from app.stt import OpenAITranscriber, TranscriptionTimeoutError, TranscriptionUnavailableError
from app.stt.transcriber import load_local_env
from app.tts import OpenAITTSSynthesizer, TTSTimeoutError, TTSUnavailableError
from app.vacancy import generate_interview_script_from_vacancy


SCRIPT_PATH = Path(__file__).parent / "interviews" / "onboarding_feedback.json"
STATIC_DIR = Path(__file__).parent / "static"
STT_TEST_PAGE = Path(__file__).parent / "static" / "stt_test.html"


class StartInterviewResponse(BaseModel):
    session_id: str
    action: str
    text: str
    question_id: str | None
    reason: str
    is_complete: bool
    summary: dict | None


class SubmitAnswerRequest(BaseModel):
    answer: str = Field(default="", description="Participant's text answer.")
    input_quality: str = Field(
        default="clear",
        description="Quality signal from STT or UI. Use unclear for low-confidence/noisy transcription.",
    )


class VacancyInterviewRequest(BaseModel):
    vacancy_text: str = Field(default="")
    role_title: str | None = None


class ModeratorResponse(BaseModel):
    session_id: str
    action: str
    text: str
    question_id: str | None
    reason: str
    is_complete: bool
    summary: dict | None
    failure_mode: str | None = None


class TranscriptResponse(BaseModel):
    session_id: str
    transcript: list[dict]


class SummaryResponse(BaseModel):
    session_id: str
    summary: dict | None


class TTSRequest(BaseModel):
    text: str = Field(default="")


app = FastAPI(
    title="Mini Research Moderator API",
    description="Backend API for testing the stateful research moderator with text and push-to-talk STT.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

_sessions: dict[str, ResearchModerator] = {}
_transcriber = OpenAITranscriber()
_synthesizer = OpenAITTSSynthesizer()


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config")
def get_config() -> dict[str, str | bool]:
    load_local_env()
    return {
        "openai_api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
        "transcribe_model": os.getenv("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-transcribe"),
        "tts_model": os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
        "tts_voice": os.getenv("OPENAI_TTS_VOICE", "coral"),
    }


@app.get("/stt-test", include_in_schema=False)
def stt_test_page() -> FileResponse:
    return FileResponse(STT_TEST_PAGE)


@app.post("/api/interviews/start", response_model=StartInterviewResponse)
def start_interview() -> StartInterviewResponse:
    script = load_interview_script(SCRIPT_PATH)
    moderator = ResearchModerator(script)
    response = moderator.start()
    session_id = str(uuid4())
    _sessions[session_id] = moderator

    return StartInterviewResponse(session_id=session_id, **_response_payload(response))


@app.post("/api/interviews/start-from-vacancy", response_model=StartInterviewResponse)
def start_interview_from_vacancy(request: VacancyInterviewRequest) -> StartInterviewResponse:
    vacancy_text = request.vacancy_text.strip()
    role_title = request.role_title.strip() if request.role_title else None

    if len(vacancy_text) < 80:
        raise HTTPException(status_code=400, detail="Paste at least 80 characters of vacancy text.")
    if len(vacancy_text) > 20000:
        raise HTTPException(status_code=400, detail="Vacancy text is too long. Keep it under 20,000 characters.")
    if role_title and len(role_title) > 120:
        role_title = role_title[:120]

    try:
        script = generate_interview_script_from_vacancy(vacancy_text, role_title)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    moderator = ResearchModerator(script)
    response = moderator.start()
    session_id = str(uuid4())
    _sessions[session_id] = moderator

    return StartInterviewResponse(session_id=session_id, **_response_payload(response))


@app.post("/api/interviews/{session_id}/answer", response_model=ModeratorResponse)
def submit_answer(session_id: str, request: SubmitAnswerRequest) -> ModeratorResponse:
    moderator = _get_session(session_id)
    input_quality = request.input_quality if request.input_quality in {"clear", "empty", "unclear"} else "clear"
    response = moderator.submit_answer(request.answer, input_quality=input_quality)

    return ModeratorResponse(session_id=session_id, **_response_payload(response))


@app.get("/api/interviews/{session_id}/transcript", response_model=TranscriptResponse)
def get_transcript(session_id: str) -> TranscriptResponse:
    moderator = _get_session(session_id)
    return TranscriptResponse(
        session_id=session_id,
        transcript=[_transcript_payload(entry) for entry in moderator.transcript()],
    )


@app.get("/api/interviews/{session_id}/summary", response_model=SummaryResponse)
def get_summary(session_id: str) -> SummaryResponse:
    moderator = _get_session(session_id)
    return SummaryResponse(session_id=session_id, summary=moderator.state.summary)


@app.post("/api/tts")
def synthesize_speech(request: TTSRequest) -> Response:
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is required for TTS.")
    if len(text) > 4000:
        raise HTTPException(status_code=400, detail="TTS text is too long. Keep it under 4,000 characters.")

    try:
        result = _synthesizer.synthesize(text)
    except TTSTimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail={
                "error": "tts_timeout",
                "message": str(exc),
                "hint": "Try shorter text or use browser TTS fallback.",
            },
        ) from exc
    except TTSUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "tts_unavailable",
                "message": str(exc),
                "hint": "Set OPENAI_API_KEY or use browser TTS fallback.",
            },
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "tts_error",
                "message": str(exc),
                "hint": "Check quota/billing or use browser TTS fallback.",
            },
        ) from exc

    media_type = "audio/mpeg" if result.response_format == "mp3" else f"audio/{result.response_format}"
    return Response(
        content=result.audio_bytes,
        media_type=media_type,
        headers={
            "X-TTS-Model": result.model,
            "X-TTS-Voice": result.voice,
        },
    )


@app.websocket("/ws/interviews/{session_id}/audio")
async def interview_audio_socket(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()

    moderator = _sessions.get(session_id)
    if moderator is None:
        await websocket.send_json({"event": "error", "detail": "Interview session not found."})
        await websocket.close(code=1008)
        return

    audio_buffer = bytearray()
    mime_type = "audio/webm"

    await websocket.send_json(
        {
            "event": "ready",
            "session_id": session_id,
            "message": "Send binary audio chunks, then send {'event':'stop'} to transcribe.",
        }
    )

    try:
        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                return

            if message.get("bytes") is not None:
                audio_buffer.extend(message["bytes"])
                await websocket.send_json(
                    {
                        "event": "chunk_received",
                        "bytes_buffered": len(audio_buffer),
                    }
                )
                continue

            text_message = message.get("text")
            if text_message is None:
                continue

            command = _parse_websocket_command(text_message)
            event = command.get("event")

            if event == "start":
                audio_buffer.clear()
                mime_type = command.get("mime_type", mime_type)
                await websocket.send_json({"event": "recording_started"})
                continue

            if event == "stop":
                mime_type = command.get("mime_type", mime_type)
                filename = _filename_for_mime_type(mime_type)
                await _transcribe_and_answer(websocket, moderator, bytes(audio_buffer), filename)
                audio_buffer.clear()
                continue

            if event == "clear":
                audio_buffer.clear()
                await websocket.send_json({"event": "buffer_cleared"})
                continue

            await websocket.send_json(
                {
                    "event": "error",
                    "detail": "Unknown command. Use start, stop, or clear.",
                }
            )
    except WebSocketDisconnect:
        return


def _get_session(session_id: str) -> ResearchModerator:
    moderator = _sessions.get(session_id)
    if moderator is None:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    return moderator


def _response_payload(response: AgentResponse) -> dict:
    return {
        "action": response.action,
        "text": response.text,
        "question_id": response.question_id,
        "reason": response.reason,
        "is_complete": response.is_complete,
        "summary": response.summary,
        "failure_mode": response.failure_mode,
    }


def _transcript_payload(entry: TranscriptEntry) -> dict:
    return {
        "role": entry.role,
        "text": entry.text,
        "question_id": entry.question_id,
        "kind": entry.kind,
        "turn_index": entry.turn_index,
        "timestamp": _format_timestamp(entry.elapsed_seconds),
        "elapsed_seconds": entry.elapsed_seconds,
        "created_at": entry.created_at,
    }


def _format_timestamp(elapsed_seconds: float) -> str:
    total_seconds = max(0, int(round(elapsed_seconds)))
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


async def _transcribe_and_answer(
    websocket: WebSocket,
    moderator: ResearchModerator,
    audio_bytes: bytes,
    filename: str,
) -> None:
    if not audio_bytes:
        response = moderator.submit_answer("")
        await websocket.send_json(
            {
                "event": "moderator_response",
                "transcript": "",
                **_response_payload(response),
            }
        )
        return

    await websocket.send_json({"event": "transcribing", "bytes_buffered": len(audio_bytes)})

    try:
        transcription = _transcriber.transcribe(audio_bytes, filename=filename)
    except TranscriptionTimeoutError as exc:
        await websocket.send_json(
            {
                "event": "transcription_timeout",
                "detail": str(exc),
                "hint": "Try a shorter recording, check your API key/billing, then record again.",
            }
        )
        return
    except TranscriptionUnavailableError as exc:
        await websocket.send_json(
            {
                "event": "transcription_unavailable",
                "detail": str(exc),
                "hint": "Set OPENAI_API_KEY and install requirements to enable live STT.",
            }
        )
        return
    except Exception as exc:
        await websocket.send_json(
            {
                "event": "transcription_error",
                "detail": str(exc),
                "hint": "Check the backend terminal for API/auth/network details.",
            }
        )
        return

    response = moderator.submit_answer(transcription.text)
    await websocket.send_json(
        {
            "event": "moderator_response",
            "transcript": transcription.text,
            "transcription_model": transcription.model,
            **_response_payload(response),
        }
    )


def _parse_websocket_command(text: str) -> dict[str, str]:
    import json

    try:
        command = json.loads(text)
    except json.JSONDecodeError:
        return {"event": text}

    if not isinstance(command, dict):
        return {"event": "unknown"}

    return {str(key): str(value) for key, value in command.items()}


def _filename_for_mime_type(mime_type: str) -> str:
    if "wav" in mime_type:
        return "participant_audio.wav"
    if "mpeg" in mime_type or "mp3" in mime_type:
        return "participant_audio.mp3"
    if "mp4" in mime_type:
        return "participant_audio.mp4"
    return "participant_audio.webm"
