"""Tests de la conversation analyste (ai.chat) — réseau entièrement simulé."""

from __future__ import annotations

import io
import json
import os
import unittest
import urllib.error
from unittest import mock

from geocapital import ai
from tests.test_ai_config import _FakeResponse, MockedEnvTestCase, completions_payload


class TestChat(MockedEnvTestCase):
    def test_chat_parses_valid_multi_turn_response(self):
        os.environ["OPENROUTER_API_KEY"] = "sk-or-test-value"
        messages = [
            {"role": "system", "content": "Règles."},
            {"role": "user", "content": "Question 1"},
            {"role": "assistant", "content": "Réponse 1"},
            {"role": "user", "content": "Question 2"},
        ]
        response = _FakeResponse(
            json.dumps(completions_payload("Voici l'interprétation.")).encode("utf-8")
        )
        with mock.patch("urllib.request.urlopen", return_value=response) as mocked:
            result = ai.chat(messages)
        self.assertEqual(result, "Voici l'interprétation.")
        body = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        self.assertEqual([m["role"] for m in body["messages"]], ["system", "user", "assistant", "user"])
        self.assertEqual(body["model"], "openai/gpt-4o")

    def test_chat_without_key_skips_network(self):
        with mock.patch("urllib.request.urlopen") as mocked:
            self.assertIsNone(ai.chat([{"role": "user", "content": "Q"}]))
        mocked.assert_not_called()

    def test_chat_empty_messages_returns_none(self):
        self.assertIsNone(ai.chat([]))

    def test_chat_http_error_returns_none(self):
        error = urllib.error.HTTPError(
            url=ai.API_URL, code=503, msg="Service Unavailable", hdrs=None, fp=None
        )
        with mock.patch("urllib.request.urlopen", side_effect=error):
            self.assertIsNone(
                ai.chat([{"role": "user", "content": "Q"}])
            )

    def test_chat_timeout_returns_none(self):
        with mock.patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            self.assertIsNone(
                ai.chat([{"role": "user", "content": "Q"}])
            )

    def test_chat_invalid_json_returns_none(self):
        response = _FakeResponse(b"not json")
        with mock.patch("urllib.request.urlopen", return_value=response):
            self.assertIsNone(
                ai.chat([{"role": "user", "content": "Q"}])
            )

    def test_chat_respects_custom_token_limit(self):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return _FakeResponse(json.dumps(completions_payload()).encode("utf-8"))

        os.environ["OPENROUTER_API_KEY"] = "sk-or-test-value"
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            ai.chat([{"role": "user", "content": "Q"}], max_tokens=350)
        self.assertEqual(captured["body"]["max_tokens"], 350)


if __name__ == "__main__":
    unittest.main()
