from __future__ import annotations

import json
from pathlib import Path

from app.agent.models import InterviewScript


def load_interview_script(path: str | Path) -> InterviewScript:
    """Load and validate an interview script JSON file."""
    script_path = Path(path)
    with script_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return InterviewScript.from_dict(data)
