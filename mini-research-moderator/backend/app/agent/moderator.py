from __future__ import annotations

from datetime import datetime, timezone

from app.agent.decision import DecisionMaker, RuleBasedDecisionMaker
from app.agent.models import AgentResponse, InputQuality, InterviewQuestion, InterviewScript, InterviewState, TranscriptEntry
from app.agent.summary import build_summary


class ResearchModerator:
    """Stateful text-only moderator loop.

    This is the core agent layer from the project prompt. Voice, WebSockets, STT,
    and TTS should call into this class after the text loop is reliable.
    """

    def __init__(
        self,
        script: InterviewScript,
        decision_maker: DecisionMaker | None = None,
    ) -> None:
        if not script.core_questions:
            raise ValueError("Interview script must define at least one core question.")

        self.script = script
        self.decision_maker = decision_maker or RuleBasedDecisionMaker()
        self.state = InterviewState()

    def start(self) -> AgentResponse:
        if self.state.status != "not_started":
            raise RuntimeError("Interview has already started.")

        self.state.status = "in_progress"
        self.state.started_at = datetime.now(timezone.utc)
        first_question = self._current_question()
        self.state.pending_question_id = first_question.id

        opening_text = f"{self.script.moderator.opening_message}\n\n{first_question.question}"
        self._record_moderator(self.script.moderator.opening_message, None, "opening")
        self._record_moderator(first_question.question, first_question.id, "question")

        return AgentResponse(
            action="move_to_next_question",
            text=opening_text,
            question_id=first_question.id,
            reason="Interview started with opening message and first scripted question.",
        )

    def submit_answer(self, answer: str, input_quality: InputQuality = "clear") -> AgentResponse:
        if self.state.status != "in_progress":
            raise RuntimeError("Interview must be started before submitting answers.")

        current_question = self._current_question()
        cleaned_answer = " ".join(answer.strip().split())
        if not cleaned_answer:
            input_quality = "empty"

        self._record_participant(cleaned_answer, current_question.id, kind=f"{input_quality}_answer")

        if input_quality in {"empty", "unclear"}:
            failure_prompt = self._failure_response_prompt(current_question, input_quality)
            if failure_prompt:
                return self.ask_followup(
                    reason=self._failure_reason(input_quality),
                    text=failure_prompt,
                    count_toward_followup_limit=False,
                    failure_mode=input_quality,
                )
            if self._has_next_question():
                return self.move_to_next_question(
                    reason=f"The participant still had {input_quality} input after one clarification attempt.",
                    failure_mode=input_quality,
                )
            return self.end_interview(
                reason=f"The participant still had {input_quality} input on the final question after one clarification attempt.",
                failure_mode=input_quality,
            )

        decision = self.decision_maker.decide(self.script, self.state, current_question, cleaned_answer)

        if decision.action == "ask_followup":
            return self.ask_followup(
                reason=decision.reason,
                text=decision.text or "Could you say a little more about that?",
            )

        if self._has_next_question():
            return self.move_to_next_question(reason=decision.reason)

        return self.end_interview(reason=decision.reason)

    def ask_followup(
        self,
        reason: str,
        text: str,
        count_toward_followup_limit: bool = True,
        failure_mode: str | None = None,
    ) -> AgentResponse:
        """Tool-style action: keep the same question active and ask a follow-up."""
        question = self._current_question()
        if count_toward_followup_limit:
            self.state.followups_by_question[question.id] = self.state.followups_by_question.get(question.id, 0) + 1

        self.state.pending_question_id = question.id
        self._record_moderator(text, question.id, "followup")

        return AgentResponse(
            action="ask_followup",
            text=text,
            question_id=question.id,
            reason=reason,
            failure_mode=failure_mode,
        )

    def move_to_next_question(self, reason: str, failure_mode: str | None = None) -> AgentResponse:
        """Tool-style action: advance to the next scripted question."""
        if not self._has_next_question():
            return self.end_interview(reason="No remaining scripted questions.")

        self.state.current_question_index += 1
        question = self._current_question()
        self.state.pending_question_id = question.id
        self._record_moderator(question.question, question.id, "question")

        return AgentResponse(
            action="move_to_next_question",
            text=question.question,
            question_id=question.id,
            reason=reason,
            failure_mode=failure_mode,
        )

    def end_interview(self, reason: str, failure_mode: str | None = None) -> AgentResponse:
        """Tool-style action: finish the interview and create a structured summary."""
        summary = build_summary(self.script, self.state)
        self.state.status = "complete"
        self.state.pending_question_id = None
        self.state.summary = summary
        self._record_moderator(self.script.moderator.closing_message, None, "closing")

        return AgentResponse(
            action="end_interview",
            text=self.script.moderator.closing_message,
            question_id=None,
            reason=reason,
            is_complete=True,
            summary=summary,
            failure_mode=failure_mode,
        )

    def transcript(self) -> list[TranscriptEntry]:
        return list(self.state.history)

    def _current_question(self) -> InterviewQuestion:
        return self.script.core_questions[self.state.current_question_index]

    def _has_next_question(self) -> bool:
        return self.state.current_question_index + 1 < len(self.script.core_questions)

    def _failure_response_prompt(self, question: InterviewQuestion, input_quality: InputQuality) -> str | None:
        failure_key = f"{question.id}:{input_quality}"
        current_count = self.state.failure_counts_by_question.get(failure_key, 0)
        failure_rule = (
            self.script.failure_handling.unclear_transcription
            if input_quality == "unclear"
            else self.script.failure_handling.empty_or_silent_response
        )

        if current_count < failure_rule.max_retries:
            self.state.failure_counts_by_question[failure_key] = current_count + 1
            return failure_rule.prompt

        return None

    def _failure_reason(self, input_quality: InputQuality) -> str:
        if input_quality == "unclear":
            return "The transcription was marked unclear or low-confidence."
        return "The participant gave an empty or silent response."

    def _record_moderator(self, text: str, question_id: str | None, kind: str) -> None:
        now = datetime.now(timezone.utc)
        self.state.history.append(
            TranscriptEntry(
                role="moderator",
                text=text,
                question_id=question_id,
                kind=kind,
                turn_index=len(self.state.history),
                elapsed_seconds=self._elapsed_seconds(now),
                created_at=now.isoformat(),
            )
        )

    def _record_participant(self, text: str, question_id: str, kind: str = "answer") -> None:
        now = datetime.now(timezone.utc)
        self.state.history.append(
            TranscriptEntry(
                role="participant",
                text=text,
                question_id=question_id,
                kind=kind,
                turn_index=len(self.state.history),
                elapsed_seconds=self._elapsed_seconds(now),
                created_at=now.isoformat(),
            )
        )

    def _elapsed_seconds(self, now: datetime) -> float:
        if self.state.started_at is None:
            return 0.0
        return round((now - self.state.started_at).total_seconds(), 3)
