from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


AgentAction = Literal["ask_followup", "move_to_next_question", "end_interview"]
InterviewStatus = Literal["not_started", "in_progress", "complete"]
TranscriptRole = Literal["moderator", "participant"]
InputQuality = Literal["clear", "empty", "unclear"]


@dataclass(frozen=True)
class Topic:
    product_name: str
    scenario: str
    research_goal: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Topic":
        return cls(
            product_name=data["product_name"],
            scenario=data["scenario"],
            research_goal=data["research_goal"],
        )


@dataclass(frozen=True)
class ModeratorPersona:
    tone: str
    opening_message: str
    closing_message: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModeratorPersona":
        return cls(
            tone=data["tone"],
            opening_message=data["opening_message"],
            closing_message=data["closing_message"],
        )


@dataclass(frozen=True)
class InterviewQuestion:
    id: str
    order: int
    question: str
    intent: str
    followup_hints: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InterviewQuestion":
        return cls(
            id=data["id"],
            order=int(data["order"]),
            question=data["question"],
            intent=data["intent"],
            followup_hints=tuple(data.get("followup_hints", [])),
        )


@dataclass(frozen=True)
class FollowupPolicy:
    max_followups_per_question: int
    ask_followup_when: tuple[dict[str, str], ...]
    move_on_when: tuple[str, ...]
    style_rules: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FollowupPolicy":
        return cls(
            max_followups_per_question=int(data["max_followups_per_question"]),
            ask_followup_when=tuple(data.get("ask_followup_when", [])),
            move_on_when=tuple(data.get("move_on_when", [])),
            style_rules=tuple(data.get("style_rules", [])),
        )


@dataclass(frozen=True)
class FailureRule:
    max_retries: int
    prompt: str

    @classmethod
    def from_dict(cls, data: dict[str, Any], retry_key: str = "max_retries") -> "FailureRule":
        return cls(max_retries=int(data[retry_key]), prompt=data["prompt"])


@dataclass(frozen=True)
class FailureHandling:
    empty_or_silent_response: FailureRule
    unclear_transcription: FailureRule
    off_topic_response: FailureRule

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FailureHandling":
        return cls(
            empty_or_silent_response=FailureRule.from_dict(data["empty_or_silent_response"]),
            unclear_transcription=FailureRule.from_dict(data["unclear_transcription"]),
            off_topic_response=FailureRule.from_dict(data["off_topic_response"], retry_key="max_redirects"),
        )


@dataclass(frozen=True)
class SummaryRequirements:
    format: str
    include: tuple[str, ...]
    quote_rules: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SummaryRequirements":
        return cls(
            format=data["format"],
            include=tuple(data.get("include", [])),
            quote_rules=data.get("quote_rules", {}),
        )


@dataclass(frozen=True)
class InterviewScript:
    id: str
    title: str
    version: str
    estimated_duration_minutes: int
    topic: Topic
    moderator: ModeratorPersona
    core_questions: tuple[InterviewQuestion, ...]
    followup_policy: FollowupPolicy
    failure_handling: FailureHandling
    summary_requirements: SummaryRequirements

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InterviewScript":
        questions = tuple(
            sorted(
                (InterviewQuestion.from_dict(item) for item in data["core_questions"]),
                key=lambda question: question.order,
            )
        )

        return cls(
            id=data["id"],
            title=data["title"],
            version=data["version"],
            estimated_duration_minutes=int(data["estimated_duration_minutes"]),
            topic=Topic.from_dict(data["topic"]),
            moderator=ModeratorPersona.from_dict(data["moderator"]),
            core_questions=questions,
            followup_policy=FollowupPolicy.from_dict(data["followup_policy"]),
            failure_handling=FailureHandling.from_dict(data["failure_handling"]),
            summary_requirements=SummaryRequirements.from_dict(data["summary_requirements"]),
        )


@dataclass(frozen=True)
class TranscriptEntry:
    role: TranscriptRole
    text: str
    question_id: str | None = None
    kind: str = "message"
    turn_index: int = 0
    elapsed_seconds: float = 0.0
    created_at: str = ""


@dataclass
class InterviewState:
    status: InterviewStatus = "not_started"
    current_question_index: int = 0
    history: list[TranscriptEntry] = field(default_factory=list)
    followups_by_question: dict[str, int] = field(default_factory=dict)
    failure_counts_by_question: dict[str, int] = field(default_factory=dict)
    pending_question_id: str | None = None
    summary: dict[str, Any] | None = None
    started_at: datetime | None = None


@dataclass(frozen=True)
class ModerationDecision:
    action: AgentAction
    reason: str
    text: str | None = None


@dataclass(frozen=True)
class AgentResponse:
    action: AgentAction
    text: str
    question_id: str | None
    reason: str
    is_complete: bool = False
    summary: dict[str, Any] | None = None
    failure_mode: str | None = None
