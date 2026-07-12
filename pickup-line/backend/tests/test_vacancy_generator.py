from __future__ import annotations

import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.vacancy import generate_interview_script_from_vacancy  # noqa: E402


VACANCY_TEXT = """
AI Engineer Intern

We are looking for an intern to build Python and FastAPI services for LLM workflows.
The role involves developing APIs, working with OpenAI, building RAG prototypes,
collaborating with product managers, and deploying Docker-based services.
Candidates should understand machine learning basics, Git, and SQL.
"""


class VacancyGeneratorTests(unittest.TestCase):
    def test_generates_interview_script_from_vacancy(self) -> None:
        script = generate_interview_script_from_vacancy(VACANCY_TEXT)

        self.assertIn("AI Engineer Intern", script.title)
        self.assertEqual(len(script.core_questions), 5)
        self.assertIn("Python", script.core_questions[1].question)
        self.assertIn("mock interview", script.moderator.opening_message.lower())

    def test_rejects_short_vacancy_text(self) -> None:
        with self.assertRaises(ValueError):
            generate_interview_script_from_vacancy("AI intern")


if __name__ == "__main__":
    unittest.main()
