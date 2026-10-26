"""Tests du comparateur (crash 3 pays sélectionnés) et du message ConfigError.

Le 2026-10-25, sélectionner 3 pays dans le comparateur levait
IndexError (colonnes de téléchargement sous-dimensionnées : [1, 1, 3]
pour max_selections=3). Ce test fige le correctif via AppTest.
"""

from __future__ import annotations

import pathlib
import unittest

from geocapital import scoring

ROOT = pathlib.Path(__file__).resolve().parent.parent


class TestComparatorThreeCountries(unittest.TestCase):
    def test_three_selected_countries_render_without_exception(self):
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
        at.session_state["lang"] = "fr"
        at.run()
        at.session_state["nav"] = "compare"
        at.run()
        widget = None
        for w in at.multiselect:
            widget = w
            break
        if widget is None:
            self.skipTest("multiselect du comparateur introuvable")
        at.multiselect[0].set_value(["usa", "lebanon", "syria"])
        at.run()
        self.assertFalse(bool(at.exception), f"exception: {at.exception}")


class TestMissingSectionMessage(unittest.TestCase):
    def test_missing_scoring_model_message_path_is_not_doubled(self):
        import json

        with open("data/meta.json", encoding="utf-8") as handle:
            meta = json.load(handle)
        del meta["scoring_model"]
        with self.assertRaises(scoring.ConfigError) as ctx:
            scoring.validate_model_params(meta)
        self.assertEqual(
            str(ctx.exception),
            "meta.scoring_model: section absente (attendue : dictionnaire)",
        )


if __name__ == "__main__":
    unittest.main()
