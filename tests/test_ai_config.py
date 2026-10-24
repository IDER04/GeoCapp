"""Tests de la couche IA GeoCapital (OpenRouter).

Tout appel réseau est simulé : aucun appel API réel n'est jamais effectué.
Lancer avec : python -m unittest discover -s tests
"""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
import urllib.error
from unittest import mock

from geocapital import ai

ENV_KEYS = ["OPENROUTER_API_KEY", "GEOCAPITAL_MODEL"]


def save_env():
    return {key: os.environ.get(key) for key in ENV_KEYS}


def restore_env(saved):
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


class _FakeResponse(io.BytesIO):
    buffer_name = None
    mode = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def completions_payload(text="Voici l'analyse demandée."):
    return {
        "choices": [
            {"message": {"role": "assistant", "content": text}}
        ]
    }


class MockedEnvTestCase(unittest.TestCase):
    """Empêche les tests de toucher la vraie clé ou le vrai réseau."""

    def setUp(self):
        self._saved = save_env()
        for key in ENV_KEYS:
            os.environ.pop(key, None)

    def tearDown(self):
        restore_env(self._saved)


class TestConfiguration(MockedEnvTestCase):
    def test_default_model_when_unconfigured(self):
        self.assertEqual(ai.api_model(), ai.DEFAULT_MODEL)
        self.assertEqual(ai.DEFAULT_MODEL, "openai/gpt-4o")

    def test_model_from_environment(self):
        os.environ["GEOCAPITAL_MODEL"] = "openai/gpt-4o-mini"
        self.assertEqual(ai.api_model(), "openai/gpt-4o-mini")

    def test_model_falls_back_after_empty_value(self):
        os.environ["GEOCAPITAL_MODEL"] = "   "
        self.assertEqual(ai.api_model(), ai.DEFAULT_MODEL)

    def test_key_from_environment(self):
        os.environ["OPENROUTER_API_KEY"] = "sk-or-test-value"
        self.assertTrue(ai.is_available())
        self.assertEqual(ai.api_key(), "sk-or-test-value")

    def test_missing_key_is_not_available(self):
        self.assertFalse(ai.is_available())
        self.assertIsNone(ai.api_key())

    def test_env_file_parsed_in_isolation(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".env", delete=False, encoding="utf-8"
        ) as handle:
            handle.write(
                "OPENROUTER_API_KEY = 'sk-or-from-file'\n"
                "# un commentaire\n"
                "GEOCAPITAL_MODEL=\"openai/gpt-4o\"\n"
                "travail=" ""
                "\n\n"
            )
            path = handle.name
        try:
            parsed = ai._parse_env(open(path, encoding="utf-8").read())
            self.assertEqual(parsed.get("OPENROUTER_API_KEY"), "sk-or-from-file")
            self.assertEqual(parsed.get("GEOCAPITAL_MODEL"), "openai/gpt-4o")
            ai._load_dotenv(path)
            self.assertEqual(os.environ.get("OPENROUTER_API_KEY"), "sk-or-from-file")
        finally:
            os.unlink(path)

    def test_loaded_env_values_do_not_override_real_environment(self):
        os.environ["GEOCAPITAL_MODEL"] = "openai/gpt-4o-mini"
        with tempfile.NamedTemporaryFile(
            "w", suffix=".env", delete=False, encoding="utf-8"
        ) as handle:
            handle.write("GEOCAPITAL_MODEL=openai/gpt-3.5-turbo\n")
            path = handle.name
        try:
            ai._load_dotenv(path)
            self.assertEqual(os.environ["GEOCAPITAL_MODEL"], "openai/gpt-4o-mini")
        finally:
            os.unlink(path)


class TestResponseParsing(MockedEnvTestCase):
    def test_parses_openai_compatible_response(self):
        response = _FakeResponse(json.dumps(completions_payload()).encode("utf-8"))
        with mock.patch("urllib.request.urlopen", return_value=response):
            os.environ["OPENROUTER_API_KEY"] = "sk-or-test-value"
            result = ai._call("Explique ce verdict.")
        self.assertEqual(result, "Voici l'analyse demandée.")

    def test_strips_whitespace_from_content(self):
        response = _FakeResponse(
            json.dumps(completions_payload("  bonjour  \n")).encode("utf-8")
        )
        with mock.patch("urllib.request.urlopen", return_value=response):
            os.environ["OPENROUTER_API_KEY"] = "sk-or-test-value"
            result = ai._call("Explique ce verdict.")
        self.assertEqual(result, "bonjour")

    def test_empty_choices_returns_none(self):
        response = _FakeResponse(json.dumps({"choices": []}).encode("utf-8"))
        with mock.patch("urllib.request.urlopen", return_value=response):
            os.environ["OPENROUTER_API_KEY"] = "sk-or-test-value"
            self.assertIsNone(ai._call("Explique ce verdict."))

    def test_empty_content_returns_none(self):
        response = _FakeResponse(
            json.dumps(completions_payload("")).encode("utf-8")
        )
        with mock.patch("urllib.request.urlopen", return_value=response):
            os.environ["OPENROUTER_API_KEY"] = "sk-or-test-value"
            self.assertIsNone(ai._call("Explique ce verdict."))

    def test_invalid_json_returns_none(self):
        response = _FakeResponse(b"<html>not json</html>")
        with mock.patch("urllib.request.urlopen", return_value=response):
            os.environ["OPENROUTER_API_KEY"] = "sk-or-test-value"
            self.assertIsNone(ai._call("Explique ce verdict."))


class TestApiErrors(MockedEnvTestCase):
    def _assert_graceful(self, side_effect):
        with mock.patch("urllib.request.urlopen", side_effect=side_effect):
            os.environ["OPENROUTER_API_KEY"] = "sk-or-test-value"
            self.assertIsNone(ai._call("Explique ce verdict."))

    def test_http_error_401_invalid_key(self):
        error = urllib.error.HTTPError(
            url=ai.API_URL, code=401, msg="Unauthorized", hdrs=None, fp=None
        )
        self._assert_graceful(error)

    def test_http_error_404_invalid_model(self):
        error = urllib.error.HTTPError(
            url=ai.API_URL, code=404, msg="Not Found", hdrs=None, fp=None
        )
        self._assert_graceful(error)

    def test_http_error_500_server_fault(self):
        error = urllib.error.HTTPError(
            url=ai.API_URL, code=500, msg="Server Error", hdrs=None, fp=None
        )
        self._assert_graceful(error)

    def test_url_error_network_down(self):
        self._assert_graceful(urllib.error.URLError("connection refused"))

    def test_timeout(self):
        self._assert_graceful(TimeoutError("timed out"))

    def test_unexpected_shape_is_handled(self):
        response = _FakeResponse(json.dumps({"error": "quota"}).encode("utf-8"))
        with mock.patch("urllib.request.urlopen", return_value=response):
            os.environ["OPENROUTER_API_KEY"] = "sk-or-test-value"
            self.assertIsNone(ai._call("Explique ce verdict."))


class TestFallbackBehaviour(MockedEnvTestCase):
    def test_missing_key_skips_network_and_returns_none(self):
        with mock.patch("urllib.request.urlopen") as mocked:
            result = ai._call("Explique ce verdict.")
        mocked.assert_not_called()
        self.assertIsNone(result)

    def test_prompt_functions_return_none_without_key(self):
        with mock.patch("urllib.request.urlopen") as mocked:
            country = {"name": "Maroc"}
            score = {"score": 6.5, "verdict": "Modéré"}
            question = {"question": "Q", "options": ["a", "b"], "answer": 0}
            self.assertIsNone(ai.country_brief(country, score))
            self.assertIsNone(ai.explain_verdict(country, score))
            self.assertIsNone(ai.decode_event({"title": "t"}, country))
            self.assertIsNone(ai.portfolio_commentary([], {}))
            self.assertIsNone(ai.explain_quiz(country, question, True))
        mocked.assert_not_called()


class TestRequestPayload(MockedEnvTestCase):
    """Vérifie le format de la requête envoyée à OpenRouter."""

    def test_request_carries_openai_compatible_payload(self):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["headers"] = {key.title(): value for key, value in request.header_items()}
            return _FakeResponse(json.dumps(completions_payload()).encode("utf-8"))

        os.environ["OPENROUTER_API_KEY"] = "sk-or-test-value"
        os.environ["GEOCAPITAL_MODEL"] = "openai/gpt-4o-mini"
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            self.assertEqual(ai._call("Explique ce verdict."), "Voici l'analyse demandée.")

        self.assertEqual(captured["url"], ai.API_URL)
        self.assertIn("openrouter.ai/api/v1/chat/completions", captured["url"])
        self.assertEqual(captured["body"]["model"], "openai/gpt-4o-mini")
        self.assertEqual(captured["body"]["max_tokens"], 700)
        roles = [message["role"] for message in captured["body"]["messages"]]
        self.assertEqual(roles, ["system", "user"])
        self.assertIn("Authorization", captured["headers"])
        self.assertIn("Content-Type", captured["headers"])


if __name__ == "__main__":
    unittest.main()
