
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import HTTPException

from src.triage import routes


def model_response(content):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content)
            )
        ]
    )


class Stage3Tests(unittest.TestCase):

    def setUp(self):
        self.env = patch.dict(
            os.environ,
            {
                "LLM_STUB": "0",
                "LLM_BASE_URL": "http://localhost:11434/v1/",
                "LLM_API_KEY": "ollama",
                "LLM_MODEL": "gemma3:1b",
            },
        )
        self.env.start()
        self.addCleanup(self.env.stop)

        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.quarantine = Path(self.temp_dir.name) / "quarantine.jsonl"

    def test_invalid_response_is_repaired(self):
        create_mock = Mock(
            side_effect=[
                model_response("This is not valid JSON"),
                model_response(
                    '{"category":"billing","urgency":"normal",'
                    '"confidence":0.95,'
                    '"reason":"The customer reports a duplicate charge."}'
                ),
            ]
        )

        fake_client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=create_mock)
            )
        )

        with (
            patch.object(routes, "OpenAI", return_value=fake_client),
            patch.object(
                routes, "QUARANTINE_PATH", self.quarantine
            ),
        ):
            result = routes.triage_ticket(
                routes.TriageRequest(text="I was charged twice.")
            )

        self.assertEqual(result.category, routes.Category.billing)
        self.assertEqual(create_mock.call_count, 2)
        self.assertFalse(self.quarantine.exists())

    def test_two_invalid_responses_are_quarantined(self):
        create_mock = Mock(
            side_effect=[
                model_response("Invalid first response"),
                model_response("Invalid repair response"),
            ]
        )

        fake_client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=create_mock)
            )
        )

        with (
            patch.object(routes, "OpenAI", return_value=fake_client),
            patch.object(
                routes, "QUARANTINE_PATH", self.quarantine
            ),
        ):
            with self.assertRaises(HTTPException) as error:
                routes.triage_ticket(
                    routes.TriageRequest(
                        text="My subscription payment failed."
                    )
                )

        self.assertEqual(error.exception.status_code, 422)
        self.assertTrue(self.quarantine.exists())

        record = json.loads(
            self.quarantine.read_text(encoding="utf-8").strip()
        )

        self.assertEqual(record["prompt_version"], "triage-v2")
        self.assertIn("Invalid first response", record["raw_output"])
        self.assertIn("Invalid repair response", record["raw_output"])
        self.assertEqual(create_mock.call_count, 2)


if __name__ == "__main__":
    unittest.main()
