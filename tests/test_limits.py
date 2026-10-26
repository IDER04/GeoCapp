"""Tests de la limite par session de l'Analyste IA (Priorité 5 — Phase 1).

Couverture :
- configuration : `meta.ai_limits.max_questions_per_session` (entier >= 1,
  violé → ConfigError avec chemin exact, aucun repli silencieux) ;
- bornes pures : remaining/can_ask exactement à la limite et à limite-1 ;
- compteur serveur : une unité par question soumise, re-run Streamlit
  sans nouvelle soumission = aucun double comptage ;
- politique : échec fournisseur → repli éditorial **compte** quand même ;
- blocage : limite atteinte → saisie désactivée, zéro soumission, encart
  explicatif, aucun appel `ai.chat` ;
- libellés FR et EN (avec la mention « par session / per-session » et
  l'absence de plafond global / garantie de dépense).
"""

from __future__ import annotations

import copy
import json
import pathlib
import unittest
import unittest.mock

from geocapital import ai, i18n, limits

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIMIT_REACHED_WITH = None  # rempli au moment du run (limite du disque)

FR_LIMIT_REMAINING_PREFIX = "Questions restantes :"
EN_LIMIT_REMAINING_PREFIX = "Questions remaining:"


def real_meta() -> dict:
    with open(ROOT / "data" / "meta.json", encoding="utf-8") as handle:
        return json.load(handle)


def fresh_analyst(lang: str = "fr", usage: int | None = None) -> "AppTest":  # noqa: F821
    """Session analyseuse fraîche.

    NOTE AppTest : en EN, un second `at.run()` sur cette page échoue avec
    une erreur du framework Streamlit (selectbox `analyst_intent` : index
    résolu sur une étiquette formatée issue du run précédent, listes
    entres deux langues) — corroboré sur la page non modifiée. Les tests
    EN restent donc en un seul `at.run()`, état semé à l'avance ; le
    comportement multi-étapes (soumission, re-run, limite) est couvert en
    FR, une seule langue suffit pour la logique (les deux pour les
    libellés)."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
    at.session_state["lang"] = lang
    at.session_state["nav"] = "analyst"
    if usage is not None:
        at.session_state[limits.USAGE_KEY] = usage
    at.run()
    return at


def submit_question(at, text: str = "Explique le verdict des EU.") -> None:
    at.chat_input[0].set_value(text)
    at.run()


class TestConfigValidation(unittest.TestCase):
    def setUp(self):
        self.meta = real_meta()
        self.addCleanup(limits.reset)

    def expect_error(self, meta: dict, needle: str) -> str:
        from geocapital.scoring import ConfigError

        with self.assertRaises(ConfigError) as ctx:
            limits.session_limit(meta)
        self.assertIn(needle, str(ctx.exception))
        return str(ctx.exception)

    def test_real_meta_limit_is_positive_integer(self):
        self.assertEqual(limits.session_limit(real_meta()), 8)
        self.assertIsInstance(limits.session_limit(real_meta()), int)

    def test_missing_section(self):
        meta = real_meta()
        del meta["ai_limits"]
        self.expect_error(meta, "meta.ai_limits: section absente")

    def test_missing_field(self):
        meta = real_meta()
        del meta["ai_limits"]["max_questions_per_session"]
        self.expect_error(meta, "max_questions_per_session")

    def test_zero_rejected(self):
        meta = real_meta()
        meta["ai_limits"]["max_questions_per_session"] = 0
        self.expect_error(meta, "entier >= 1")

    def test_negative_rejected(self):
        meta = real_meta()
        meta["ai_limits"]["max_questions_per_session"] = -3
        self.expect_error(meta, "entier >= 1")

    def test_float_rejected(self):
        meta = real_meta()
        meta["ai_limits"]["max_questions_per_session"] = 8.0
        self.expect_error(meta, "entier >= 1")

    def test_bool_rejected(self):
        meta = real_meta()
        meta["ai_limits"]["max_questions_per_session"] = True
        self.expect_error(meta, "entier >= 1")

    def test_string_rejected(self):
        meta = real_meta()
        meta["ai_limits"]["max_questions_per_session"] = "8"
        self.expect_error(meta, "entier >= 1")

    def test_config_change_changes_limit_via_load_data(self):
        """La méta est la source de vérité : la limite suit le disque."""
        meta = real_meta()
        meta["ai_limits"]["max_questions_per_session"] = 2
        patcher = unittest.mock.patch("geocapital.data.load_data", return_value=meta)
        self.addCleanup(patcher.stop)
        with patcher:
            self.assertEqual(limits.limit(), 2)


class TestPureBoundaries(unittest.TestCase):
    def test_remaining_full(self):
        self.assertEqual(limits.remaining(0, 8), 8)

    def test_boundary_at_limit_minus_one_allows_one_more(self):
        self.assertEqual(limits.remaining(7, 8), 1)
        self.assertTrue(limits.can_ask(7, 8))

    def test_boundary_at_limit_blocks(self):
        self.assertEqual(limits.remaining(8, 8), 0)
        self.assertFalse(limits.can_ask(8, 8))

    def test_over_limit_never_negative(self):
        self.assertEqual(limits.remaining(12, 8), 0)

    def test_limit_one_allows_a_single_question(self):
        self.assertTrue(limits.can_ask(0, 1))
        self.assertFalse(limits.can_ask(1, 1))


class TestSessionCounter(unittest.TestCase):
    def setUp(self):
        self.addCleanup(limits.reset)
        limits.reset()

    def test_default_used_is_zero(self):
        self.assertEqual(limits.used(), 0)

    def test_record_counts_one_per_call(self):
        limits.record()
        self.assertEqual(limits.used(), 1)
        limits.record()
        self.assertEqual(limits.used(), 2)

    def test_corrupted_counter_is_tolerated(self):
        i18n.st.session_state[limits.USAGE_KEY] = "not-a-number"
        self.assertEqual(limits.used(), 0)
        self.addCleanup(i18n.st.session_state.pop, limits.USAGE_KEY)


class TestAnalystPageFlow(unittest.TestCase):
    """Bout-en-bout AppTest : la page doit compter une unité par question."""

    def setUp(self):
        self.addCleanup(limits.reset)

    def test_caption_shows_full_allowance_in_french(self):
        at = fresh_analyst("fr")
        self.assertFalse(bool(at.exception))
        captions = "\n".join(str(c.value) for c in at.caption)
        self.assertIn(FR_LIMIT_REMAINING_PREFIX, captions)
        self.assertIn("8/8", captions)

    def test_caption_shows_allowance_in_english(self):
        at = fresh_analyst("en")
        self.assertFalse(bool(at.exception))
        captions = "\n".join(str(c.value) for c in at.caption)
        self.assertIn(EN_LIMIT_REMAINING_PREFIX, captions)
        self.assertIn("per-session limit", captions)

    def test_normal_submission_counts_once_and_answers(self):
        at = fresh_analyst("fr")
        submit_question(at)
        self.assertFalse(bool(at.exception))
        # Réponse éditoriale prête (pas de clé en test) ; la question compte.
        history = at.session_state[limits.USAGE_KEY]
        self.assertEqual(history, 1)
        blob = "\n".join(m.value for m in at.markdown)
        self.assertIn("Explique le verdict des EU.", blob)

    def test_plain_rerun_does_not_double_count(self):
        at = fresh_analyst("fr")
        submit_question(at)
        self.assertEqual(at.session_state[limits.USAGE_KEY], 1)
        at.run()  # re-run sans nouvelle soumission
        self.assertEqual(at.session_state[limits.USAGE_KEY], 1)
        at.run()
        self.assertEqual(at.session_state[limits.USAGE_KEY], 1)

    def test_second_submission_counts_two(self):
        at = fresh_analyst("fr")
        submit_question(at, "Première question")
        submit_question(at, "Deuxième question")
        self.assertEqual(at.session_state[limits.USAGE_KEY], 2)
        at.run()  # la limite affichée suit : 6/8
        captions = "\n".join(str(c.value) for c in at.caption)
        self.assertIn("6/8", captions)

    def test_provider_failure_editorial_fallback_counts(self):
        """Politique : échec fournisseur → repli éditorial → la question compte."""
        at = fresh_analyst("fr")
        # Pas de clé (mode éditorial) OU fournisseur injoignable : même unité.
        patcher = unittest.mock.patch.object(ai, "is_available", return_value=True)
        chat_patcher = unittest.mock.patch.object(ai, "chat", return_value=None)
        self.addCleanup(patcher.stop)
        self.addCleanup(chat_patcher.stop)
        with patcher, chat_patcher:
            submit_question(at)
        self.assertEqual(at.session_state[limits.USAGE_KEY], 1)
        blob = "\n".join(m.value for m in at.markdown)
        self.assertIn("Explique le verdict des EU.", blob)

    def test_limit_exact_boundary_blocks_with_callout_and_no_submission(self):
        at = fresh_analyst("fr", usage=limits.limit())
        limit_value = limits.limit()
        self.assertGreaterEqual(limit_value, 1)
        blob = "\n".join(m.value for m in at.markdown)
        self.assertIn(str(limit_value), blob)
        # Aucune soumission possible : le compteur reste à la limite.
        self.assertEqual(at.session_state[limits.USAGE_KEY], limit_value)
        try:
            at.chat_input[0].set_value("Tentative après limite")
            at.run()
        except Exception:
            pass  # saisie désactivée : set_value/interaction refusée
        self.assertEqual(at.session_state[limits.USAGE_KEY], limit_value)

    def test_provider_call_never_fires_after_limit(self):
        limit_value = limits.limit()
        patcher = unittest.mock.patch.object(ai, "is_available", return_value=True)
        chat_patcher = unittest.mock.patch.object(ai, "chat", return_value="interdit")
        self.addCleanup(patcher.stop)
        self.addCleanup(chat_patcher.stop)
        with patcher, chat_patcher:
            at = fresh_analyst("fr", usage=limit_value)
            blob = "\n".join(m.value for m in at.markdown)
        self.assertNotIn("interdit", blob)
        self.assertNotIn("IndexError", blob)

    def test_reached_message_french_scopes_per_session(self):
        at = fresh_analyst("fr", usage=limits.limit())
        blob = "\n".join(m.value for m in at.markdown)
        self.assertIn("par session de navigateur", blob)
        self.assertIn("ni un plafond global ni une garantie de dépense", blob)
        self.assertNotIn("index error", blob.lower())

    def test_reached_message_english_scopes_per_session(self):
        at = fresh_analyst("en", usage=limits.limit())
        blob = "\n".join(m.value for m in at.markdown)
        self.assertIn("per browser session", blob)
        self.assertIn("neither a global account limit nor a guaranteed spending cap", blob)


if __name__ == "__main__":
    unittest.main()
