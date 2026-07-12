from __future__ import annotations

import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.agent import ResearchModerator, load_interview_script  # noqa: E402


SCRIPT_PATH = BACKEND_ROOT / "app" / "interviews" / "onboarding_feedback.json"


class ResearchModeratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.script = load_interview_script(SCRIPT_PATH)
        self.moderator = ResearchModerator(self.script)

    def test_start_opens_with_first_scripted_question(self) -> None:
        response = self.moderator.start()

        self.assertEqual(response.action, "move_to_next_question")
        self.assertEqual(response.question_id, "q1_first_impression")
        self.assertIn("Hi, thanks for helping test Atlas Notes", response.text)
        self.assertIn("What was your first impression", response.text)
        self.assertEqual(self.moderator.state.status, "in_progress")

    def test_short_answer_gets_one_followup_then_moves_on(self) -> None:
        self.moderator.start()

        followup = self.moderator.submit_answer("Good.")
        self.assertEqual(followup.action, "ask_followup")
        self.assertEqual(followup.question_id, "q1_first_impression")
        self.assertIn("specific", followup.text.lower())

        next_question = self.moderator.submit_answer(
            "The first screen felt friendly because it explained the setup before asking me to continue."
        )
        self.assertEqual(next_question.action, "move_to_next_question")
        self.assertEqual(next_question.question_id, "q2_value_clarity")

    def test_empty_response_asks_for_clarification_without_advancing(self) -> None:
        self.moderator.start()

        clarification = self.moderator.submit_answer("")

        self.assertEqual(clarification.action, "ask_followup")
        self.assertEqual(clarification.failure_mode, "empty")
        self.assertEqual(clarification.question_id, "q1_first_impression")
        self.assertIn("did not catch", clarification.text)
        self.assertEqual(self.moderator.state.current_question_index, 0)

    def test_unclear_transcription_asks_for_repeat_without_advancing(self) -> None:
        self.moderator.start()

        clarification = self.moderator.submit_answer("muffled partial transcript", input_quality="unclear")

        self.assertEqual(clarification.action, "ask_followup")
        self.assertEqual(clarification.failure_mode, "unclear")
        self.assertEqual(clarification.question_id, "q1_first_impression")
        self.assertIn("misheard", clarification.text)
        self.assertEqual(self.moderator.state.current_question_index, 0)

    def test_repeated_unclear_transcription_moves_on_after_retry_limit(self) -> None:
        self.moderator.start()

        first = self.moderator.submit_answer("muffled partial transcript", input_quality="unclear")
        second = self.moderator.submit_answer("still garbled", input_quality="unclear")

        self.assertEqual(first.action, "ask_followup")
        self.assertEqual(second.action, "move_to_next_question")
        self.assertEqual(second.failure_mode, "unclear")
        self.assertEqual(second.question_id, "q2_value_clarity")

    def test_repeated_empty_response_moves_on_after_retry_limit(self) -> None:
        self.moderator.start()

        first = self.moderator.submit_answer("")
        second = self.moderator.submit_answer("")

        self.assertEqual(first.action, "ask_followup")
        self.assertEqual(second.action, "move_to_next_question")
        self.assertEqual(second.question_id, "q2_value_clarity")

    def test_interview_completes_with_structured_summary(self) -> None:
        self.moderator.start()
        answers = [
            "The onboarding felt clear because the first screen explained why the app needed a setup step.",
            "I understood it helps organize class notes and make them easier to review later.",
            "The data permission made me pause because I was not sure what would be stored.",
            "I would want a plain explanation of what is stored and why it is needed.",
            "I would shorten setup because account creation happened before I saw the main value.",
        ]

        response = None
        for answer in answers:
            response = self.moderator.submit_answer(answer)
            if response.is_complete:
                break

        self.assertIsNotNone(response)
        self.assertTrue(response.is_complete)
        self.assertEqual(response.action, "end_interview")
        self.assertIsNotNone(response.summary)
        assert response.summary is not None
        self.assertIn("key_points_by_question", response.summary)
        self.assertIn("notable_quotes", response.summary)
        self.assertIn("flagged_themes", response.summary)
        self.assertIn("coverage", response.summary)
        self.assertGreaterEqual(len(response.summary["notable_quotes"]), 1)
        self.assertIn("timestamp", response.summary["notable_quotes"][0])
        self.assertIn("answer_count", response.summary["key_points_by_question"][0])

    def test_followup_limit_prevents_repeating_same_question_forever(self) -> None:
        self.moderator.start()

        first = self.moderator.submit_answer("Nice.")
        second = self.moderator.submit_answer("Okay.")

        self.assertEqual(first.action, "ask_followup")
        self.assertEqual(second.action, "move_to_next_question")
        self.assertEqual(self.moderator.state.followups_by_question["q1_first_impression"], 1)


if __name__ == "__main__":
    unittest.main()
