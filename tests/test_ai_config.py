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

ENV_KEYS = ["OPENROUTER_API_KEY", "GEOCAPITAL_MODEL", "LLM_MODEL", "LLM_BASE_URL"]


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
        self.assertEqual(captured["body"]["max_tokens"], 700 + ai.REASONING_HEADROOM)  # 700 visibles + marge de réflexion
        roles = [message["role"] for message in captured["body"]["messages"]]
        self.assertEqual(roles, ["system", "user"])
        self.assertIn("Authorization", captured["headers"])
        self.assertIn("Content-Type", captured["headers"])


class TestLlmSettings(MockedEnvTestCase):
    """LLM_MODEL / LLM_BASE_URL (ex. modèle gratuit « openrouter/free »)."""

    def _request_for(self):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["headers"] = {key.title(): value for key, value in request.header_items()}
            return _FakeResponse(json.dumps(completions_payload("ok")).encode("utf-8"))

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            self.assertEqual(ai._call("Q"), "ok")
        return captured

    def test_defaults_are_unchanged(self):
        self.assertEqual(ai.api_base_url(), "https://openrouter.ai/api/v1")
        self.assertEqual(ai.api_url(), ai.API_URL)
        self.assertEqual(ai.api_model(), "openai/gpt-4o")

    def test_llm_model_selects_the_free_model(self):
        os.environ["LLM_MODEL"] = "openrouter/free"
        self.assertEqual(ai.api_model(), "openrouter/free")

    def test_llm_model_wins_over_legacy_name(self):
        os.environ["LLM_MODEL"] = "openrouter/free"
        os.environ["GEOCAPITAL_MODEL"] = "openai/gpt-4o"
        self.assertEqual(ai.api_model(), "openrouter/free")

    def test_blank_llm_model_falls_back_to_legacy_then_default(self):
        os.environ["LLM_MODEL"] = "   "
        os.environ["GEOCAPITAL_MODEL"] = "openai/gpt-4o-mini"
        self.assertEqual(ai.api_model(), "openai/gpt-4o-mini")
        os.environ.pop("GEOCAPITAL_MODEL")
        self.assertEqual(ai.api_model(), ai.DEFAULT_MODEL)

    def test_dotenv_style_lines_are_parsed(self):
        values = ai._parse_env("LLM_BASE_URL=https://openrouter.ai/api/v1\nLLM_MODEL=openrouter/free\n")
        self.assertEqual(values["LLM_BASE_URL"], "https://openrouter.ai/api/v1")
        self.assertEqual(values["LLM_MODEL"], "openrouter/free")

    def test_streamlit_secrets_are_used_when_env_is_empty(self):
        secrets = {"LLM_MODEL": "openrouter/free", "LLM_BASE_URL": "https://openrouter.ai/api/v1/"}
        with mock.patch.object(ai, "_from_secrets", side_effect=lambda name: secrets.get(name, "")):
            self.assertEqual(ai.api_model(), "openrouter/free")
            self.assertEqual(ai.api_base_url(), "https://openrouter.ai/api/v1")  # « / » final retiré

    def test_environment_wins_over_secrets(self):
        os.environ["LLM_MODEL"] = "openai/gpt-4o-mini"
        with mock.patch.object(ai, "_from_secrets", return_value="openrouter/free"):
            self.assertEqual(ai.api_model(), "openai/gpt-4o-mini")

    def test_custom_https_base_url_is_used_without_trailing_slash(self):
        os.environ["LLM_BASE_URL"] = "https://llm.example.org/v1/"
        self.assertEqual(ai.api_base_url(), "https://llm.example.org/v1")
        self.assertEqual(ai.api_url(), "https://llm.example.org/v1/chat/completions")

    def test_unsafe_base_urls_fall_back_to_default(self):
        for bad in ("http://evil.example.org/v1", "ftp://x/v1", "https://", "javascript:alert(1)", "openrouter.ai/api/v1"):
            os.environ["LLM_BASE_URL"] = bad
            self.assertEqual(ai.api_base_url(), ai.DEFAULT_BASE_URL, bad)

    def test_local_http_is_tolerated(self):
        os.environ["LLM_BASE_URL"] = "http://localhost:11434/v1"
        self.assertEqual(ai.api_base_url(), "http://localhost:11434/v1")

    def test_request_with_the_free_model_settings(self):
        os.environ["OPENROUTER_API_KEY"] = "sk-or-test-value"
        os.environ["LLM_BASE_URL"] = "https://openrouter.ai/api/v1"
        os.environ["LLM_MODEL"] = "openrouter/free"
        sent = self._request_for()
        self.assertEqual(sent["url"], "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(sent["body"]["model"], "openrouter/free")
        self.assertTrue(sent["headers"]["Authorization"].startswith("Bearer "))

    def test_request_goes_to_the_configured_base_url(self):
        os.environ["OPENROUTER_API_KEY"] = "sk-or-test-value"
        os.environ["LLM_BASE_URL"] = "https://llm.example.org/v1"
        self.assertEqual(self._request_for()["url"], "https://llm.example.org/v1/chat/completions")

    def test_unsafe_base_url_never_receives_the_key(self):
        os.environ["OPENROUTER_API_KEY"] = "sk-or-test-value"
        os.environ["LLM_BASE_URL"] = "http://evil.example.org/v1"
        self.assertEqual(self._request_for()["url"], ai.API_URL)


class TestEmptyOrOddReplies(MockedEnvTestCase):
    """Une réponse vide ne doit jamais s'afficher comme « None » (modèles gratuits / raisonnement)."""

    def _answer_for(self, message, finish_reason="stop"):
        body = json.dumps({"choices": [{"message": message, "finish_reason": finish_reason}]}).encode("utf-8")
        os.environ["OPENROUTER_API_KEY"] = "sk-or-test-value"
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(body)):
            return ai._call("Q")

    def test_null_content_is_not_the_string_none(self):
        self.assertIsNone(self._answer_for({"role": "assistant", "content": None, "reasoning": "..."}, "length"))

    def test_missing_content_is_none(self):
        self.assertIsNone(self._answer_for({"role": "assistant"}))

    def test_blank_content_is_none(self):
        self.assertIsNone(self._answer_for({"role": "assistant", "content": "   \n"}))

    def test_literal_none_or_null_text_is_treated_as_empty(self):
        for literal in ("None", "none", "null", " NULL "):
            self.assertIsNone(self._answer_for({"role": "assistant", "content": literal}), literal)

    def test_text_parts_are_joined(self):
        parts = [{"type": "text", "text": "Bonjour"}, {"type": "text", "text": " monde"}]
        self.assertEqual(self._answer_for({"role": "assistant", "content": parts}), "Bonjour monde")

    def test_non_text_parts_are_ignored(self):
        parts = [{"type": "image_url", "image_url": {"url": "x"}}, {"type": "text", "text": "ok"}]
        self.assertEqual(self._answer_for({"role": "assistant", "content": parts}), "ok")

    def test_normal_text_is_unchanged(self):
        self.assertEqual(self._answer_for({"role": "assistant", "content": "  Analyse.  "}), "Analyse.")

    def test_no_choices_or_bad_message_shape_is_none(self):
        os.environ["OPENROUTER_API_KEY"] = "sk-or-test-value"
        for body in ({"choices": []}, {"choices": [{"message": None}]}, {"choices": [{"message": "x"}]}, {}):
            with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(json.dumps(body).encode("utf-8"))):
                self.assertIsNone(ai._call("Q"), body)

    def test_chat_returns_none_on_null_content_so_the_page_can_fall_back(self):
        body = json.dumps({"choices": [{"message": {"role": "assistant", "content": None}}]}).encode("utf-8")
        os.environ["OPENROUTER_API_KEY"] = "sk-or-test-value"
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(body)):
            self.assertIsNone(ai.chat([{"role": "user", "content": "Explique le verdict de la France"}]))


class TestDiagnostics(MockedEnvTestCase):
    """last_error() : cause réelle d'un échec, sans jamais exposer la clé API."""

    KEY = "sk-or-v1-supersecretvalue1234567890"

    def setUp(self):
        super().setUp()
        os.environ["OPENROUTER_API_KEY"] = self.KEY

    def _http_error(self, code, body):
        raw = json.dumps(body).encode("utf-8") if not isinstance(body, bytes) else body
        return urllib.error.HTTPError(url=ai.API_URL, code=code, msg="Err", hdrs=None, fp=io.BytesIO(raw))

    def _fail_with(self, exc):
        with mock.patch("urllib.request.urlopen", side_effect=exc):
            self.assertIsNone(ai._call("Q"))
        return ai.last_error()

    def test_http_402_payment_message_is_reported(self):
        err = self._fail_with(self._http_error(402, {"error": {"message": "Insufficient credits", "code": 402}}))
        self.assertEqual(err, "HTTP 402: Insufficient credits")

    def test_http_404_data_policy_message_is_reported(self):
        msg = "No endpoints found matching your data policy (Free model publication)"
        self.assertIn("HTTP 404", self._fail_with(self._http_error(404, {"error": {"message": msg}})))
        self.assertIn("data policy", ai.last_error())

    def test_http_429_rate_limit_is_reported(self):
        err = self._fail_with(self._http_error(429, {"error": {"message": "Rate limit exceeded: free-models-per-day"}}))
        self.assertTrue(err.startswith("HTTP 429: Rate limit"))

    def test_http_error_without_json_body_keeps_the_code(self):
        err = self._fail_with(self._http_error(502, b"<html>Bad gateway</html>"))
        self.assertTrue(err.startswith("HTTP 502"))

    def test_http_error_without_body_at_all(self):
        exc = urllib.error.HTTPError(url=ai.API_URL, code=401, msg="Unauthorized", hdrs=None, fp=None)
        self.assertEqual(self._fail_with(exc), "HTTP 401: Unauthorized")

    def test_network_and_timeout_are_distinguished(self):
        self.assertIn("network error", self._fail_with(urllib.error.URLError("connection refused")))
        self.assertIn("timeout", self._fail_with(TimeoutError()))

    def test_unreadable_response(self):
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(b"not json")):
            self.assertIsNone(ai._call("Q"))
        self.assertIn("unreadable response", ai.last_error())

    def test_error_body_with_http_200_is_reported(self):
        body = json.dumps({"error": {"message": "Provider returned error", "code": 502}}).encode("utf-8")
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(body)):
            self.assertIsNone(ai._call("Q"))
        self.assertEqual(ai.last_error(), "API error: Provider returned error")

    def test_empty_content_with_length_is_explained(self):
        body = json.dumps({"choices": [{"message": {"content": None}, "finish_reason": "length"}]}).encode("utf-8")
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(body)):
            self.assertIsNone(ai._call("Q"))
        self.assertIn("token budget", ai.last_error())
        self.assertIn("finish_reason=length", ai.last_error())

    def test_empty_content_without_length_and_no_choices(self):
        body = json.dumps({"choices": [{"message": {"content": ""}, "finish_reason": "stop"}]}).encode("utf-8")
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(body)):
            ai._call("Q")
        self.assertIn("finish_reason=stop", ai.last_error())
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(b'{"choices": []}')):
            ai._call("Q")
        self.assertIn("no choices", ai.last_error())

    def test_missing_key_is_reported(self):
        os.environ.pop("OPENROUTER_API_KEY")
        with mock.patch("urllib.request.urlopen") as mocked:
            self.assertIsNone(ai._call("Q"))
        mocked.assert_not_called()
        self.assertEqual(ai.last_error(), "no API key")

    def test_success_clears_the_previous_error(self):
        self._fail_with(TimeoutError())
        self.assertTrue(ai.last_error())
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(json.dumps(completions_payload("ok")).encode("utf-8"))):
            self.assertEqual(ai._call("Q"), "ok")
        self.assertEqual(ai.last_error(), "")

    def test_the_api_key_is_never_exposed_even_if_the_provider_echoes_it(self):
        echoed = {"error": {"message": f"Invalid key {self.KEY} for this request"}}
        err = self._fail_with(self._http_error(401, echoed))
        self.assertNotIn(self.KEY, err)
        self.assertIn("***", err)

    def test_message_is_bounded_and_single_line(self):
        err = self._fail_with(self._http_error(500, {"error": {"message": "line one\n\n" + "x" * 1000}}))
        self.assertLessEqual(len(err), 240)
        self.assertNotIn("\n", err)


class TestAnalystShowsTheReason(MockedEnvTestCase):
    """La page Analyste affiche la vraie cause quand la clé est présente mais l'appel échoue."""

    def _ask(self, side_effect=None, return_value=None):
        from pathlib import Path

        from streamlit.testing.v1 import AppTest

        root = Path(__file__).resolve().parent.parent
        os.environ["OPENROUTER_API_KEY"] = "sk-or-v1-supersecretvalue1234567890"
        os.environ["LLM_MODEL"] = "nvidia/nemotron-3.5-super-vl:free"
        with mock.patch("urllib.request.urlopen", side_effect=side_effect, return_value=return_value):
            at = AppTest.from_file(str(root / "app.py"), default_timeout=120)
            at.session_state["nav"] = "analyst"
            at.run()
            at.chat_input[0].set_value("Explique le verdict de la France").run()
        self.assertFalse(bool(at.exception), at.exception)
        return "\n".join(m.value for m in at.markdown)

    def test_reason_and_model_are_shown_on_failure(self):
        exc = urllib.error.HTTPError(
            url=ai.API_URL, code=404, msg="x", hdrs=None,
            fp=io.BytesIO(json.dumps({"error": {"message": "No endpoints found matching your data policy"}}).encode("utf-8")),
        )
        shown = self._ask(side_effect=exc)
        self.assertIn("Détail technique : HTTP 404: No endpoints found matching your data policy", shown)
        self.assertIn("modèle : nvidia/nemotron-3.5-super-vl:free", shown)
        self.assertNotIn("sk-or-v1-supersecretvalue", shown)
        self.assertIn("Faits validés", shown)  # le repli éditorial reste fourni

    def test_empty_reply_reason_is_shown(self):
        body = json.dumps({"choices": [{"message": {"content": None}, "finish_reason": "length"}]}).encode("utf-8")
        shown = self._ask(return_value=_FakeResponse(body))
        self.assertIn("token budget", shown)

    def test_no_reason_line_on_success(self):
        body = json.dumps(completions_payload("France : investir avec prudence.")).encode("utf-8")
        shown = self._ask(return_value=_FakeResponse(body))
        self.assertNotIn("Détail technique", shown)
        self.assertIn("Interprétation IA", shown)


class TestReasoningHeadroom(MockedEnvTestCase):
    """Les modèles « raisonnement » (ex. modèles gratuits) ont besoin de jetons pour réfléchir."""

    def _capture(self, call):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return _FakeResponse(json.dumps(completions_payload("ok")).encode("utf-8"))

        os.environ["OPENROUTER_API_KEY"] = "sk-or-test-value"
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            self.assertEqual(call(), "ok")
        return captured

    def test_constants_leave_real_room_to_think(self):
        self.assertGreaterEqual(ai.REASONING_HEADROOM, 2000)
        self.assertEqual(ai.MAX_TOKENS, 700)  # la longueur visible visée ne change pas
        self.assertGreaterEqual(ai.REQUEST_TIMEOUT, 60)

    def test_call_sends_visible_budget_plus_headroom(self):
        sent = self._capture(lambda: ai._call("Q"))
        self.assertEqual(sent["body"]["max_tokens"], ai.MAX_TOKENS + ai.REASONING_HEADROOM)

    def test_every_helper_gets_the_headroom(self):
        country = {"name": "Maroc", "indicators": {}}
        score = {"score": 6.5, "verdict": "Modéré"}
        for call, visible in (
            (lambda: ai.country_brief(country, score), 700),
            (lambda: ai.explain_verdict(country, score), 500),
            (lambda: ai.decode_event({"title": "t"}, country), 550),
            (lambda: ai.portfolio_commentary([], {}), 500),
            (lambda: ai.explain_quiz(country, {"question": "Q", "options": ["a", "b"], "answer": 0}, True), 350),
        ):
            sent = self._capture(call)
            self.assertEqual(sent["body"]["max_tokens"], visible + ai.REASONING_HEADROOM)

    def test_chat_gets_the_headroom(self):
        sent = self._capture(lambda: ai.chat([{"role": "user", "content": "Q"}]))
        self.assertEqual(sent["body"]["max_tokens"], ai.MAX_TOKENS + ai.REASONING_HEADROOM)

    def test_caller_payload_is_not_mutated(self):
        payload = {"model": "m", "max_tokens": 100, "messages": []}
        os.environ["OPENROUTER_API_KEY"] = "sk-or-test-value"
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(json.dumps(completions_payload("ok")).encode("utf-8"))):
            ai._post(payload)
        self.assertEqual(payload["max_tokens"], 100)

    def test_payload_without_max_tokens_is_left_alone(self):
        sent = {}

        def fake_urlopen(request, timeout=None):
            sent["body"] = json.loads(request.data.decode("utf-8"))
            return _FakeResponse(json.dumps(completions_payload("ok")).encode("utf-8"))

        os.environ["OPENROUTER_API_KEY"] = "sk-or-test-value"
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            ai._post({"model": "m", "messages": []})
        self.assertNotIn("max_tokens", sent["body"])

    def test_longer_timeout_is_used(self):
        sent = self._capture(lambda: ai._call("Q"))
        self.assertEqual(sent["timeout"], ai.REQUEST_TIMEOUT)

    def test_timeout_message_mentions_the_actual_limit(self):
        os.environ["OPENROUTER_API_KEY"] = "sk-or-test-value"
        with mock.patch("urllib.request.urlopen", side_effect=TimeoutError()):
            self.assertIsNone(ai._call("Q"))
        self.assertIn(f"{ai.REQUEST_TIMEOUT} s", ai.last_error())

    def test_reasoning_style_reply_with_text_is_accepted(self):
        body = json.dumps({"choices": [{"message": {"role": "assistant", "content": "France : investir avec prudence.", "reasoning": "réflexion interne très longue"}, "finish_reason": "stop"}]}).encode("utf-8")
        os.environ["OPENROUTER_API_KEY"] = "sk-or-test-value"
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(body)):
            answer = ai._call("Q")
        self.assertEqual(answer, "France : investir avec prudence.")
        self.assertNotIn("réflexion", answer)  # le raisonnement interne n'est jamais affiché

    def test_length_failure_reports_the_budget_used(self):
        body = json.dumps({"choices": [{"message": {"content": None}, "finish_reason": "length"}]}).encode("utf-8")
        os.environ["OPENROUTER_API_KEY"] = "sk-or-test-value"
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse(body)):
            self.assertIsNone(ai._call("Q"))
        self.assertIn(f"budget {ai.MAX_TOKENS + ai.REASONING_HEADROOM}", ai.last_error())


if __name__ == "__main__":
    unittest.main()
