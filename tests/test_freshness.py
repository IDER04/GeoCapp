"""Tests de la couche « fraîcheur des données » (affichage, hors scoring).

Garanties :
- extraction de millésime robuste sur toutes les formes présentes dans les
  données (« 2024 », « déc. 2024 », « janv. 2025 », « calcul », vide) ;
- règle stale déterministe : observation antérieure à l'année courante − 1 ;
- la date de consultation vient de `data/meta.json` (`app.data_as_of`) ;
- libellés disponibles en FR **et** EN (parité garantie par test_i18n,
  on vérifie ici le contenu).
- aucun impact sur le score : le module n'importera jamais scoring.py.
"""

import datetime
import json
import unittest
import unittest.mock

from geocapital import data, freshness, i18n


def set_lang(lang: str) -> None:
    i18n.st.session_state["lang"] = lang


class TestObsYear(unittest.TestCase):
    """Extraction du millésime d'observation."""

    def test_plain_year(self):
        self.assertEqual(freshness.obs_year("2024"), 2024)

    def test_month_prefixed_year(self):
        # Les formes réelles des données (françaises et futur canonical) :
        self.assertEqual(freshness.obs_year("déc. 2024"), 2024)
        self.assertEqual(freshness.obs_year("janv. 2025"), 2025)

    def test_undated_values_return_none(self):
        self.assertIsNone(freshness.obs_year("calcul"))
        self.assertIsNone(freshness.obs_year(""))
        self.assertIsNone(freshness.obs_year(None))

    def test_every_real_indicator_date_yields_a_vintage(self):
        """Corpus réel : chaque date d'indicateur doit être analysable."""
        for country in data.countries():
            for key, meta in country.get("indicators", {}).items():
                date = meta.get("date", "")
                if key == "rating" and date == "":
                    continue
                self.assertIsNotNone(
                    freshness.obs_year(date),
                    f"{country['id']}/{key}: millésime illisible: {date!r}",
                )
                self.assertGreaterEqual(freshness.obs_year(date), 1990)


class TestStaleRule(unittest.TestCase):
    """Règle de rajeunissement : obs_year(date) < année courante − 1."""

    def test_stale_boundary(self):
        # En 2026 : 2024 et avant = à rafraîchir ; 2025 et après = ok.
        self.assertTrue(freshness.is_stale("2024", now_year=2026))
        self.assertTrue(freshness.is_stale("déc. 2024", now_year=2026))
        self.assertFalse(freshness.is_stale("2025", now_year=2026))
        self.assertFalse(freshness.is_stale("2026", now_year=2026))
        self.assertTrue(freshness.is_stale("2025", now_year=2027))

    def test_undated_is_never_stale(self):
        self.assertFalse(freshness.is_stale("calcul", now_year=2026))
        self.assertFalse(freshness.is_stale("", now_year=2026))
        self.assertFalse(freshness.is_stale(None, now_year=2026))

    def test_threshold_falls_one_year_behind_now(self):
        self.assertEqual(freshness.stale_threshold(now_year=2026), 2025)
        self.assertEqual(freshness.stale_threshold(now_year=2025), 2024)

    def test_any_stale(self):
        self.assertTrue(freshness.any_stale(["2025", "2024"], now_year=2026))
        self.assertFalse(freshness.any_stale(["2025", "calcul"], now_year=2026))
        self.assertFalse(freshness.any_stale([], now_year=2026))

    def test_default_now_year_is_today(self):
        current = datetime.date.today().year
        self.assertEqual(
            freshness.is_stale(str(current - 2)),
            freshness.is_stale(str(current - 2), now_year=current),
        )

    def test_stale_badge_prefixes_only_stale(self):
        self.assertEqual(freshness.stale_badge("2024"), "⚠ 2024")
        self.assertEqual(freshness.stale_badge("janv. 2025"), "janv. 2025")
        self.assertEqual(freshness.stale_badge(""), "")


class TestAsOf(unittest.TestCase):
    """Date de consultation (retrieval) : source de vérité = meta.json."""

    def test_as_of_matches_meta_file(self):
        with open("data/meta.json", encoding="utf-8") as handle:
            expected = json.load(handle)["app"]["data_as_of"]
        self.assertEqual(freshness.as_of(), expected)

    def test_as_of_falls_back_to_today_when_missing(self):
        """Sans `app.data_as_of`, repli sur la date du jour — et le mock
        doit être démonté (`addCleanup`), sinon data.load_data reste mocké
        et corrompt tous les tests suivants."""
        patcher = unittest.mock.patch.object(
            data, "load_data", return_value={"app": {}}
        )
        fix_today = unittest.mock.patch.object(
            freshness, "_today_iso", return_value="2099-12-31"
        )
        self.addCleanup(patcher.stop)
        self.addCleanup(fix_today.stop)
        patcher.start()
        fix_today.start()
        # Sans `app.data_as_of` dans le méta, repli sur la date du jour
        # (ici figée à 2099-12-31 pour rendre le test déterministe) :
        self.assertEqual(freshness.as_of(), "2099-12-31")


class TestLabels(unittest.TestCase):
    """Libellés bilingues (FR par défaut)."""

    def test_french_labels(self):
        set_lang("fr")
        self.addCleanup(set_lang, "fr")
        label = i18n.t("fresh.as_of", as_of="2026-10-25")
        self.assertIn("Données au", label)
        self.assertIn("2026-10-25", label)

    def test_english_labels(self):
        set_lang("en")
        self.addCleanup(set_lang, "fr")
        label = i18n.t("fresh.as_of", as_of="2026-10-25")
        self.assertIn("Data as of 2026-10-25", label)
        note = i18n.t("fresh.stale_note", limit=2025)
        self.assertIn("2025", note)
        self.assertIn("the most recent confirmed one", note)

    def test_verdict_dates_label_mentions_vintage(self):
        set_lang("fr")
        self.addCleanup(set_lang, "fr")
        self.assertIn("2024", i18n.t("fresh.verdict_dates", oldest=2024))


if __name__ == "__main__":
    unittest.main()
