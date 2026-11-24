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


class OfficialLogo(unittest.TestCase):
    """Logo animé officiel : asset conservé tel quel, rendu via <img>, accessible."""

    asset = ROOT / "assets" / "geocapp-animated-logo.svg"

    def test_asset_is_the_original_animated_svg(self):
        raw = self.asset.read_bytes()
        text = raw.decode("utf-8")
        self.assertTrue(text.lstrip().startswith("<svg"))
        self.assertIn('width="2000" height="2000"', text)
        # animations CSS d'origine conservées
        for token in ("@keyframes lm-trace", "@keyframes lm-fill", ".lm-dt", ".lm-df", "stroke-dasharray"):
            self.assertIn(token, text)
        # accessibilité : l'animation se coupe si l'utilisateur le demande (règle intégrée au SVG)
        self.assertIn("prefers-reduced-motion", text)
        # sûr : ni script, ni image raster embarquée, ni ressource externe
        self.assertNotIn("<script", text.lower())
        self.assertNotIn("<image", text.lower())
        self.assertNotIn('href="http', text.lower())

    def test_logo_is_black_monochrome_with_transparent_background(self):
        text = self.asset.read_text(encoding="utf-8")
        # plus aucune trace du bleu d'origine ni du fond crème
        self.assertNotIn("rgb(3, 3, 49)", text)
        self.assertNotIn("rgb(3,3,49)", text)
        self.assertNotIn("#f9f9f3", text.lower())
        # encre noire #111111 : traits, remplissages et flood des filtres
        self.assertGreaterEqual(text.count("#111111"), 30)
        # fond du canevas transparent
        self.assertRegex(text, r'<rect width="2000" height="2000"[^>]*id="background"[^>]*fill="transparent"')
        # géométrie et animation d'origine intactes (comptes mesurés sur le fichier d'origine :
        # 8 tracés, 8 contours animés, 15 groupes de remplissage, 23 minuteries --d)
        self.assertEqual(text.count("<path "), 8)
        self.assertEqual(text.count('pathLength="1"'), 8)
        self.assertEqual(text.count('class="lm-dt"'), 8)
        self.assertEqual(text.count('class="lm-df"'), 15)
        self.assertEqual(text.count("--d:"), 23)
        self.assertIn("stroke-dasharray:1 1", text)

    def test_logo_markup_is_accessible_and_has_no_embedded_raster(self):
        markup = ui.logo()
        self.assertIn('class="gc-logo"', markup)
        self.assertIn('role="img"', markup)
        self.assertIn('aria-label="Logo GeoCapp"', markup)
        self.assertNotIn("<img", markup)  # le dessin vient de --gc-logo, rien n'est dupliqué dans la page
        self.assertNotIn("data:", markup)

    def test_inject_css_serves_exact_asset_bytes_as_svg_variable(self):
        import base64

        with mock.patch.object(ui.st, "markdown") as md:
            ui.inject_css()
        css = md.call_args.args[0]
        match = re.search(r'--gc-logo:url\("data:image/svg\+xml;base64,([A-Za-z0-9+/=]+)"\)', css)
        self.assertIsNotNone(match, "le logo doit être injecté comme SVG (pas de raster)")
        self.assertEqual(base64.b64decode(match.group(1)), self.asset.read_bytes())
        for raster in ("image/png", "image/jpeg", "image/gif", ".png", ".jpg", ".gif"):
            self.assertNotIn(raster, css.split("--gc-logo")[1][:60])

    def test_header_bar_has_no_logo(self):
        with mock.patch.object(ui.st, "markdown") as md:
            ui.context_bar("Carte", "🇫🇷 France", "Équilibré", "2024-2025")
        markup = md.call_args.args[0]
        self.assertNotIn("gc-logo", markup)
        self.assertNotIn("<img", markup)
        self.assertIn("gc-context-page", markup)  # le titre de page reste

    def test_sidebar_has_logo_wordmark_and_slogan_in_both_languages(self):
        from streamlit.testing.v1 import AppTest

        for lang in ("fr", "en"):
            at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
            at.session_state["lang"] = lang
            at.run()
            self.assertFalse(bool(at.exception), at.exception)
            side = "\n".join(m.value for m in at.sidebar.markdown)
            self.assertIn("gc-logo", side)
            # Le logo SVG est l'unique marque : plus de mot-symbole « GeoCapp » texte dessous.
            self.assertNotIn("gc-brand-title", side)
            visible_text = re.sub(r"<[^>]+>", " ", side.split("gc-brand-sub")[0].split('class="gc-brand"')[1])
            self.assertNotIn("GeoCapp", visible_text)
            # La signature reste, sous le logo.
            self.assertIn(i18n.STRINGS[lang]["side.brand_sub"], side)
            self.assertLess(side.index("gc-logo"), side.index(i18n.STRINGS[lang]["side.brand_sub"]))
            self.assertEqual(side.count('class="gc-logo"'), 1, "un seul logo, dans la barre latérale")
            self.assertNotIn("<img", side)

    def test_logo_is_not_repeated_in_page_bodies(self):
        # Le grand logo n'apparaît que dans la barre latérale ; les pages n'embarquent que la mini-version.
        for path in (ROOT / "views").glob("*.py"):
            self.assertNotIn("ui.logo(", path.read_text(encoding="utf-8"), str(path))

    def test_logo_css_has_no_plate_or_background(self):
        css = (ROOT / "assets" / "styles.css").read_text(encoding="utf-8")
        block = css[css.index(".gc-logo {") : css.index("@keyframes gc-logo-load")]
        self.assertIn("background-color: transparent", block)
        self.assertIn("box-shadow: none", block)
        self.assertNotIn("f9f9f3", css.lower())

    def test_sidebar_is_fluid_glass_and_wordmark_rules_are_gone(self):
        css = (ROOT / "assets" / "styles.css").read_text(encoding="utf-8")
        rule = css[css.index('[data-testid="stSidebar"] {') :]
        rule = rule[: rule.index("}")]
        self.assertIn("blur(44px) saturate(1.8)", rule)
        self.assertIn("backdrop-filter", rule)
        self.assertRegex(rule, r"rgba\(255, 255, 255, 0\.[0-5]\d*\)")  # translucent, never opaque
        self.assertNotRegex(rule, r"background:\s*(#fff|white|rgb\(255)")
        self.assertIn("border-right: 1px solid rgba(255, 255, 255", rule)
        self.assertNotIn(".gc-brand-title", css)
        self.assertNotIn(".gc-brand-row", css)

    def test_css_frames_logo_without_distortion(self):
        css = (ROOT / "assets" / "styles.css").read_text(encoding="utf-8")
        block = css[css.index(".gc-logo {") : css.index("@keyframes gc-logo-load")]
        self.assertIn("aspect-ratio: 1700 / 978", block)
        self.assertIn("background-size: 117.647% auto", block)  # 2000/1700 : échelle uniforme, aucune déformation
        self.assertIn("background-position: center", block)
        self.assertIn("background-repeat: no-repeat", block)

    def test_desktop_defers_logo_load_but_mobile_is_unchanged(self):
        css = (ROOT / "assets" / "styles.css").read_text(encoding="utf-8")
        # défaut (donc mobile) : chargement immédiat via var(--gc-logo)
        base = css[css.index(".gc-logo {") : css.index("@keyframes gc-logo-load")]
        self.assertIn("background-image: var(--gc-logo)", base)
        self.assertNotIn("animation:", base)
        # bureau seulement : chargement différé après la rafale de rendu initiale
        self.assertIn("@keyframes gc-logo-load", css)
        desktop = css[css.index("@media (min-width: 641px) {\n  .gc-logo") :]
        desktop = desktop[: desktop.index("}\n}") + 3]
        self.assertIn("background-image: none", desktop)
        self.assertIn("animation: gc-logo-load", desktop)

    def test_reduced_motion_keeps_logo_visible(self):
        css = (ROOT / "assets" / "styles.css").read_text(encoding="utf-8")
        block = css[css.index("@media (prefers-reduced-motion: reduce) {") :]
        self.assertIn(".gc-logo { background-image: var(--gc-logo) !important; }", block)

    def test_desktop_sidebar_has_tonal_layers_mobile_does_not_get_them(self):
        css = (ROOT / "assets" / "styles.css").read_text(encoding="utf-8")
        i = css.index("@media (min-width: 641px) {\n  .stApp")
        block = css[i : css.index("\n}\n", css.index("var(--bg);", i)) + 3]
        self.assertGreaterEqual(block.count("radial-gradient(3"), 3)  # 3 masses confinées à la colonne de 300px
        self.assertIn("rgba(139, 127, 199", block)  # lavande
        self.assertIn("rgba(18, 18, 20", block)  # graphite
        # la règle mobile/base de .stApp reste inchangée (4 dégradés + fond)
        base = css[css.index(".stApp {") : css.index("@media (min-width: 641px) {\n  .stApp")]
        self.assertEqual(base.count("radial-gradient"), 4)

    def test_no_logo_styles_left_for_header_or_img(self):
        css = (ROOT / "assets" / "styles.css").read_text(encoding="utf-8")
        self.assertNotIn(".gc-logo-sm", css)
        self.assertNotIn(".gc-logo-lg", css)
        self.assertNotIn(".gc-logo img", css)


if __name__ == "__main__":
    unittest.main()
