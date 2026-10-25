"""Tests du normalisateur HTML (parade au HTML affiché en code indenté)."""

from __future__ import annotations

import unittest
from unittest import mock

from geocapital import ui


class TestFlattenHtml(unittest.TestCase):
    def test_plain_html_is_stripped_of_indentation_and_blank_lines(self):
        markup = """
        <div class="gc-card">
          <div class="gc-kpi-label">Rendement exigé</div>

          <p>Ligne après une ligne vide</p>
        </div>
        """
        flattened = ui.flatten_html(markup)
        self.assertNotIn("\n\n", flattened)
        self.assertTrue(flattened.startswith('<div class="gc-card">'))
        self.assertIn("<p>Ligne après une ligne vide</p>", flattened)

    def test_indented_substitution_no_longer_starts_with_four_spaces(self):
        ring = ui.ring(78.0, "score / 100")
        markup = f"""
        <div class="gc-score-row">
            {ring}
            <div>
              <div class="gc-kpi-label">Rendement exigé</div>
            </div>
        </div>
        """
        flattened = ui.flatten_html(markup)
        # Plus aucune ligne indentée : le parseur Markdown ne peut plus voir
        # un bloc de code indenté, et aucun HTML ne doit ressortir en clair.
        self.assertTrue(all(line == line.strip() for line in flattened.splitlines()))
        self.assertIn("gc-ring", flattened)

    def test_content_is_preserved_verbatim(self):
        markup = """<div>"Deux" & plus — accents é è à</div>"""
        self.assertEqual(ui.flatten_html(markup), markup)

    def test_single_line_untouched(self):
        markup = '<div style="height:10px"></div>'
        self.assertEqual(ui.flatten_html(markup), markup)

    def test_pre_blocks_preserve_whitespace(self):
        markup = '<pre style="x">{\n  "a": 1,\n  "b": [\n    1,\n    2\n  ]\n}</pre>'
        self.assertEqual(ui.flatten_html(markup), markup)

    def test_pre_blocks_surrounded_by_html(self):
        markup = (
            '<div class="wrap">\n'
            "<pre>{\n  \"pays\": \"France\"\n}</pre>\n"
            '<p>Après le bloc pré.</p>\n'
        )
        flattened = ui.flatten_html(markup)
        self.assertIn('<pre>{\n  "pays": "France"\n}</pre>', flattened)
        self.assertIn("<p>Après le bloc pré.</p>", flattened)
        self.assertNotIn("\n\n", flattened)

    def test_empty_and_whitespace_only_strings(self):
        self.assertEqual(ui.flatten_html(""), "")
        self.assertEqual(ui.flatten_html("   \n  \n "), "")


class TestMarkdownNormalizer(unittest.TestCase):
    """Vérifie le comportement du wrapper sans exécuter le runtime Streamlit."""

    def setUp(self):
        import streamlit as st

        self._st_ref = st
        self._restore = getattr(st.markdown, "_geocapital_original", st.markdown)
        self._original = st.markdown
        self.calls = []

        def fake_markdown(body, *args, **kwargs):
            self.calls.append((body, args, kwargs))
            return body

        st.markdown = fake_markdown
        ui.install_markdown_normalizer()

    def tearDown(self):
        self._st_ref.markdown = self._restore

    def test_html_markdown_is_flattened(self):
        import streamlit as st

        indented = "\n    <div>\n\n      <p>texte</p>\n    </div>\n"
        st.markdown(indented, unsafe_allow_html=True)
        body = self.calls[-1][0]
        self.assertEqual(body, "<div>\n<p>texte</p>\n</div>")

    def test_plain_markdown_is_not_touched(self):
        import streamlit as st

        markdown_text = "# Titre\n\n  4 espaces après ligne vide"
        st.markdown(markdown_text)
        st.markdown(markdown_text, unsafe_allow_html=False)
        for body, _, kwargs in self.calls[-2:]:
            self.assertEqual(body, markdown_text)
            self.assertFalse(kwargs.get("unsafe_allow_html"))

    def test_installing_twice_does_not_stack_wrappers(self):
        import streamlit as st

        before = st.markdown
        ui.install_markdown_normalizer()
        self.assertIs(st.markdown, before)


if __name__ == "__main__":
    unittest.main()
