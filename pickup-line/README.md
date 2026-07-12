# Mini Research Moderator

Mini Research Moderator is a voice-enabled portfolio demo for an AI Engineer internship application. It conducts a short structured user-research interview, asks adaptive follow-up questions, speaks moderator replies, and generates a wrap-up summary with key points, timestamped quotes, and flagged themes.

The demo is intentionally scoped as a small but real prototype of a realtime agentic AI moderator. It focuses on the STT -> agent decision -> TTS loop before adding larger product features.

It also includes a vacancy-driven mock interview mode: paste a job vacancy, generate likely interview questions from the role requirements, then run the same voice-based interview flow.

## Demo Video

Screen recording: `TODO: add 2-3 minute walkthrough link`

Recommended recording flow:

1. Start the backend and open `http://127.0.0.1:8000/stt-test`.
2. Paste an AI Engineer vacancy and click `Generate Mock Interview`, or click `Start Default Interview`.
3. Answer the first question with a short vague answer like `Good` to trigger an adaptive follow-up.
4. Use `Use Browser Speech`, `Send Typed Answer`, or `Hold To Record` when OpenAI quota is available.
5. Click `Simulate Unclear Input` to show explicit failure handling.
6. Complete the generated interview.
7. Show the final summary panel with themes, quotes, and key points.

## What Is Implemented

- Structured interview script loaded from JSON.
- Vacancy-driven mock interview generation from pasted job descriptions.
- Stateful moderator agent with:
  - current question tracking
  - transcript history
  - follow-up limits
  - explicit `ask_followup`, `move_to_next_question`, and `end_interview` actions
- Push-to-talk STT WebSocket endpoint.
- OpenAI transcription adapter with quota/error handling.
- Free browser speech-recognition fallback.
- Typed answer fallback when browser speech recognition is blocked.
- OpenAI TTS endpoint.
- Free browser TTS fallback.
- Talking interviewer avatar with mouth-state animation, blink, and listening/speaking status.
- Final structured summary:
  - coverage
  - key points by question
  - timestamped notable quotes
  - flagged themes with evidence
  - unanswered or unclear items
- Explicit failure handling for silent and unclear/noisy input.
- FastAPI docs and automated tests.

## Explicitly Out Of Scope For V1

- Vision or webcam awareness.
- Full realtime duplex speech-to-speech.
- Production authentication, persistence, or multi-user session storage.
- A polished React frontend. The current UI is a lightweight browser test page served by FastAPI so the voice loop can be tested quickly.
- LLM provider function-calling. The current decision maker is deterministic and testable; it is designed so a Claude/Gemini/OpenAI function-calling adapter can replace it later without changing the moderator state machine.

Vision awareness is a clear next step, not an accidental omission. STT, TTS, agent state, failure handling, and summary generation are already enough scope for the first demo.

## Architecture

```text
Browser test page
  -> speech input
  -> FastAPI WebSocket / HTTP API
  -> STT adapter
  -> ResearchModerator state machine
  -> TTS adapter
  -> transcript + spoken moderator reply
  -> final summary
```

Important files:

- `backend/app/interviews/onboarding_feedback.json` - interview script
- `backend/app/vacancy/generator.py` - vacancy-to-question generator
- `backend/app/agent/moderator.py` - stateful moderator loop
- `backend/app/agent/decision.py` - adaptive follow-up decision logic
- `backend/app/agent/summary.py` - wrap-up summary generation
- `backend/app/stt/transcriber.py` - OpenAI STT adapter
- `backend/app/tts/synthesizer.py` - OpenAI TTS adapter
- `backend/app/api.py` - FastAPI routes and WebSocket
- `backend/app/static/stt_test.html` - browser demo page
- `backend/app/static/avatar/*.svg` - local illustrated avatar frames

## Quickstart

From the project root:

```powershell
cd "D:\Nini\ai engineer samsaxurii\GreatQuestion\pickup-line\mini-research-moderator\backend"
```

Install dependencies:

```powershell
& "C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pip install -r requirements.txt
```

Create local environment config:

```powershell
Copy-Item .env.example .env
notepad .env
```

Optional OpenAI config:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_TRANSCRIBE_MODEL=gpt-4o-transcribe
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=coral
```

OpenAI quota is optional for the local demo because the browser page includes free STT and TTS fallbacks.

Start the backend:

```powershell
cd "D:\Nini\ai engineer samsaxurii\GreatQuestion\pickup-line"
powershell -ExecutionPolicy Bypass -File ".\mini-research-moderator\backend\run_backend.ps1"
```

Open the demo:

```text
http://127.0.0.1:8000/stt-test
```

To use vacancy mode, paste a job post into the `Vacancy Mode` panel and click
`Generate Mock Interview`.

Open API docs:

```text
http://127.0.0.1:8000/docs
```

## Testing

From `backend`:

```powershell
& "C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest discover tests
```

Expected result:

```text
Ran 15 tests
OK
```

## Failure Mode Design

The moderator does not blindly proceed on unreliable input.

- Empty or silent response: asks once for clarification.
- Unclear or noisy transcription: asks once for the participant to repeat the main point.
- Repeated failure on the same question: moves on to avoid an infinite loop.

The browser page includes `Simulate Unclear Input` so this can be demonstrated reliably in a recording.

## Current Limitations

- In-memory sessions reset when the backend restarts.
- Browser speech recognition depends on Chrome/Edge support.
- Browser speech recognition can fail with network/privacy errors; typed answers keep the demo unblocked.
- Browser TTS does not expose an audio stream, so avatar mouth movement uses a timed fallback there. OpenAI TTS audio uses amplitude analysis.
- OpenAI STT/TTS require quota and billing.
- The current adaptive decision maker is deterministic rather than LLM-powered.
- Vacancy question generation is deterministic and quota-free in this version.
- The browser page is a demo harness, not a production UI.

## Next Steps

1. Add a React frontend around the existing FastAPI API.
2. Add a provider-backed vacancy question generator and function-calling decision maker.
3. Add persistent interview records.
4. Add optional local Whisper STT for offline transcription.
5. Add vision awareness as a separate v2 feature.
