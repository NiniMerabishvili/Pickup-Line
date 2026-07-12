from __future__ import annotations

import re
from typing import Protocol

from app.agent.models import InterviewQuestion, InterviewScript, InterviewState, ModerationDecision


class DecisionMaker(Protocol):
    """Decision interface that an LLM function-calling adapter can implement later."""

    def decide(
        self,
        script: InterviewScript,
        state: InterviewState,
        question: InterviewQuestion,
        answer: str,
    ) -> ModerationDecision:
        ...


class RuleBasedDecisionMaker:
    """Local decision maker for proving the text loop before adding LLM/API dependencies."""

    _confusion_terms = {
        "confusing",
        "confused",
        "unclear",
        "lost",
        "frustrating",
        "frustrated",
        "annoying",
        "hard",
        "difficult",
        "overwhelming",
    }
    _trust_terms = {
        "trust",
        "privacy",
        "private",
        "permission",
        "permissions",
        "data",
        "secure",
        "security",
        "creepy",
        "tracking",
    }
    _vague_terms = {
        "good",
        "bad",
        "fine",
        "okay",
        "ok",
        "nice",
        "cool",
        "normal",
        "simple",
        "easy",
    }
    _concrete_markers = {
        "because",
        "when",
        "after",
        "before",
        "screen",
        "button",
        "permission",
        "example",
        "felt",
        "made",
        "showed",
        "asked",
        "step",
    }

    def decide(
        self,
        script: InterviewScript,
        state: InterviewState,
        question: InterviewQuestion,
        answer: str,
    ) -> ModerationDecision:
        followup_count = state.followups_by_question.get(question.id, 0)
        if followup_count >= script.followup_policy.max_followups_per_question:
            return ModerationDecision(
                action="move_to_next_question",
                reason="The question already reached the follow-up limit.",
            )

        words = _words(answer)
        lower_words = {word.lower() for word in words}

        if len(words) < 10:
            return ModerationDecision(
                action="ask_followup",
                reason="The answer is too short to produce useful research insight.",
                text=self._followup_for_short_answer(question),
            )

        if lower_words & self._trust_terms:
            return ModerationDecision(
                action="ask_followup",
                reason="The participant mentioned trust, privacy, permissions, or data.",
                text="What would have made that feel more trustworthy?",
            )

        if lower_words & self._confusion_terms:
            return ModerationDecision(
                action="ask_followup",
                reason="The participant mentioned confusion or frustration.",
                text="What part felt confusing or frustrating, specifically?",
            )

        if self._is_vague(lower_words):
            return ModerationDecision(
                action="ask_followup",
                reason="The answer is broad but does not include a specific example or cause.",
                text=self._followup_for_vague_answer(question),
            )

        return ModerationDecision(
            action="move_to_next_question",
            reason="The answer includes enough detail to continue.",
        )

    def _is_vague(self, lower_words: set[str]) -> bool:
        has_vague_language = bool(lower_words & self._vague_terms)
        has_concrete_marker = bool(lower_words & self._concrete_markers)
        return has_vague_language and not has_concrete_marker

    def _followup_for_short_answer(self, question: InterviewQuestion) -> str:
        if question.id == "q4_improvement":
            return "Why would that change matter most?"
        return "Could you share one specific example or moment?"

    def _followup_for_vague_answer(self, question: InterviewQuestion) -> str:
        if question.id == "q2_value_clarity":
            return "How would you describe the product in your own words?"
        if question.id == "q4_improvement":
            return "What would a better version look or sound like?"
        return "What specifically made you feel that way?"


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", text)
