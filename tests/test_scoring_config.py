"""Tests de refactorisation « paramètres du modèle » (Priorité 3 — Phase 1).

Garanties :
1. RÉGRESSION : les scores, verdicts, risques et composantes calculés après
   la migration vers `data/meta.json::scoring_model` sont **identiques** au
   baseline figé AVANT le refactor (fichier /tmp/geocapital_baseline.json,
   copié littéralement ci-dessous sous `BASELINE`).
2. SEUILS : `decide_verdict` coupe exactement aux bornes 76 / 62 / 45 / 38
   (+ condition dynamisme 55) et bloque la note NR/D/RD sans CDS coté.
3. SCHÉMA : toute configuration critique absente ou incohérente lève une
   `ConfigError` informative (chemin exact), sans repli silencieux.
4. AUTORITÉ DE LA MÉTADONNÉE : modifier un poids dans meta.json change
   réellement le score (le fichier est la source de vérité, pas le code).

Le baseline est figé lors de la recette du 2026-10-25 (avant le refactor).
Profilés testés : « Prudent », « Équilibré », « Audacieux ».

Seule exception, approuvée dans l'incrément 6.1 (Priorité 6) : les
lignes `lebanon` reflètent la mise à jour validée de l'inflation
(45,0 % @2024 → 14,6 % @2025, cf. docs/REFRESH_REVIEW.md entrée 2,
docs/DATA_AUDIT.md). Les lignes de tous les autres pays restent celles
du baseline pré-refactor : c'est exactement ce que cette suite vérifie.
"""

from __future__ import annotations

import copy
import json
import unittest
import unittest.mock

from geocapital import data, scoring

# ---------------------------------------------------------------------------
# Baseline figé avant le refactor (aucune recalibration autorisée ici)
# ---------------------------------------------------------------------------
BASELINE: dict[str, dict] = {
    "china": {"ke": 10.12, "profiles": {"Audacieux": {"score": 71.7, "verdict": "Investir avec prudence", "risk": 28.9, "volatility": 23.9}, "Prudent": {"score": 72.0, "verdict": "Investir avec prudence", "risk": 28.9, "volatility": 23.9}, "Équilibré": {"score": 72.1, "verdict": "Investir avec prudence", "risk": 28.9, "volatility": 23.9}}},
    "france": {"ke": 9.90, "profiles": {"Audacieux": {"score": 67.8, "verdict": "Investir avec prudence", "risk": 17.7, "volatility": 18.5}, "Prudent": {"score": 76.6, "verdict": "Investir", "risk": 17.7, "volatility": 18.5}, "Équilibré": {"score": 72.3, "verdict": "Investir avec prudence", "risk": 17.7, "volatility": 18.5}}},
    "japan": {"ke": 10.12, "profiles": {"Audacieux": {"score": 64.2, "verdict": "Investir avec prudence", "risk": 25.7, "volatility": 22.3}, "Prudent": {"score": 69.8, "verdict": "Investir avec prudence", "risk": 25.7, "volatility": 22.3}, "Équilibré": {"score": 67.2, "verdict": "Investir avec prudence", "risk": 25.7, "volatility": 22.3}}},
    "lebanon": {"ke": 31.20, "profiles": {"Audacieux": {"score": 20.5, "verdict": "Éviter", "risk": 78.4, "volatility": 47.6}, "Prudent": {"score": 20.9, "verdict": "Éviter", "risk": 78.4, "volatility": 47.6}, "Équilibré": {"score": 20.2, "verdict": "Éviter", "risk": 78.4, "volatility": 47.6}}},
    "morocco": {"ke": 12.60, "profiles": {"Audacieux": {"score": 65.7, "verdict": "Investir avec prudence", "risk": 31.2, "volatility": 25.0}, "Prudent": {"score": 68.3, "verdict": "Investir avec prudence", "risk": 31.2, "volatility": 25.0}, "Équilibré": {"score": 66.8, "verdict": "Investir avec prudence", "risk": 31.2, "volatility": 25.0}}},
    "saudi": {"ke": 10.12, "profiles": {"Audacieux": {"score": 67.3, "verdict": "Investir avec prudence", "risk": 22.4, "volatility": 20.7}, "Prudent": {"score": 74.5, "verdict": "Investir avec prudence", "risk": 22.4, "volatility": 20.7}, "Équilibré": {"score": 70.7, "verdict": "Investir avec prudence", "risk": 22.4, "volatility": 20.7}}},
    "south_africa": {"ke": 13.95, "profiles": {"Audacieux": {"score": 48.1, "verdict": "Attendre", "risk": 39.5, "volatility": 29.0}, "Prudent": {"score": 55.5, "verdict": "Attendre", "risk": 39.5, "volatility": 29.0}, "Équilibré": {"score": 51.9, "verdict": "Attendre", "risk": 39.5, "volatility": 29.0}}},
    "syria": {"ke": 31.95, "profiles": {"Audacieux": {"score": 12.4, "verdict": "Éviter", "risk": 90.4, "volatility": 53.4}, "Prudent": {"score": 10.7, "verdict": "Éviter", "risk": 90.4, "volatility": 53.4}, "Équilibré": {"score": 11.5, "verdict": "Éviter", "risk": 90.4, "volatility": 53.4}}},
    "uae": {"ke": 9.75, "profiles": {"Audacieux": {"score": 83.2, "verdict": "Investir", "risk": 17.7, "volatility": 18.5}, "Prudent": {"score": 83.9, "verdict": "Investir", "risk": 17.7, "volatility": 18.5}, "Équilibré": {"score": 83.0, "verdict": "Investir", "risk": 17.7, "volatility": 18.5}}},
    "usa": {"ke": 9.53, "profiles": {"Audacieux": {"score": 76.2, "verdict": "Investir", "risk": 17.4, "volatility": 18.3}, "Prudent": {"score": 80.3, "verdict": "Investir", "risk": 17.4, "volatility": 18.3}, "Équilibré": {"score": 78.2, "verdict": "Investir", "risk": 17.4, "volatility": 18.3}}},
}
PROFILES = ("Prudent", "Équilibré", "Audacieux")
COMPONENTS_EQUILIBRE = {  # composantes Équilibré (indépendantes du profil)
    "china": {"dynamisme": 86.6, "institutions": 61.0, "ouverture": 53.2, "solvabilite": 71.2, "stabilite": 77.4},
    "usa": {"dynamisme": 71.6, "institutions": 76.4, "ouverture": 77.2, "solvabilite": 73.6, "stabilite": 94.4},
    "lebanon": {"dynamisme": 5.0, "institutions": 25.0, "ouverture": 46.0, "solvabilite": 7.9, "stabilite": 31.5},
}


def real_meta() -> dict:
    """Méta réel de disque (bypass le cache Streamlit)."""
    with open("data/meta.json", encoding="utf-8") as handle:
        return json.load(handle)


class TestBaselineRegression(unittest.TestCase):
    """Les résultats actuels doivent reproduire le baseline au dixième."""

    def test_scores_and_verdicts_all_countries_all_profiles(self):
        countries = {c["id"]: c for c in data.countries()}
        self.assertEqual(set(countries), set(BASELINE), "corpus pays du baseline ≠ corpus actuel")
        mismatches: list[str] = []
        for country_id, expected in BASELINE.items():
            country = countries[country_id]
            for profile in PROFILES:
                result = scoring.overall_score(country, profile)
                exp = expected["profiles"][profile]
                for field in ("score", "verdict", "risk", "volatility"):
                    if result[field] != exp[field]:
                        mismatches.append(
                            f"{country_id}/{profile}/{field}: {result[field]!r} ≠ {exp[field]!r}"
                        )
        self.assertEqual(mismatches, [], "écarts vs baseline pré-refactor")

    def test_required_return_ke(self):
        countries = {c["id"]: c for c in data.countries()}
        for country_id, expected in BASELINE.items():
            ke = scoring.required_return(countries[country_id])["ke"]
            self.assertEqual(ke, expected["ke"], f"Ke {country_id}")

    def test_component_scores_equilibre(self):
        countries = {c["id"]: c for c in data.countries()}
        for country_id, expected in COMPONENTS_EQUILIBRE.items():
            components = scoring.component_scores(countries[country_id])
            self.assertEqual(components, expected, f"composantes Équilibré {country_id}")

    def test_spot_verdicts_documented(self):
        """Verdicts de référence cités dans la documentation."""
        countries = {c["id"]: c for c in data.countries()}
        self.assertEqual(scoring.overall_score(countries["uae"], "Équilibré")["verdict"], "Investir")
        self.assertEqual(scoring.overall_score(countries["usa"], "Équilibré")["verdict"], "Investir")
        self.assertEqual(scoring.overall_score(countries["south_africa"], "Équilibré")["verdict"], "Attendre")
        self.assertEqual(scoring.overall_score(countries["lebanon"], "Équilibré")["verdict"], "Éviter")
        self.assertEqual(scoring.overall_score(countries["syria"], "Équilibré")["verdict"], "Éviter")

    def test_unknown_profile_falls_back_to_equilibre(self):
        countries = {c["id"]: c for c in data.countries()}
        result = scoring.overall_score(countries["usa"], "profil inexistant")
        self.assertEqual(result["score"], BASELINE["usa"]["profiles"]["Équilibré"]["score"])


class TestVerdictBoundaries(unittest.TestCase):
    """`decide_verdict` : bornes exactes (fonction pure, composantes forgées)."""

    def setUp(self):
        verdicts = scoring.model()["verdicts"]
        self.assertEqual(verdicts["invest_min"], 76.0)
        self.assertEqual(verdicts["caution_min"], 62.0)
        self.assertEqual(verdicts["wait_min"], 45.0)
        self.assertEqual(verdicts["wait_rescue_score"], 38.0)
        self.assertEqual(verdicts["wait_rescue_dynamisme"], 55.0)
        self.assertEqual(sorted(verdicts["blocking_ratings"]), ["D", "NR", "RD"])
        self.components = {k: 50.0 for k in ("dynamisme", "stabilite", "solvabilite", "institutions", "ouverture")}

    def country(self, rating: str = "A", cds: float | None = 100.0) -> dict:
        return {"id": "test", "indicators": {"rating": {"value": rating}, "cds": {"value": cds}}}

    def verdict(self, score: float, country: dict | None = None, dynamisme: float = 50.0) -> str:
        components = {**self.components, "dynamisme": dynamisme}
        verdict, _ = scoring.decide_verdict(score, components, country or self.country())
        return verdict

    def test_invest_boundary_is_76_inclusive(self):
        self.assertEqual(self.verdict(76.0), "Investir")
        self.assertEqual(self.verdict(75.9), "Investir avec prudence")

    def test_caution_boundary_is_62_inclusive(self):
        self.assertEqual(self.verdict(62.0), "Investir avec prudence")
        self.assertEqual(self.verdict(61.9), "Attendre")

    def test_wait_boundary_is_45_inclusive(self):
        self.assertEqual(self.verdict(45.0), "Attendre")
        self.assertEqual(self.verdict(44.9), "Éviter")

    def test_rescue_rule_needs_score_38_and_dynamisme_55(self):
        self.assertEqual(self.verdict(38.0, dynamisme=55.0), "Attendre")
        self.assertEqual(self.verdict(37.9, dynamisme=55.0), "Éviter")
        self.assertEqual(self.verdict(38.0, dynamisme=54.9), "Éviter")
        self.assertEqual(self.verdict(40.0, dynamisme=30.0), "Éviter")

    def test_blocking_rating_without_cds_caps_at_wait(self):
        blocked = self.country(rating="NR", cds=None)
        self.assertEqual(self.verdict(90.0, country=blocked), "Attendre")
        self.assertEqual(self.verdict(80.0, country=blocked), "Attendre")
        # CDS coté (même élevé) : pas de blocage.
        quoted = self.country(rating="NR", cds=2000.0)
        self.assertEqual(self.verdict(90.0, country=quoted), "Investir")
        # Notations D / RD bloquent aussi.
        for rating in ("D", "RD"):
            blocked = self.country(rating=rating, cds=None)
            self.assertEqual(self.verdict(90.0, country=blocked), "Attendre")

    def test_invest_with_quoted_cds_even_at_nr(self):
        quoted = self.country(rating="NR", cds=500.0)
        self.assertEqual(self.verdict(80.0, country=quoted), "Investir")


class TestConfigValidation(unittest.TestCase):
    """Schéma strict : chemin exact dans chaque ConfigError, aucun repli."""

    def setUp(self):
        self.meta = real_meta()
        self.addCleanup(scoring.reset_model_cache)

    def expect_error(self, meta: dict, needle: str | None = None) -> str:
        with self.assertRaises(scoring.ConfigError) as ctx:
            scoring.validate_model_params(meta)
        message = str(ctx.exception)
        if needle is not None:
            self.assertIn(needle, message)
        return message

    def test_real_meta_validates(self):
        config = scoring.validate_model_params(real_meta())
        self.assertIn("Équilibré", config["profiles"])
        self.assertEqual(config["verdicts"]["invest_min"], 76.0)
        self.assertEqual(config["financial"]["risk_free_rate"], 4.2)

    def test_missing_scoring_model(self):
        meta = real_meta()
        del meta["scoring_model"]
        message = self.expect_error(meta)
        self.assertIn("scoring_model", message)

    def test_missing_financial_params_section(self):
        meta = real_meta()
        del meta["financial_params"]
        self.expect_error(meta, "financial_params")

    def test_missing_financial_params_key(self):
        meta = real_meta()
        del meta["financial_params"]["beta"]
        self.expect_error(meta, "financial_params.beta")

    def test_financial_out_of_range(self):
        meta = real_meta()
        meta["financial_params"]["risk_free_rate"] = 25.0
        self.expect_error(meta, "risk_free_rate")

    def test_profile_weight_sum_not_one(self):
        meta = real_meta()
        meta["scoring_model"]["profiles"]["Audacieux"]["weights"]["dynamisme"] = 0.30
        self.expect_error(meta, "profiles.Audacieux.weights")

    def test_profile_missing_component(self):
        meta = real_meta()
        del meta["scoring_model"]["profiles"]["Prudent"]["weights"]["ouverture"]
        self.expect_error(meta, "profiles.Prudent.weights")

    def test_profile_unknown_component(self):
        meta = real_meta()
        meta["scoring_model"]["profiles"]["Prudent"]["weights"]["mystere"] = 0.0
        self.expect_error(meta, "composantes inconnues")

    def test_non_numeric_weight(self):
        meta = real_meta()
        meta["scoring_model"]["risk"]["weights"]["stabilite"] = "0.40"
        self.expect_error(meta, "risk.weights.stabilite")

    def test_negative_weight(self):
        meta = real_meta()
        meta["scoring_model"]["components"]["dynamisme"]["weights"]["growth"] = -0.2
        self.expect_error(meta, "dynamisme.weights.growth")

    def test_missing_component_section(self):
        meta = real_meta()
        del meta["scoring_model"]["components"]["ouverture"]
        self.expect_error(meta, "components.ouverture")

    def test_missing_sub_weight(self):
        meta = real_meta()
        del meta["scoring_model"]["components"]["stabilite"]["weights"]["currency"]
        self.expect_error(meta, "stabilite.weights")

    def test_invalid_range_pair(self):
        meta = real_meta()
        meta["scoring_model"]["components"]["solvabilite"]["debt_range"] = [180.0, 20.0]
        self.expect_error(meta, "debt_range")

    def test_real_rate_bands_bad_score(self):
        meta = real_meta()
        meta["scoring_model"]["components"]["stabilite"]["real_rate_bands"][0][2] = 150.0
        self.expect_error(meta, "real_rate_bands[0]")

    def test_verdict_thresholds_unordered(self):
        meta = real_meta()
        meta["scoring_model"]["verdicts"]["invest_min"] = 50.0  # < caution_min 62
        self.expect_error(meta, "verdicts")

    def test_blocking_ratings_not_a_list(self):
        meta = real_meta()
        meta["scoring_model"]["verdicts"]["blocking_ratings"] = "NR"
        self.expect_error(meta, "blocking_ratings")

    def test_ratings_tables_length_mismatch(self):
        meta = real_meta()
        del meta["scoring_model"]["ratings"]["spreads"]["NR"]
        self.expect_error(meta, "ratings")


class TestMetadataAuthority(unittest.TestCase):
    """meta.json est la source de vérité : tamper → résultat différent/error."""

    def setUp(self):
        self.addCleanup(scoring.reset_model_cache)
        scoring.reset_model_cache()
        self.usa = copy.deepcopy({c["id"]: c for c in data.countries()}["usa"])

    def patch_meta(self, meta: dict) -> None:
        """Mock data.load_data (module attr). Le contenu simulé diffère du
        disque (signature de contenu), donc le cache de model() l'invalide."""
        patcher = unittest.mock.patch.object(data, "load_data", return_value=meta)
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_tampered_weight_changes_score(self):
        reference = scoring.overall_score(self.usa, "Équilibré")["score"]
        self.assertEqual(reference, 78.2)

        meta = real_meta()
        weights = meta["scoring_model"]["profiles"]["Équilibré"]["weights"]
        weights["stabilite"] = 0.50   # 0.20 → 0.50 (usa.stabilite = 94.4 : le score monte)
        weights["solvabilite"] = 0.10  # 0.25 → 0.10
        weights["ouverture"] = 0.0    # 0.15 → 0.00 (somme = 1.00)
        self.patch_meta(meta)

        tampered = scoring.overall_score(self.usa, "Équilibré")["score"]
        self.assertNotEqual(tampered, reference)
        self.assertEqual(
            round(71.6 * 0.25 + 94.4 * 0.50 + 73.6 * 0.10 + 76.4 * 0.15 + 77.2 * 0.0, 1),
            tampered,
            "le score calculé n'applique pas les poids de la méta",
        )

    def test_tampered_threshold_changes_verdict(self):
        """usa/Équilibré = 78.2 : Investir → prudence → Attendre selon seuils."""
        self.assertEqual(scoring.overall_score(self.usa, "Équilibré")["verdict"], "Investir")

        meta = real_meta()
        meta["scoring_model"]["verdicts"]["invest_min"] = 100.0  # inatteignable
        self.patch_meta(meta)
        self.assertEqual(
            scoring.overall_score(self.usa, "Équilibré")["verdict"],
            "Investir avec prudence",
        )

        meta = real_meta()
        meta["scoring_model"]["verdicts"]["invest_min"] = 100.0
        meta["scoring_model"]["verdicts"]["caution_min"] = 90.0  # glisse sous Attendre
        self.patch_meta(meta)
        self.assertEqual(
            scoring.overall_score(self.usa, "Équilibré")["verdict"],
            "Attendre",
        )

    def test_invalid_config_raises_from_scoring_not_silent(self):
        """ConfigError remonte aux appels métier (avalé par l'app, jamais caché)."""
        meta = real_meta()
        del meta["scoring_model"]["verdicts"]["invest_min"]
        self.patch_meta(meta)
        with self.assertRaises(scoring.ConfigError) as ctx:
            scoring.overall_score(self.usa, "Équilibré")
        self.assertIn("verdicts.invest_min", str(ctx.exception))

    def test_cache_revalidates_on_content_change(self):
        first = scoring.overall_score(self.usa, "Prudent")["score"]
        self.assertEqual(first, 80.3)
        # Second appel : la méta identique réutilise le cache (résultat identique)
        second = scoring.overall_score(self.usa, "Prudent")["score"]
        self.assertEqual(second, first)


if __name__ == "__main__":
    unittest.main()
