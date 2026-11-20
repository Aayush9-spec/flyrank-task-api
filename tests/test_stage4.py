
import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
from openai import APIStatusError, APITimeoutError

from src.triage import routes


def make_status_error(status_code, headers=None):
    request = httpx.Request("POST", "http://localhost:11434/v1/chat/completions")
    response = httpx.Response(
        status_code,
        headers=headers or {},
        request=request,
    )
    return APIStatusError(
        "Provider error",
        response=response,
        body=None,
    )


def make_timeout_error():
    request = httpx.Request("POST", "http://localhost:11434/v1/chat/completions")
    return APITimeoutError(request=request)


class Stage4Tests(unittest.TestCase):

    def test_429_is_retried_and_then_succeeds(self):
        client = Mock()
        client.chat.completions.create.side_effect = [
            make_status_error(429),
            "success",
        ]

        with patch.object(routes.time, "sleep") as sleep_mock:
            result = routes.call_model_with_retry(
                client, "gemma3:1b", [], 0.1
            )

        self.assertEqual(result, "success")
        self.assertEqual(client.chat.completions.create.call_count, 2)
        sleep_mock.assert_called_once()

    def test_500_is_retried(self):
        client = Mock()
        client.chat.completions.create.side_effect = [
            make_status_error(500),
            "success",
        ]

        with patch.object(routes.time, "sleep"):
            result = routes.call_model_with_retry(
                client, "gemma3:1b", [], 0.1
            )

        self.assertEqual(result, "success")
        self.assertEqual(client.chat.completions.create.call_count, 2)

    def test_timeout_is_retried(self):
        client = Mock()
        client.chat.completions.create.side_effect = [
            make_timeout_error(),
            "success",
        ]

        with patch.object(routes.time, "sleep"):
            result = routes.call_model_with_retry(
                client, "gemma3:1b", [], 0.1
            )

        self.assertEqual(result, "success")
        self.assertEqual(client.chat.completions.create.call_count, 2)

    def test_401_is_not_retried(self):
        client = Mock()
        client.chat.completions.create.side_effect = make_status_error(401)

        with patch.object(routes.time, "sleep") as sleep_mock:
            with self.assertRaises(APIStatusError):
                routes.call_model_with_retry(
                    client, "gemma3:1b", [], 0.1
                )

        self.assertEqual(client.chat.completions.create.call_count, 1)
        sleep_mock.assert_not_called()

    def test_retry_after_header_is_honored(self):
        client = Mock()
        client.chat.completions.create.side_effect = [
            make_status_error(429, {"Retry-After": "5"}),
            "success",
        ]

        with (
            patch.object(routes.time, "sleep") as sleep_mock,
            patch.object(routes.random, "uniform", return_value=1.0),
        ):
            routes.call_model_with_retry(
                client, "gemma3:1b", [], 0.1
            )

        sleep_mock.assert_called_once_with(5.0)

    def test_disabled_ai_returns_deterministic_fallback(self):
        with patch.dict(
            os.environ,
            {"LLM_ENABLED": "false", "LLM_STUB": "0"},
        ):
            with patch.object(routes, "OpenAI") as openai_mock:
                result = routes.triage_ticket(
                    routes.TriageRequest(text="My payment failed.")
                )

        self.assertEqual(result.category, routes.Category.other)
        self.assertEqual(result.urgency, routes.Urgency.normal)
        self.assertEqual(result.confidence, 0.0)
        openai_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
