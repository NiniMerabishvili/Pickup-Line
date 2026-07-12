from __future__ import annotations

import json
from pathlib import Path

from app.agent import ResearchModerator, load_interview_script


DEFAULT_SCRIPT = Path(__file__).parent / "interviews" / "onboarding_feedback.json"


def main() -> None:
    script = load_interview_script(DEFAULT_SCRIPT)
    moderator = ResearchModerator(script)
    response = moderator.start()

    print(f"Moderator: {response.text}\n")

    while not response.is_complete:
        answer = input("Participant: ")
        response = moderator.submit_answer(answer)
        print(f"\nModerator: {response.text}\n")

    print("Summary:")
    print(json.dumps(response.summary, indent=2))


if __name__ == "__main__":
    main()
