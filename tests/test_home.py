"""Tests de la page Accueil : route, rendu FR/EN, bouton d'appel à l'action."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from geocapital import i18n

ROOT = Path(__file__).resolve().parent.parent

KEYS = (
    "nav.home", "home.eyebrow", "home.title.1", "home.title.2", "home.title.3", "home.subtitle",
    "home.cta", "home.note.1", "home.note.2",
    "home.folder.ai.title", "home.folder.ai.text", "home.folder.risk.title", "home.folder.risk.text",
    "home.folder.finance.title", "home.folder.finance.text",
)


class TestRoute(unittest.TestCase):
    def test_home_is_first_and_other_routes_are_kept(self):
        import app

        self.assertEqual(app.PAGES[0], "home")
        self.assertEqual(app.PAGES[1], "map")
        for page in ("country", "compare", "decoder", "analyst", "risk_lab", "portfolio", "progress", "subscriptions", "sources"):
            self.assertIn(page, app.PAGES)
        self.assertEqual(set(app.ICONS), set(app.PAGES))

    def test_labels_exist_in_both_languages(self):
        for lang in i18n.LANGS:
            self.assertFalse(set(KEYS) - set(i18n.STRINGS[lang]), lang)


class TestPage(unittest.TestCase):
    def _run(self, lang: str = "fr", **state):
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
        at.session_state["lang"] = lang
        for key, value in state.items():
            at.session_state[key] = value
        at.run()
        self.assertFalse(bool(at.exception), at.exception)
        return at

    def _html(self, at) -> str:
        return "\n".join(str(m.value) for m in at.markdown if not str(m.value).lstrip().startswith("<style>"))

    def test_app_opens_on_home(self):
        at = self._run()
        self.assertEqual(at.session_state["nav"], "home")
        self.assertIn("gc-home-hero", self._html(at))

    def test_renders_both_languages_without_raw_keys(self):
        for lang in ("fr", "en"):
            at = self._run(lang)
            html = self._html(at)
            self.assertEqual(next(b for b in at.button if b.key == "home_open_map").label, i18n.STRINGS[lang]["home.cta"])
            for key in (k for k in KEYS[2:] if k != "home.cta"):
                text = i18n.STRINGS[lang][key]
                self.assertIn(text.replace("'", "&#x27;"), html, f"[{lang}] {key}")
            self.assertIsNone(re.search(r"\bhome\.[a-z_.0-9]+", html), f"[{lang}] clé brute")

    def test_three_folders_and_two_notes(self):
        html = self._html(self._run())
        self.assertEqual(len(re.findall(r'<article class="gc-folder ', html)), 3)
        self.assertEqual(len(re.findall(r'<div class="gc-home-note ', html)), 2)

    def test_cta_opens_the_living_map(self):
        at = self._run()
        next(b for b in at.button if b.key == "home_open_map").click().run()
        self.assertFalse(bool(at.exception), at.exception)
        self.assertEqual(at.session_state["nav"], "map")
        html = self._html(at)
        self.assertIn("gc-hero", html)  # hero d'origine de la Carte vivante conservé
        self.assertNotIn("gc-home-hero", html)

    def test_map_page_is_unchanged_by_the_landing(self):
        text = (ROOT / "views" / "map_page.py").read_text(encoding="utf-8")
        self.assertIn("ui.hero(", text)
        self.assertNotIn("home", text.lower().replace("homepage", ""))

    def test_font_import_stays_first_in_the_stylesheet(self):
        css = (ROOT / "assets" / "styles.css").read_text(encoding="utf-8")
        self.assertTrue(css.startswith("@import url("))
        self.assertIn("Caveat", css.split("\n", 1)[0])


if __name__ == "__main__":
    unittest.main()
