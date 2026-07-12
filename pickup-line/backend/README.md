# Mini Research Moderator Backend

This backend starts with the text-only agent loop from the project prompt. Audio, STT, TTS, and WebSockets should be added only after this loop is reliable.

## Current Scope

- Loads a structured interview script from JSON.
- Generates a mock interview script from pasted vacancy text.
- Tracks current question index, transcript history, follow-up counts, and completion state.
- Exposes tool-style moderator actions:
  - `ask_followup(reason)`
  - `move_to_next_question()`
  - `end_interview(summary)`
- Uses a local deterministic decision maker for repeatable testing.
- Generates a structured summary at the end of the interview.
- Shows a wrap-up summary with coverage, key points by question, timestamped notable quotes, and flagged themes.
- Handles empty/silent responses as an explicit failure mode.
- Handles unclear/noisy transcription as an explicit failure mode.
- Accepts push-to-talk audio chunks over WebSocket and transcribes them before feeding the text into the moderator.
- Shows a talking interviewer avatar with mouth-state animation while the moderator speaks.

## Run Text Demo

From `backend`:

```bash
python -m app.text_chat
```

## Run Tests

From `backend`:

```bash
python -m unittest discover tests
```

## Run Backend API

Install dependencies first:

```powershell
& "C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pip install -r requirements.txt
```

Create a local `.env` file for API keys:

```powershell
Copy-Item .env.example .env
```

Then edit `.env`:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_TRANSCRIBE_MODEL=gpt-4o-transcribe
OPENAI_TRANSCRIBE_TIMEOUT_SECONDS=30
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=coral
OPENAI_TTS_FORMAT=mp3
OPENAI_TTS_TIMEOUT_SECONDS=30
```

Start the API:

```powershell
.\run_backend.ps1
```

If PowerShell blocks local scripts, use:

```powershell
powershell -ExecutionPolicy Bypass -File ".\run_backend.ps1"
```

Or run it directly:

```powershell
& "C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m uvicorn app.api:app --reload --host 127.0.0.1 --port 8000
```

Open the interactive API docs:

```text
http://127.0.0.1:8000/docs
```

Open the push-to-talk STT test page:

```text
http://127.0.0.1:8000/stt-test
```

If the OpenAI API returns quota errors, use the `Use Browser Speech` button on
the same page. It uses the browser's speech recognition when available and sends
the recognized text into the same moderator backend.

If browser speech recognition returns a `network` error, use `Send Typed Answer`.
This keeps the same moderator flow without relying on the browser speech service.

Useful test endpoints:

- `GET /health`
- `POST /api/interviews/start`
- `POST /api/interviews/start-from-vacancy`
- `POST /api/interviews/{session_id}/answer`
- `GET /api/interviews/{session_id}/transcript`
- `GET /api/interviews/{session_id}/summary`
- `POST /api/tts`
- `WS /ws/interviews/{session_id}/audio`

Example PowerShell flow after the server is running:

```powershell
$start = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/interviews/start"
$start

$answer = Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/interviews/$($start.session_id)/answer" `
  -ContentType "application/json" `
  -Body '{"answer":"Good."}'
$answer
```

## Test Speech-to-Text WebSocket

Set an OpenAI API key before testing live STT:

```powershell
$env:OPENAI_API_KEY = "your_api_key_here"
```

The WebSocket accepts push-to-talk style audio:

1. Start an interview with `POST /api/interviews/start`.
2. Connect to `ws://127.0.0.1:8000/ws/interviews/{session_id}/audio`.
3. Send binary audio chunks from the browser.
4. Send `{"event":"stop","mime_type":"audio/webm"}` when the user releases the talk button.
5. The server transcribes the buffered audio and returns a `moderator_response` event.

The STT adapter defaults to `gpt-4o-transcribe`. Set `OPENAI_TRANSCRIBE_MODEL=whisper-1` if you specifically want Whisper API compatibility for the demo.

## Free STT Fallback

The fastest free fallback is browser speech recognition:

1. Open `http://127.0.0.1:8000/stt-test` in Chrome or Edge.
2. Click `Start Interview`.
3. Click `Use Browser Speech`.
4. Speak your answer.
5. The browser transcript is sent to `POST /api/interviews/{session_id}/answer`.

This keeps the agent loop working even when OpenAI quota is unavailable.

## Test Text-to-Speech

The test page has a `Speak replies` checkbox and a speech mode selector:

- `Browser TTS`: free fallback using built-in browser speech synthesis.
- `OpenAI TTS`: calls `POST /api/tts`, then plays the returned audio.

Because OpenAI quota can fail independently for STT and TTS, the page falls back
to browser TTS if the OpenAI TTS request fails.

The avatar uses Web Audio amplitude analysis for real audio elements from
`POST /api/tts`. Browser TTS does not expose raw audio samples, so the page uses
a timed mouth animation fallback while speech synthesis is active.

## Wrap-Up Summary

At the end of the final scripted question, the moderator returns `end_interview`
with a structured summary:

- `one_sentence_overall_summary`
- `coverage`
- `key_points_by_question`
- `notable_quotes` with timestamps and turn indexes
- `flagged_themes` with severity and evidence
- `unanswered_or_unclear_items`

The browser test page renders this summary below the transcript when the
interview is complete.

## Explicit Failure Mode

The demo intentionally handles unreliable participant input instead of silently
moving forward:

- Silent or empty response: the moderator asks once for the participant to say a
  little about what stood out.
- Unclear or noisy transcription: the moderator asks once for the participant to
  repeat the main point in one sentence.
- If the same failure happens again for the same question, the moderator moves
  on to avoid looping.

The browser test page includes `Simulate Unclear Input` so reviewers can trigger
this behavior without needing actual background noise.

## Next Prompt Step

Next, record a short end-to-end walkthrough and add the video link to the top-level README.
