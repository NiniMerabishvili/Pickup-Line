from __future__ import annotations

import re
from typing import Any

from app.agent.models import InterviewScript, InterviewState, TranscriptEntry


_THEME_KEYWORDS = {
    "clarity": {"clear", "unclear", "understand", "confusing", "confused", "explain"},
    "trust_privacy": {"trust", "privacy", "permission", "permissions", "data", "secure", "tracking"},
    "friction": {"slow", "long", "hard", "difficult", "frustrating", "annoying", "too much"},
    "value": {"useful", "help", "organize", "notes", "save", "benefit"},
    "improvement": {"change", "remove", "add", "simplify", "shorter", "better"},
}

_THEME_LABELS = {
    "clarity": "Clarity",
    "trust_privacy": "Trust and privacy",
    "friction": "Friction",
    "value": "Value proposition",
    "improvement": "Improvement request",
}


def build_summary(script: InterviewScript, state: InterviewState) -> dict[str, Any]:
    answers_by_question = _answers_by_question(state.history)
    key_points = []
    unanswered = []

    for question in script.core_questions:
        answers = answers_by_question.get(question.id, [])
        if not answers:
            unanswered.append({"question_id": question.id, "reason": "No participant answer recorded."})
            key_points.append(
                {
                    "question_id": question.id,
                    "question": question.question,
                    "participant_points": [],
                }
            )
            continue

        participant_points = [
            {
                "text": _compact_answer(answer.text),
                "timestamp": _format_timestamp(answer.elapsed_seconds),
                "elapsed_seconds": answer.elapsed_seconds,
                "turn_index": answer.turn_index,
            }
            for answer in answers
            if answer.text.strip()
        ]
        if not participant_points:
            unanswered.append({"question_id": question.id, "reason": "Only empty or unclear answers recorded."})

        key_points.append(
            {
                "question_id": question.id,
                "question": question.question,
                "answer_count": len(participant_points),
                "participant_points": participant_points,
            }
        )

    themes = _detect_themes(state.history)
    quotes = _notable_quotes(script, state.history)
    overall = _overall_summary(script, themes, unanswered)

    return {
        "interview_title": script.title,
        "script_id": script.id,
        "one_sentence_overall_summary": overall,
        "key_points_by_question": key_points,
        "notable_quotes": quotes,
        "flagged_themes": themes,
        "unanswered_or_unclear_items": unanswered,
        "coverage": {
            "questions_answered": sum(1 for item in key_points if item["answer_count"] > 0),
            "total_questions": len(script.core_questions),
            "participant_turns": sum(1 for entry in state.history if entry.role == "participant"),
        },
    }


def _answers_by_question(history: list[TranscriptEntry]) -> dict[str, list[TranscriptEntry]]:
    answers: dict[str, list[TranscriptEntry]] = {}
    for entry in history:
        if entry.role == "participant" and entry.question_id:
            answers.setdefault(entry.question_id, []).append(entry)
    return answers


def _compact_answer(text: str) -> str:
    cleaned = " ".join(text.strip().split())
    if len(cleaned) <= 180:
        return cleaned
    return f"{cleaned[:177].rstrip()}..."


def _detect_themes(history: list[TranscriptEntry]) -> list[dict[str, Any]]:
    participant_entries = [entry for entry in history if entry.role == "participant" and entry.text.strip()]
    combined_text = " ".join(entry.text.lower() for entry in participant_entries)
    found = []

    for theme, keywords in _THEME_KEYWORDS.items():
        matched = sorted(keyword for keyword in keywords if keyword in combined_text)
        if matched:
            evidence = [
                {
                    "quote": _compact_answer(entry.text),
                    "timestamp": _format_timestamp(entry.elapsed_seconds),
                    "question_id": entry.question_id or "unknown",
                }
                for entry in participant_entries
                if any(keyword in entry.text.lower() for keyword in matched)
            ][:2]
            found.append(
                {
                    "theme": theme,
                    "label": _THEME_LABELS.get(theme, theme.replace("_", " ").title()),
                    "severity": _theme_severity(theme, matched),
                    "evidence_keywords": matched[:5],
                    "evidence": evidence,
                }
            )

    return found


def _notable_quotes(script: InterviewScript, history: list[TranscriptEntry]) -> list[dict[str, Any]]:
    max_quotes = int(script.summary_requirements.quote_rules.get("max_quotes", 3))
    answers = [
        entry
        for entry in history
        if entry.role == "participant" and entry.text.strip() and len(_words(entry.text)) >= 6
    ]
    ranked = sorted(answers, key=lambda entry: (_quote_score(entry.text), len(entry.text)), reverse=True)

    quotes = []
    for entry in ranked[:max_quotes]:
        quotes.append(
            {
                "question_id": entry.question_id or "unknown",
                "quote": _compact_answer(entry.text),
                "timestamp": _format_timestamp(entry.elapsed_seconds),
                "elapsed_seconds": entry.elapsed_seconds,
                "turn_index": entry.turn_index,
            }
        )
    return quotes


def _quote_score(text: str) -> int:
    lower = text.lower()
    score = 0
    for keywords in _THEME_KEYWORDS.values():
        score += sum(1 for keyword in keywords if keyword in lower)
    if "because" in lower:
        score += 2
    return score


def _overall_summary(
    script: InterviewScript,
    themes: list[dict[str, Any]],
    unanswered: list[dict[str, str]],
) -> str:
    if themes:
        theme_names = ", ".join(theme["label"].lower() for theme in themes[:3])
        return f"The {script.title} interview surfaced signals around {theme_names}."
    if unanswered:
        return f"The {script.title} interview completed with limited detail on some questions."
    return f"The {script.title} interview completed with usable feedback across the scripted questions."


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", text)


def _format_timestamp(elapsed_seconds: float) -> str:
    total_seconds = max(0, int(round(elapsed_seconds)))
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


def _theme_severity(theme: str, matched_keywords: list[str]) -> str:
    if theme in {"trust_privacy", "friction"}:
        return "high" if len(matched_keywords) >= 2 else "medium"
    if theme == "clarity" and any(keyword in matched_keywords for keyword in ["unclear", "confusing", "confused"]):
        return "high"
    return "medium" if len(matched_keywords) >= 2 else "low"
