# Mini Research Moderator

A voice-enabled prototype of a realtime agentic AI research moderator, built as a portfolio demo for an AI Engineer internship application.

The system runs a short, structured user-research interview: it asks adaptive follow-up questions, speaks its replies aloud, and produces a wrap-up summary with key points, timestamped quotes, and flagged themes. It also supports a **vacancy-driven mock interview mode** — paste in a job posting and the system generates likely interview questions from the role's requirements, then runs the same voice interview flow against them.

The project is deliberately scoped as a small but real slice of a larger realtime agentic moderator: it proves out the **STT → agent decision → TTS** loop end to end before layering on larger product features.

## Demo Video

Screen recording: `TODO: add 2–3 minute walkthrough link`

Suggested recording flow:

1. Start the backend and open `http://127.0.0.1:8000/stt-test`.
2. Paste an AI Engineer vacancy and click **Generate Mock Interview**, or click **Start Default Interview**.
3. Answer the first question with something short and vague (e.g. "Good") to trigger an adaptive follow-up.
4. Use **Use Browser Speech**, **Send Typed Answer**, or **Hold to Record** (when OpenAI quota is available).
5. Click **Simulate Unclear Input** to demonstrate explicit failure handling.
6. Complete the generated interview.
7. Show the final summary panel with themes, quotes, and key points.

## What's Implemented

- Structured interview script loaded from JSON
- Vacancy-driven mock interview generation from pasted job descriptions
- A stateful moderator agent with:
  - current question tracking
  - full transcript history
  - follow-up limits (to avoid infinite loops)
  - explicit `ask_followup`, `move_to_next_question`, and `end_interview` actions
- Push-to-talk STT WebSocket endpoint
- OpenAI transcription adapter with quota and error handling
- Free browser speech-recognition fallback
- Typed-answer fallback when browser speech recognition is unavailable or blocked
- OpenAI TTS endpoint, with a free browser TTS fallback
- An animated interviewer avatar (mouth-state animation, blinking, listening/speaking status)
- A final structured summary covering:
  - question coverage
  - key points per question
  - timestamped notable quotes
  - flagged themes with supporting evidence
  - unanswered or unclear items
- Explicit failure handling for silent and unclear/noisy input
- FastAPI-generated API docs and an automated test suite

## Out of Scope for v1

These are deliberate boundaries, not omissions — the loop above is already enough surface area for a first demo:

- Vision or webcam awareness
- Full realtime duplex speech-to-speech
- Production authentication, persistence, or multi-user session storage
- A polished frontend — the current UI is a lightweight browser test page served by FastAPI, chosen to keep the voice loop testable quickly
- LLM-based function calling — the current decision maker is deterministic and fully testable, and is designed so a Claude/Gemini/OpenAI function-calling adapter can drop in later without changing the moderator's state machine

## Architecture

```text
Browser test page
  → speech input
  → FastAPI WebSocket / HTTP API
  → STT adapter
  → ResearchModerator state machine
  → TTS adapter
  → transcript + spoken moderator reply
  → final summary
```

### Key Files

| File | Purpose |
|---|---|
| `backend/app/interviews/onboarding_feedback.json` | Interview script |
| `backend/app/vacancy/generator.py` | Vacancy-to-question generator |
| `backend/app/agent/moderator.py` | Stateful moderator loop |
| `backend/app/agent/decision.py` | Adaptive follow-up decision logic |
| `backend/app/agent/summary.py` | Wrap-up summary generation |
| `backend/app/stt/transcriber.py` | OpenAI STT adapter |
| `backend/app/tts/synthesizer.py` | OpenAI TTS adapter |
| `backend/app/api.py` | FastAPI routes and WebSocket |
| `backend/app/static/stt_test.html` | Browser demo page |
| `backend/app/static/avatar/*.svg` | Local illustrated avatar frames |

## Quickstart

From the project root:

```powershell
cd "D:\Nini\ai engineer samsaxurii\GreatQuestion\pickup-line\mini-research-moderator\backend"
```

Install dependencies:

```powershell
& "C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pip install -r requirements.txt
```

Create a local environment config:

```powershell
Copy-Item .env.example .env
notepad .env
```

Optional OpenAI configuration:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_TRANSCRIBE_MODEL=gpt-4o-transcribe
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=coral
```

> OpenAI quota is optional for the local demo — the browser page ships with free STT and TTS fallbacks.

Start the backend:

```powershell
cd "D:\Nini\ai engineer samsaxurii\GreatQuestion\pickup-line"
powershell -ExecutionPolicy Bypass -File ".\mini-research-moderator\backend\run_backend.ps1"
```

Open the demo:

```text
http://127.0.0.1:8000/stt-test
```

For vacancy mode, paste a job posting into the **Vacancy Mode** panel and click **Generate Mock Interview**.

Open the API docs:

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

The moderator never blindly proceeds on unreliable input:

- **Empty or silent response** → asks once for clarification
- **Unclear or noisy transcription** → asks once for the participant to repeat the main point
- **Repeated failure on the same question** → moves on, to avoid an infinite loop

The browser page includes a **Simulate Unclear Input** control so this behavior can be demonstrated reliably on camera.

## Current Limitations

- In-memory sessions reset when the backend restarts
- Browser speech recognition depends on Chrome/Edge support, and can fail with network or privacy errors — typed answers keep the demo unblocked in that case
- Browser TTS doesn't expose an audio stream, so avatar mouth movement falls back to a timed animation there; OpenAI TTS audio uses amplitude analysis instead
- OpenAI STT/TTS require API quota and billing
- The adaptive decision maker is deterministic rather than LLM-powered
- Vacancy question generation is deterministic and quota-free in this version
- The browser page is a demo harness, not a production UI

## Next Steps

1. Add a React frontend around the existing FastAPI API
2. Add a provider-backed vacancy question generator and a function-calling decision maker
3. Add persistent interview records
4. Add optional local Whisper STT for offline transcription
5. Add vision awareness as a separate v2 feature
