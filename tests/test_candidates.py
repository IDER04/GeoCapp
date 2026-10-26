"""Incrément 6.1 (Priorité 6) — validation ciblée.

Garanties :
1. Mise à jour Liban `inflation` appliquée telle qu'approuvée
   (docs/REFRESH_REVIEW.md entrée 2) — valeur, millésime, provenance
   complète (`source`, `source_url`, `obs_status`, `retrieved`), note
   réécrite, et « uniquement l'inflation » a changé dans la fiche.
2. Le candidat Brésil (data/candidates/brazil.json) est
   structurellement valide, isolé (jamais chargé par la production) et
   sans valeur substituée depuis une définition rejetée.
3. Tolérance aux indicateurs manquants/non résolus : le scoring ne
   lève pas sur une fiche minimale ; le candidat liste explicitement
   ses `open_items` au lieu d'inventer des valeurs.
4. Identité de formule : tous les pays NON libanais restent EXACTS
   vis-à-vis du baseline figé (constantes in-repo, CI-safe).
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import unittest

from geocapital import data, scoring

# Constante du baseline figé (in-repo, self-contained) — garantit que la
# formule, les poids et les seuils n'ont pas bougé.
_spec = importlib.util.find_spec("test_scoring_config")
if _spec is not None:  # exécution via `unittest discover -s tests`
    from test_scoring_config import BASELINE, COMPONENTS_EQUILIBRE
else:  # filet de sécurité : chargement direct du fichier
    _p = pathlib.Path(__file__).parent / "test_scoring_config.py"
    _m = importlib.util.spec_from_file_location("test_scoring_config", _p)
    assert _m is not None
    test_scoring_config = importlib.util.module_from_spec(_m)
    _m.loader.exec_module(test_scoring_config)
    BASELINE, COMPONENTS_EQUILIBRE = (
        test_scoring_config.BASELINE,
        test_scoring_config.COMPONENTS_EQUILIBRE,
    )

ROOT = pathlib.Path(__file__).resolve().parents[1]
CANDIDATE_PATH = ROOT / "data" / "candidates" / "brazil.json"

PASTeqProvenance = {
    "value",
    "unit",
    "date",
    "obs_status",
    "source",
    "source_url",
    "retrieved",
}


class LebanonInflationUpdate(unittest.TestCase):
    """Partie A — application approuvée : Liban inflation 2025 = 14,6 %."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.country = data.country_by_id("lebanon")
        cls.ind = (cls.country or {}).get("indicators", {}).get("inflation", {})

    def test_applied_value_period_status(self) -> None:
        self.assertEqual(self.ind["value"], 14.6)
        self.assertEqual(self.ind["unit"], "%")
        self.assertEqual(self.ind["date"], "2025")  # période observée
        self.assertEqual(self.ind["obs_status"], "actual")

    def test_retrieval_date_is_not_observation_date(self) -> None:
        self.assertEqual(self.ind["retrieved"], "2026-10-25")
        # les deux notions restent distinctes dans la fiche
        self.assertNotEqual(self.ind["retrieved"], self.ind["date"])

    def test_provenance_source_and_url(self) -> None:
        self.assertIn("Banque mondiale", self.ind["source"])
        self.assertIn("FP.CPI.TOTL.ZG", self.ind["source"])
        self.assertEqual(
            self.ind["source_url"],
            "https://data.worldbank.org/indicator/FP.CPI.TOTL.ZG?locations=LB",
        )

    def test_note_rewritten_for_disinflation(self) -> None:
        note = self.ind["note"].lower()
        self.assertIn("désinflation", note)
        # l'ancien récit (hyperinflation au présent) ne doit plus régir la note
        self.assertNotIn("reste très élevée", note)

    def test_old_values_gone(self) -> None:
        self.assertNotEqual(self.ind["value"], 45.0)
        self.assertNotEqual(self.ind["date"], "2024")

    def test_only_inflation_changed_in_lebanon(self) -> None:
        """Ancres de régression : les autres indicateurs ne bougent pas."""
        indicators = self.country["indicators"]
        self.assertEqual(indicators["gdp_growth"]["value"], -6.5)
        self.assertEqual(indicators["policy_rate"]["value"], 20.0)
        self.assertEqual(indicators["unemployment"]["value"], 30.0)
        self.assertEqual(indicators["reserves"]["value"], 10.0)
        self.assertEqual(indicators["inflation"]["value"], 14.6)

    def test_model_outputs_match_approved_update(self) -> None:
        """Scores/verdicts Liban = mise à jour approuvée (baseline adapte
        UNIQUEMENT les lignes lebanon — cf. docstring de
        test_scoring_config.py)."""
        expected = BASELINE["lebanon"]["profiles"]
        for prof in ("Prudent", "Équilibré", "Audacieux"):
            got = scoring.overall_score(self.country, prof)
            for key in ("score", "verdict", "risk", "volatility"):
                self.assertEqual(got[key], expected[prof][key], (prof, key))
        components = scoring.component_scores(self.country)
        self.assertEqual(
            components["stabilite"],
            COMPONENTS_EQUILIBRE["lebanon"]["stabilite"],
        )

    def test_ke_and_crp_unchanged(self) -> None:
        """ke/crp dépendent du rating et du CDS — pas de l'inflation."""
        self.assertEqual(scoring.required_return(self.country)["ke"], 31.20)
        self.assertEqual(scoring.country_risk_premium(self.country)[0], 22.5)


class BrazilCandidateIsolated(unittest.TestCase):
    """Partie B — candidat Brésil : valide, isolé, sans substitution."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = CANDIDATE_PATH.read_text(encoding="utf-8")
        cls.candidate = json.loads(cls.raw)

    def test_file_is_outside_production_directory(self) -> None:
        self.assertTrue(CANDIDATE_PATH.exists())
        self.assertIn("candidates", str(CANDIDATE_PATH))
        # et jamais chargé par la couche de production
        self.assertNotIn("brazil", [c["id"] for c in data.countries()])
        self.assertIsNone(data.country_by_id("brazil"))

    def test_candidate_metadata_declares_status(self) -> None:
        meta = self.candidate["_candidate"]
        self.assertEqual(meta["status"], "proposed_for_review")
        self.assertTrue(meta["not_registered_in_production"])
        self.assertTrue(meta["open_items"])  # au moins un point ouvert
        # les indicateurs de marché non résolus sont listés, pas inventés
        open_text = " ".join(meta["open_items"])
        for unresolved in ("policy_rate", "rating", "cds"):
            self.assertIn(unresolved, open_text)

    def test_identity_keys(self) -> None:
        self.assertEqual(self.candidate["id"], "brazil")
        self.assertEqual(self.candidate["iso3"], "BRA")
        self.assertEqual(self.candidate["group_key"], "emerging")
        self.assertEqual(self.candidate["group"], "Émergent")

    def test_resolved_indicators_schema(self) -> None:
        """Les 5 indicateurs résolus portent la provenance complète."""
        indicators = self.candidate["indicators"]
        self.assertEqual(
            sorted(indicators.keys()),
            ["debt_gdp", "gdp_growth", "inflation", "reserves", "unemployment"],
        )
        for key, block in indicators.items():
            missing = PASTeqProvenance - set(block)
            self.assertFalse(missing, (key, missing))
            self.assertEqual(block["obs_status"], "actual", key)
            self.assertEqual(block["retrieved"], "2026-10-25", key)
            self.assertTrue(block["source_url"].startswith("http"), key)

    def test_verified_values_and_periods(self) -> None:
        ind = self.candidate["indicators"]
        expected = {
            "gdp_growth": (2.3, "%", "2025"),
            "inflation": (4.26, "%", "2025"),
            "unemployment": (5.6, "%", "2025"),
            "debt_gdp": (78.64, "%", "2025"),
            "reserves": (358.2, "Mds $", "2025"),
        }
        for key, (value, unit, date) in expected.items():
            self.assertEqual(ind[key]["value"], value, key)
            self.assertEqual(ind[key]["unit"], unit, key)
            self.assertEqual(ind[key]["date"], date, key)

    def test_no_substitution_from_rejected_definitions(self) -> None:
        """Les valeurs WB rejetées en revue (entrées 5 et 7) n'ont pas
        remplacé les sources nationales."""
        ind = self.candidate["indicators"]
        self.assertNotAlmostEqual(ind["inflation"]["value"], 5.0168, places=3)
        self.assertNotAlmostEqual(ind["debt_gdp"]["value"], 81.8554, places=3)
        # définition Dette = gouvernement GÉNÉRAL documentée dans la note,
        # la valeur WDI (gouvernement central) référencée comme écartée
        self.assertIn("GÉNÉRAL", ind["debt_gdp"]["note"])
        self.assertIn("est écartée", ind["debt_gdp"]["note"])
        # concept réserves (total, or inclus / conceito caixa) explicite
        reserves_note = ind["reserves"]["note"]
        self.assertIn("or inclus", reserves_note)
        self.assertIn("caixa", reserves_note)

    def test_candidate_scores_and_required_return_without_crash(self) -> None:
        """Une fiche partielle reste calculable (défauts, jamais crash)."""
        for prof in ("Prudent", "Équilibré", "Audacieux"):
            result = scoring.overall_score(self.candidate, prof)
            self.assertIsInstance(result["score"], float)
            self.assertTrue(result["verdict"])
            self.assertIsInstance(result["risk"], float)


class MissingIndicatorTolerance(unittest.TestCase):
    """Gestion fiches partielles / indicateurs non résolus."""

    def test_minimal_country_scores_with_defaults(self) -> None:
        minimal = {"id": "_synthetic_min", "indicators": {}}
        result = scoring.overall_score(minimal, "Équilibré")
        self.assertIsInstance(result["score"], float)
        self.assertTrue(scoring.component_scores(minimal))

    def test_synthetic_country_with_partial_indicators(self) -> None:
        partial = {
            "id": "_synthetic_partial",
            "indicators": {
                "inflation": {"value": 3.0},
                "debt_gdp": {"value": 60.0},
            },
        }
        for prof in ("Prudent", "Équilibré", "Audacieux"):
            self.assertIsInstance(
                scoring.overall_score(partial, prof)["score"], float
            )


class ScoringFormulaUnchanged(unittest.TestCase):
    """Partie D — formule/seuils/poids inchangés pour les AUTRES pays."""

    def test_all_non_lebanon_countries_exact_vs_baseline(self) -> None:
        countries = {c["id"]: c for c in data.countries()}
        self.assertIn("lebanon", countries)
        for cid, snapshot in BASELINE.items():
            if cid == "lebanon":  # seule exception approuvée (incrément 6.1)
                continue
            country = countries[cid]
            for prof, expected in snapshot["profiles"].items():
                got = scoring.overall_score(country, prof)
                for key in ("score", "verdict", "risk", "volatility"):
                    self.assertEqual(got[key], expected[key], (cid, prof, key))
        for cid, expected in COMPONENTS_EQUILIBRE.items():
            if cid == "lebanon":
                continue
            self.assertEqual(
                scoring.component_scores(countries[cid]),
                expected,
                cid,
            )


if __name__ == "__main__":
    unittest.main()
