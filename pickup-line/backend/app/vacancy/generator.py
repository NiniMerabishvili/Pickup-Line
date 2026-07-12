from __future__ import annotations

import re
from collections import Counter
from typing import Any

from app.agent.models import InterviewScript


_SKILL_PATTERNS = {
    "python": "Python",
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "react": "React",
    "typescript": "TypeScript",
    "javascript": "JavaScript",
    "sql": "SQL",
    "postgres": "PostgreSQL",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "aws": "AWS",
    "azure": "Azure",
    "gcp": "Google Cloud",
    "llm": "LLMs",
    "rag": "RAG",
    "langchain": "LangChain",
    "openai": "OpenAI API",
    "machine learning": "machine learning",
    "deep learning": "deep learning",
    "nlp": "NLP",
    "computer vision": "computer vision",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "api": "API design",
    "websocket": "WebSockets",
    "git": "Git",
}

_SENIORITY_TERMS = {
    "intern": "internship",
    "junior": "junior",
    "entry": "entry-level",
    "mid": "mid-level",
    "senior": "senior",
    "lead": "lead",
}


def generate_interview_script_from_vacancy(vacancy_text: str, role_title: str | None = None) -> InterviewScript:
    """Generate a deterministic mock interview script from a vacancy description.

    This is intentionally local and quota-free. A provider-backed LLM generator
    can replace this later while returning the same InterviewScript shape.
    """
    cleaned_text = _clean_text(vacancy_text)
    if len(cleaned_text) < 80:
        raise ValueError("Vacancy text is too short to generate useful interview questions.")

    detected_role = role_title or _detect_role_title(cleaned_text)
    skills = _detect_skills(cleaned_text)
    seniority = _detect_seniority(cleaned_text)
    responsibilities = _extract_responsibility_phrases(cleaned_text)
    questions = _build_questions(detected_role, skills, seniority, responsibilities)

    script_data: dict[str, Any] = {
        "id": "generated-vacancy-interview-v1",
        "title": f"{detected_role} Mock Interview",
        "version": "1.0.0",
        "estimated_duration_minutes": 6,
        "topic": {
            "product_name": detected_role,
            "scenario": f"A mock interview generated from a {detected_role} vacancy description.",
            "research_goal": "Practice likely interview questions based on the role requirements and responsibilities.",
        },
        "moderator": {
            "tone": "Warm, concise, realistic, and interviewer-like.",
            "opening_message": (
                f"Hi, I will run a short mock interview for the {detected_role} role. "
                "I will ask likely questions based on the vacancy, and I may ask one follow-up if your answer needs more detail."
            ),
            "closing_message": "Thanks, that is the end of the mock interview. I will summarize your answers now.",
        },
        "core_questions": questions,
        "followup_policy": {
            "max_followups_per_question": 1,
            "ask_followup_when": [
                {
                    "condition": "answer_word_count < 10",
                    "reason": "The answer is too short to evaluate interview readiness.",
                },
                {
                    "condition": "answer_is_vague",
                    "reason": "The answer needs a concrete example, tradeoff, or result.",
                },
                {
                    "condition": "answer_mentions_confusion_or_frustration",
                    "reason": "The candidate surfaced a challenge worth probing.",
                },
            ],
            "move_on_when": [
                "The candidate gives a concrete answer with an example or reason.",
                "The interviewer has already asked one follow-up for the current question.",
                "The candidate says they do not know after a clarification attempt.",
            ],
            "style_rules": [
                "Ask only one question at a time.",
                "Keep follow-ups under 25 words.",
                "Prefer realistic interview phrasing.",
            ],
        },
        "failure_handling": {
            "empty_or_silent_response": {
                "max_retries": 1,
                "prompt": "I did not catch an answer. Could you give a short response to the question?",
            },
            "unclear_transcription": {
                "max_retries": 1,
                "prompt": "I may have misheard that. Could you repeat your main point in one sentence?",
            },
            "off_topic_response": {
                "max_redirects": 1,
                "prompt": "Helpful context. Thinking about this role, what would your answer be?",
            },
        },
        "summary_requirements": {
            "format": "structured_json",
            "include": [
                "one_sentence_overall_summary",
                "key_points_by_question",
                "notable_quotes",
                "themes",
                "unanswered_or_unclear_items",
            ],
            "quote_rules": {
                "max_quotes": 3,
                "prefer_specific_quotes": True,
                "include_question_id": True,
            },
        },
    }

    return InterviewScript.from_dict(script_data)


def _clean_text(text: str) -> str:
    return " ".join(text.strip().split())


def _detect_role_title(text: str) -> str:
    lines = [line.strip() for line in re.split(r"[\r\n]+", text) if line.strip()]
    for line in lines[:8]:
        if re.search(r"(engineer|developer|scientist|analyst|intern|designer|manager)", line, re.I):
            return _compact_title(line)

    match = re.search(
        r"(?i)(?:role|position|title)\s*[:\-]\s*([A-Za-z0-9 /,+#.-]{3,80})",
        text,
    )
    if match:
        return _compact_title(match.group(1))

    return "Generated Role"


def _compact_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title).strip(" -:|")
    title = title[:70].strip()
    return title or "Generated Role"


def _detect_skills(text: str) -> list[str]:
    lower = text.lower()
    found = [label for pattern, label in _SKILL_PATTERNS.items() if pattern in lower]
    return found[:6]


def _detect_seniority(text: str) -> str:
    lower = text.lower()
    for term, label in _SENIORITY_TERMS.items():
        if term in lower:
            return label
    return "unspecified"


def _extract_responsibility_phrases(text: str) -> list[str]:
    candidates = re.split(r"[.;\n]", text)
    useful = []
    for candidate in candidates:
        cleaned = candidate.strip(" -•*\t")
        lower = cleaned.lower()
        if 30 <= len(cleaned) <= 160 and any(
            marker in lower
            for marker in ["build", "design", "develop", "deploy", "work with", "collaborate", "implement", "analyze"]
        ):
            useful.append(cleaned)
    return useful[:3]


def _build_questions(
    role_title: str,
    skills: list[str],
    seniority: str,
    responsibilities: list[str],
) -> list[dict[str, Any]]:
    primary_skill = skills[0] if skills else "the main technical stack"
    secondary_skill = skills[1] if len(skills) > 1 else "the role requirements"
    responsibility = responsibilities[0] if responsibilities else "building and improving production features"

    questions = [
        {
            "id": "q1_role_fit",
            "order": 1,
            "question": f"Why are you a strong fit for this {role_title} role?",
            "intent": "Assess motivation, role understanding, and candidate positioning.",
            "followup_hints": [
                "Ask for one concrete example from a project or previous experience.",
                "Ask how their background maps to the vacancy requirements.",
            ],
        },
        {
            "id": "q2_core_skill",
            "order": 2,
            "question": f"Tell me about a project where you used {primary_skill} to solve a real problem.",
            "intent": "Probe hands-on experience with a likely core skill from the vacancy.",
            "followup_hints": [
                "Ask about tradeoffs, constraints, or measurable results.",
                "Ask what they would improve if they rebuilt it.",
            ],
        },
        {
            "id": "q3_responsibility",
            "order": 3,
            "question": f"This role may involve {responsibility}. How would you approach that work?",
            "intent": "Evaluate role-specific problem solving and execution approach.",
            "followup_hints": [
                "Ask how they would break down the problem.",
                "Ask how they would validate success.",
            ],
        },
        {
            "id": "q4_collaboration",
            "order": 4,
            "question": f"Describe a time you had to learn or collaborate around {secondary_skill}. What did you do?",
            "intent": "Assess learning ability, communication, and collaboration.",
            "followup_hints": [
                "Ask what made the situation difficult.",
                "Ask what changed because of their contribution.",
            ],
        },
        {
            "id": "q5_growth",
            "order": 5,
            "question": _growth_question(seniority, skills),
            "intent": "Probe self-awareness and growth plan for this role.",
            "followup_hints": [
                "Ask for a concrete learning plan.",
                "Ask how they would close the gap in the first month.",
            ],
        },
    ]
    return questions


def _growth_question(seniority: str, skills: list[str]) -> str:
    if seniority == "internship":
        return "What would you want to learn most during this internship, and how would you contribute while learning?"
    if skills:
        counted = Counter(skills)
        skill = counted.most_common(1)[0][0]
        return f"What is one area related to {skill} where you still want to grow?"
    return "What is one technical or professional area where you still want to grow for this role?"
