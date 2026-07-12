# Interview Script Structure

The first demo interview lives in `backend/app/interviews/onboarding_feedback.json`.

The script is designed to be consumed by a stateful moderator agent. It separates the fixed research plan from the adaptive behavior so the agent can ask scripted questions while still making local decisions about follow-ups.

## Main Sections

- `topic`: describes the fictional product, scenario, and research goal.
- `moderator`: defines the moderator's tone and start/end messages.
- `core_questions`: contains the ordered interview questions, their research intent, and hints for useful follow-ups.
- `followup_policy`: defines when the agent should ask a follow-up or move to the next scripted question.
- `failure_handling`: defines what to do for silent, unclear, or off-topic responses.
- `summary_requirements`: defines the expected output at the end of the interview.

## V1 Agent Rules

- Ask the opening message first.
- Ask each `core_questions` item in ascending `order`.
- After each participant answer, decide whether to ask one follow-up or move on.
- Ask no more than one follow-up per core question.
- End the interview after the final question and generate a structured summary.
- Treat vision awareness as future work, not part of this script.

## Agent Loop Implementation

The text-only agent loop lives in `backend/app/agent`.

- `ResearchModerator.start()` begins the interview and asks the first scripted question.
- `ResearchModerator.submit_answer(answer)` records participant text and returns the next moderator response.
- `ask_followup(reason)`, `move_to_next_question()`, and `end_interview(summary)` are implemented as tool-style actions.
- `RuleBasedDecisionMaker` provides deterministic local behavior for testing. A Claude or Gemini function-calling adapter can replace it later without changing the moderator state machine.
