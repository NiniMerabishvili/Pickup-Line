from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


@unittest.skipIf(
    importlib.util.find_spec("fastapi") is None,
    "FastAPI is not installed in this Python environment.",
)
class ApiTests(unittest.TestCase):
    def test_start_and_answer_flow(self) -> None:
        from fastapi.testclient import TestClient

        from app.api import app

        client = TestClient(app)

        root = client.get("/", follow_redirects=False)
        self.assertEqual(root.status_code, 307)
        self.assertEqual(root.headers["location"], "/docs")

        stt_test = client.get("/stt-test")
        self.assertEqual(stt_test.status_code, 200)
        self.assertIn("Mini Research Moderator STT Test", stt_test.text)
        self.assertIn("Interviewer Avatar", stt_test.text)
        self.assertIn("avatar_neo.png", stt_test.text)
        self.assertIn("volumeIndicator", stt_test.text)
        self.assertIn("Volume indicator follows TTS audio energy", stt_test.text)
        self.assertIn("TalkingAvatar", stt_test.text)
        self.assertLess(stt_test.text.index("class TalkingAvatar"), stt_test.text.rindex("initializeAvatar();"))
        self.assertIn("Vacancy Mode", stt_test.text)
        self.assertIn("Generate Mock Interview", stt_test.text)
        self.assertIn("Use Browser Speech", stt_test.text)
        self.assertIn("Answer Fallback", stt_test.text)
        self.assertIn("Send Typed Answer", stt_test.text)
        self.assertIn("Interview session was not found", stt_test.text)
        self.assertIn("Simulate Unclear Input", stt_test.text)
        self.assertIn("Speak replies", stt_test.text)
        self.assertIn("OpenAI TTS", stt_test.text)
        self.assertIn("Flagged Themes", stt_test.text)
        self.assertIn("Key Points By Question", stt_test.text)

        avatar = client.get("/static/avatar/avatar_neo.png")
        self.assertEqual(avatar.status_code, 200)
        self.assertIn("image/png", avatar.headers["content-type"])
        self.assertGreater(len(avatar.content), 1000)

        config = client.get("/api/config")
        self.assertEqual(config.status_code, 200)
        self.assertIn("openai_api_key_configured", config.json())

        start = client.post("/api/interviews/start")
        self.assertEqual(start.status_code, 200)
        start_body = start.json()
        self.assertIn("session_id", start_body)
        self.assertEqual(start_body["question_id"], "q1_first_impression")

        answer = client.post(
            f"/api/interviews/{start_body['session_id']}/answer",
            json={"answer": "Good."},
        )
        self.assertEqual(answer.status_code, 200)
        answer_body = answer.json()
        self.assertEqual(answer_body["action"], "ask_followup")
        self.assertIsNone(answer_body["failure_mode"])

        unclear = client.post(
            f"/api/interviews/{start_body['session_id']}/answer",
            json={"answer": "garbled transcript", "input_quality": "unclear"},
        )
        self.assertEqual(unclear.status_code, 200)
        unclear_body = unclear.json()
        self.assertEqual(unclear_body["action"], "ask_followup")
        self.assertEqual(unclear_body["failure_mode"], "unclear")

        transcript = client.get(f"/api/interviews/{start_body['session_id']}/transcript")
        self.assertEqual(transcript.status_code, 200)
        transcript_body = transcript.json()
        self.assertIn("timestamp", transcript_body["transcript"][0])
        self.assertIn("elapsed_seconds", transcript_body["transcript"][0])

    def test_start_interview_from_vacancy(self) -> None:
        from fastapi.testclient import TestClient

        from app.api import app

        client = TestClient(app)
        vacancy_text = """
        AI Engineer Intern
        Build Python and FastAPI APIs for LLM workflows. Work with OpenAI,
        RAG prototypes, SQL, Docker, and collaborate with product managers.
        """

        response = client.post(
            "/api/interviews/start-from-vacancy",
            json={"vacancy_text": vacancy_text, "role_title": "AI Engineer Intern"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("session_id", body)
        self.assertIn("AI Engineer Intern", body["text"])
        self.assertEqual(body["question_id"], "q1_role_fit")

    def test_audio_websocket_transcribes_and_feeds_agent(self) -> None:
        from fastapi.testclient import TestClient

        import app.api as api
        from app.stt import TranscriptionResult

        class FakeTranscriber:
            def transcribe(self, audio_bytes: bytes, filename: str) -> TranscriptionResult:
                self.audio_bytes = audio_bytes
                self.filename = filename
                return TranscriptionResult(
                    text="The onboarding was clear because the first screen explained the setup.",
                    model="fake-transcriber",
                )

        original_transcriber = api._transcriber
        api._transcriber = FakeTranscriber()
        try:
            client = TestClient(api.app)
            start = client.post("/api/interviews/start")
            session_id = start.json()["session_id"]

            with client.websocket_connect(f"/ws/interviews/{session_id}/audio") as websocket:
                ready = websocket.receive_json()
                self.assertEqual(ready["event"], "ready")

                websocket.send_bytes(b"fake-audio")
                chunk = websocket.receive_json()
                self.assertEqual(chunk["event"], "chunk_received")
                self.assertEqual(chunk["bytes_buffered"], len(b"fake-audio"))

                websocket.send_json({"event": "stop", "mime_type": "audio/webm"})
                transcribing = websocket.receive_json()
                self.assertEqual(transcribing["event"], "transcribing")

                response = websocket.receive_json()
                self.assertEqual(response["event"], "moderator_response")
                self.assertEqual(response["transcription_model"], "fake-transcriber")
                self.assertEqual(response["action"], "move_to_next_question")
                self.assertEqual(response["question_id"], "q2_value_clarity")
        finally:
            api._transcriber = original_transcriber

    def test_tts_endpoint_returns_audio_bytes(self) -> None:
        from fastapi.testclient import TestClient

        import app.api as api
        from app.tts import TTSResult

        class FakeSynthesizer:
            def synthesize(self, text: str) -> TTSResult:
                self.text = text
                return TTSResult(
                    audio_bytes=b"fake-mp3-bytes",
                    model="fake-tts",
                    voice="fake-voice",
                    response_format="mp3",
                )

        original_synthesizer = api._synthesizer
        fake_synthesizer = FakeSynthesizer()
        api._synthesizer = fake_synthesizer
        try:
            client = TestClient(api.app)
            response = client.post("/api/tts", json={"text": "Hello participant."})

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, b"fake-mp3-bytes")
            self.assertEqual(response.headers["content-type"], "audio/mpeg")
            self.assertEqual(response.headers["x-tts-model"], "fake-tts")
            self.assertEqual(fake_synthesizer.text, "Hello participant.")
        finally:
            api._synthesizer = original_synthesizer

    def test_audio_websocket_empty_buffer_uses_silent_response_handling(self) -> None:
        from fastapi.testclient import TestClient

        from app.api import app

        client = TestClient(app)
        start = client.post("/api/interviews/start")
        session_id = start.json()["session_id"]

        with client.websocket_connect(f"/ws/interviews/{session_id}/audio") as websocket:
            ready = websocket.receive_json()
            self.assertEqual(ready["event"], "ready")

            websocket.send_json({"event": "stop"})
            response = websocket.receive_json()
            self.assertEqual(response["event"], "moderator_response")
            self.assertEqual(response["transcript"], "")
            self.assertEqual(response["action"], "ask_followup")
            self.assertIn("did not catch", response["text"])


if __name__ == "__main__":
    unittest.main()
