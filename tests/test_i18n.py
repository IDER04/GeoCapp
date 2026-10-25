"""Tests du socle i18n (Étape 1 — Phase 3) : clés, repli, store de langue."""

from __future__ import annotations

import unittest

from geocapital import i18n


class TestParity(unittest.TestCase):
    def test_langs_listed(self):
        self.assertEqual(set(i18n.LANGS), {"fr", "en"})

    def test_fr_en_have_identical_key_sets(self):
        fr_keys = set(i18n.STRINGS["fr"])
        en_keys = set(i18n.STRINGS["en"])
        self.assertEqual(fr_keys, en_keys)

    def test_no_empty_string_value(self):
        for lang, strings in i18n.STRINGS.items():
            for key, value in strings.items():
                with self.subTest(lang=lang, key=key):
                    self.assertIsInstance(value, str)
                    self.assertNotEqual(value.strip(), "")


class TestStore(unittest.TestCase):
    def setUp(self):
        import streamlit as st

        st.session_state.clear()
        st.session_state["lang"] = "fr"

    def tearDown(self):
        import streamlit as st

        st.session_state.clear()

    def test_default_lang_is_fr(self):
        import streamlit as st

        st.session_state.pop("lang", None)
        self.assertEqual(i18n.current_lang(), "fr")

    def test_set_lang_persists_in_session(self):
        import streamlit as st

        i18n.set_lang("en")
        self.assertEqual(st.session_state["lang"], "en")
        self.assertEqual(i18n.current_lang(), "en")

    def test_set_lang_unknown_falls_back_to_fr(self):
        i18n.set_lang("de")
        self.assertEqual(i18n.current_lang(), "fr")

    def test_current_lang_unknown_value_falls_back_to_fr(self):
        import streamlit as st

        st.session_state["lang"] = "es"
        self.assertEqual(i18n.current_lang(), "fr")


class TestTranslate(unittest.TestCase):
    def setUp(self):
        import streamlit as st

        st.session_state.clear()
        st.session_state["lang"] = "fr"

    def tearDown(self):
        import streamlit as st

        st.session_state.clear()

    def test_known_key_in_both_langs(self):
        self.assertEqual(i18n.t("nav.country"), "Fiche pays")
        import streamlit as st

        st.session_state["lang"] = "en"
        self.assertEqual(i18n.t("nav.country"), "Country profile")

    def test_fallback_to_fr_when_key_missing_in_current_lang(self):
        i18n.STRINGS["en"]["__missing_key__"] = None  # absent en EN
        del i18n.STRINGS["en"]["__missing_key__"]
        # Clé présente uniquement en FR (cas simulé d'ajout partiel).
        i18n.STRINGS["fr"]["__tmp_only_fr__"] = "Seulement en français"
        try:
            import streamlit as st

            st.session_state["lang"] = "en"
            self.assertEqual(i18n.t("__tmp_only_fr__"), "Seulement en français")
        finally:
            del i18n.STRINGS["fr"]["__tmp_only_fr__"]

    def test_unknown_key_returns_key_without_error(self):
        self.assertEqual(i18n.t("__nope__"), "__nope__")

    def test_format_substitution(self):
        result = i18n.t("side.profile_line", profile="Balanced", quiz_passed=3)
        self.assertIn("Balanced", result)
        self.assertIn("3", result)

    def test_format_extra_placeholder_does_not_crash(self):
        result = i18n.t("nav.map", unknown="x")
        self.assertEqual(result, i18n.STRINGS["fr"]["nav.map"])


class TestProfiles(unittest.TestCase):
    def test_profile_key_mapping(self):
        self.assertEqual(i18n.profile_key("Équilibré"), "balanced")
        self.assertEqual(i18n.profile_key("Prudent"), "prudent")
        self.assertEqual(i18n.profile_key("Audacieux"), "bold")

    def test_profile_keys_exist_in_both_langs(self):
        for code in i18n.PROFILE_KEYS.values():
            for lang in ("fr", "en"):
                self.assertIn(f"profile.{code}", i18n.STRINGS[lang])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
