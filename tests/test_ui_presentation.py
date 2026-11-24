"""Tests de la couche de présentation (refonte « Obsidian & Frost »).

Aucun test de logique financière ici : on fige l'identité visuelle et les
garde-fous de la refonte (marque, slogan, tokens CSS, palette monochrome,
composants UI) sans toucher aux calculs.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent

from geocapital import charts, i18n, ui  # noqa: E402


class EditorialTitle(unittest.TestCase):
    def test_last_word_is_emphasised(self):
        self.assertEqual(ui.editorial("Deux histoires risquées"), "Deux histoires <em>risquées</em>")

    def test_single_word_is_not_wrapped(self):
        self.assertEqual(ui.editorial("Japon"), "Japon")

    def test_html_is_escaped(self):
        out = ui.editorial("<b>x</b> y")
        self.assertNotIn("<b>", out)
        self.assertTrue(out.endswith("<em>y</em>"))

    def test_empty_title(self):
        self.assertEqual(ui.editorial(""), "")


class UiComponents(unittest.TestCase):
    def _markup(self, func, *args, **kwargs) -> str:
        with mock.patch.object(ui.st, "markdown") as md:
            func(*args, **kwargs)
        return md.call_args.args[0]

    def test_kpi_default_is_glass_and_dark_variant_is_anchor(self):
        self.assertIn('class="gc-kpi"', self._markup(ui.kpi, "10", "Label", "note"))
        self.assertIn('class="gc-kpi dark"', self._markup(ui.kpi, "10", "Label", "note", dark=True))

    def test_context_bar_escapes_and_shows_context(self):
        markup = self._markup(ui.context_bar, "Carte", "🇫🇷 <France>", "Équilibré", "2024-2025")
        self.assertIn("gc-context", markup)
        self.assertIn("&lt;France&gt;", markup)
        self.assertIn("Équilibré", markup)

    def test_ring_uses_css_variable_tones(self):
        for score, expected in ((90, "var(--green)"), (65, "var(--lime)"), (50, "var(--orange)"), (20, "var(--red)")):
            self.assertIn(expected, ui.ring(float(score)))

    def test_hero_title_emphasis_rendered(self):
        markup = self._markup(ui.hero, "eyebrow", "Comprendre le passé", "sub", ["chip"])
        self.assertIn("<em>passé</em>", markup)


class Charts(unittest.TestCase):
    def test_palette_is_monochrome(self):
        for color in (charts.OBSIDIAN, charts.GRAPHITE, charts.SLATE, charts.SILVER, charts.LIGHT, *charts.SERIES):
            r, g, b = (int(color[i : i + 2], 16) for i in (1, 3, 5))
            self.assertLess(max(r, g, b) - min(r, g, b), 8, f"{color} n'est pas un gris")

    def test_layout_is_transparent_with_requested_height(self):
        lay = charts.layout(300)
        self.assertEqual(lay["height"], 300)
        self.assertEqual(lay["paper_bgcolor"], charts.CLEAR)
        self.assertEqual(lay["plot_bgcolor"], charts.CLEAR)

    def test_layout_extra_overrides_base(self):
        self.assertFalse(charts.layout(200, showlegend=False)["showlegend"])

    def test_axis_is_minimal(self):
        ax = charts.axis(title="x")
        self.assertFalse(ax["zeroline"])
        self.assertEqual(ax["title"], "x")

    def test_series_are_distinguishable_beyond_shade(self):
        self.assertEqual(len(set(charts.DASHES)), len(charts.DASHES))
        self.assertEqual(len(set(charts.SYMBOLS)), len(charts.SYMBOLS))

    def test_hex_to_rgb(self):
        self.assertEqual(charts.hex_to_rgb("#121212"), "18,18,18")


class Branding(unittest.TestCase):
    def test_no_visible_geocapital_string_in_i18n(self):
        for lang, table in i18n.STRINGS.items():
            for key, value in table.items():
                self.assertNotIn("GeoCapital", str(value), f"[{lang}] {key}")

    def test_slogan_in_both_languages(self):
        self.assertEqual(i18n.STRINGS["fr"]["side.brand_sub"], "Connaître le passé pour anticiper le futur.")
        self.assertEqual(i18n.STRINGS["en"]["side.brand_sub"], "Know the past to anticipate the future.")
        self.assertEqual(i18n.STRINGS["fr"]["ui.footer.tagline"], i18n.STRINGS["fr"]["side.brand_sub"])
        self.assertEqual(i18n.STRINGS["en"]["ui.footer.tagline"], i18n.STRINGS["en"]["side.brand_sub"])

    def test_page_title_uses_geocapp(self):
        for lang in ("fr", "en"):
            self.assertTrue(i18n.STRINGS[lang]["app.page_title"].startswith("GeoCapp"))

    def test_data_files_carry_no_old_brand(self):
        for path in (ROOT / "data").rglob("*.json"):
            json.loads(path.read_text(encoding="utf-8"))  # JSON toujours valide
            self.assertNotIn("GeoCapital", path.read_text(encoding="utf-8"), str(path))

    def test_preset_label_keys_have_parity(self):
        self.assertIn("pf.presets_label", i18n.STRINGS["fr"])
        self.assertIn("pf.presets_label", i18n.STRINGS["en"])

    def test_internal_identifiers_unchanged(self):
        from geocapital import ai

        self.assertTrue((ROOT / "geocapital").is_dir())
        self.assertIn("GEOCAPITAL_MODEL", (ROOT / "geocapital" / "ai.py").read_text(encoding="utf-8"))
        self.assertTrue(hasattr(ai, "is_available"))


class DesignSystem(unittest.TestCase):
    css = (ROOT / "assets" / "styles.css").read_text(encoding="utf-8")

    def test_tokens_defined(self):
        for token in ("--bg: #F7F7F5", "--obsidian: #121212", "--glass-1", "--glass-3", "--glass-blur", "--ink", "--r-card"):
            self.assertIn(token, self.css)

    def test_heavy_glass_and_fallback(self):
        self.assertIn("backdrop-filter", self.css)
        self.assertIn("blur(26px)", self.css)
        self.assertIn("@supports not", self.css)

    def test_reduced_motion_respected(self):
        self.assertIn("prefers-reduced-motion: reduce", self.css)

    def test_fonts_are_editorial_pair(self):
        self.assertIn("Instrument+Serif", self.css)
        self.assertIn("Inter", self.css)

    def test_old_dark_palette_is_gone(self):
        for old in ("#070b14", "#0e1626", "#e6b86b"):
            self.assertNotIn(old, self.css)

    def test_streamlit_theme_is_light(self):
        config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
        self.assertIn('base = "light"', config)
        self.assertIn("#F7F7F5", config)

    def test_no_dark_theme_hex_left_in_python_presentation(self):
        pattern = re.compile(r"#(?:e6b86b|4ade80|fb7185|fbbf24|a3e635|7dd3fc|0b1220|0e1626)", re.I)
        for path in [ROOT / "app.py", ROOT / "geocapital" / "ui.py", *(ROOT / "views").glob("*.py")]:
            self.assertIsNone(pattern.search(path.read_text(encoding="utf-8")), str(path))

    def test_nav_icons_cover_every_route(self):
        import app

        self.assertEqual(set(app.ICONS), set(app.PAGES))
        for icon in app.ICONS.values():
            self.assertTrue(icon.startswith(":material/"))


if __name__ == "__main__":
    unittest.main()
