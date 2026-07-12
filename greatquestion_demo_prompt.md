## PROMPT B — Realtime Agentic Moderator (ალტერნატივა, უფრო მაღალი რისკის)

Maps to Great Question's challenge #2 (realtime agentic AI moderator — TTS, STT, vision awareness). 

```
I'm building a portfolio demo project for an AI Engineer internship application.
The target company builds AI tools for running live user-research interviews, and
one of their stated challenges is a "realtime agentic AI moderator" that uses
text-to-speech, speech-to-text, and vision awareness. I want a small but REAL
working prototype of a simplified version of this, not a mockup.

PROJECT: "Mini Research Moderator" — a voice-based AI agent that conducts a short
structured interview with a person, asks adaptive follow-up questions based on
their answers, and produces a summary at the end.

TECH STACK:
- STT: OpenAI Whisper API (or a local whisper.cpp if latency needs testing)
- TTS: ElevenLabs API or OpenAI TTS (pick whichever has simplest free-tier setup)
- LLM/agent logic: Claude API or Gemini API, function-calling for structured
  question flow
- Backend: Python, FastAPI, WebSocket connection for streaming audio in/out
- Frontend: minimal React page: a single "start interview" button, live
  transcript display, audio playback of the agent's questions
- Skip vision/webcam awareness for v1 — scope it out explicitly as "future work"
  in the README rather than attempting it half-working; STT+TTS+agent logic
  alone is already a full scope for a short timeline.

STEP-BY-STEP BUILD PLAN:

1. Define the interview script structure
   - A small JSON config: interview topic (e.g., "feedback on a fictional
     product's onboarding flow"), 3-4 core scripted questions, and rules for
     when to ask a follow-up vs move on (e.g., if the answer is under 10 words
     or vague, ask one clarifying follow-up before moving to the next question).

2. Backend agent loop (this is the core of the project — build this first,
   test it with TEXT input/output before adding voice)
   - Implement the moderator as a stateful agent: current question index,
     conversation history, a function/tool the LLM can call: ask_followup(reason),
     move_to_next_question(), end_interview(summary).
   - Test this thoroughly as a text-only chat loop first. Do not add audio until
     the text-based agent logic reliably asks sensible follow-ups and doesn't
     loop infinitely or repeat questions.

3. Add STT (speech-to-text)
   - WebSocket endpoint that accepts streamed audio chunks from the browser,
     buffers them, sends to Whisper API when the user stops speaking (simple
     silence detection or push-to-talk button — push-to-talk is more reliable
     for a demo, use that instead of automatic voice-activity-detection unless
     there's time to tune it).
   - Transcribe and feed the text into the agent loop from step 2.

4. Add TTS (text-to-speech)
   - When the agent generates its next question/follow-up, send text to the
     TTS API, stream or return the audio, play it in the frontend.
   - Show the text transcript on screen alongside the audio, so the demo is
     watchable even without sound.

5. Wrap-up + summary generation
   - At the end of the scripted questions, have the agent generate a short
     structured summary: key points per question, notable quotes with
     timestamps, and any flagged themes. This mirrors what Great Question's
     actual product likely needs to output.

6. Handle at least one realistic failure mode explicitly
   - E.g., user gives a silent/empty response, or background noise garbles
     the transcript — show that the agent asks for clarification rather than
     proceeding on bad data, and document this in the README as an
     intentional design decision.

7. README
   - Explain what's implemented vs explicitly out of scope (vision/webcam
     awareness — note this as a clear "next step" so it reads as a scoping
     decision, not a gap I didn't notice).
   - Include a 2-3 minute screen-recording link/video of an actual interview
     session start to finish — for this project, a video walkthrough is
     strongly preferred over asking a reviewer to run it locally, since
     audio/mic permissions and API keys make local setup friction-heavy.

SUCCESS CRITERIA FOR ME TO CHECK BEFORE SUBMITTING:
- The full loop (speak -> transcribe -> agent decides -> speaks back) actually
  works end-to-end at least 5 times in a row without breaking.
- The agent asks at least one genuinely adaptive follow-up question that
  wasn't in the scripted list, driven by a real previous answer.
- I have a clean video recording as a fallback, since live voice demos are
  the most likely thing to fail during actual review.

Build and test incrementally: text-only agent logic first (fully working before
touching audio), then STT, then TTS, then the wrap-up summary. Do not move to the
next piece until the previous one is reliable — a working three-step pipeline beats
a broken five-step one.
```


