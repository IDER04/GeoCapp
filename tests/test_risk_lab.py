"""Tests du Sovereign Risk Lab (Priorité 8 — phase 2).

Garanties :
1. CALCULS : taux réel = taux directeur − inflation (convention moteur),
   lecture dans les paliers existants de scoring.model(), position de
   dette dans le palier de solvabilité — aucune formule réinventée.
2. DONNÉES MANQUANTES : une métrique absente du schéma est indisponible
   (value=None), jamais remplacée par zéro ; une fiche future qui porte
   l'alias est lue automatiquement.
3. MILLÉSIMES MÉLANGÉS : warning explicite quand taux directeur et
   inflation n'ont pas le même millésime (Liban 2024×2025, Japon).
4. LOCALISATION : clés FR/EN présentes et non vides pour tous les
   libellés du lab ; la synthèse ne laisse passer aucune clé brute.
5. COUVERTURE : 12 métriques × 10 pays de production ; matrice
   comparative complète.
6. ISOLATION : les fonctions du lab n'écrivent rien ; la page se rend
   sans exception (FR puis EN).
"""

from __future__ import annotations

import copy
import hashlib
import pathlib
import unittest

from geocapital import data, freshness, i18n, risk_lab, scoring

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Tous les libellés i18n du lab (préfixes lâches : rl.* + nav.risk_lab).
RL_KEYS = [
    "nav.risk_lab",
    "rl.eyebrow",
    "rl.title",
    "rl.subtitle",
    "rl.select",
    "rl.section.fiscal",
    "rl.section.fiscal_sub",
    "rl.section.external",
    "rl.section.external_sub",
    "rl.section.macro",
    "rl.section.macro_sub",
    "rl.metric.fiscal_balance",
    "rl.metric.interest_revenue",
    "rl.metric.current_account",
    "rl.metric.external_debt_total",
    "rl.metric.external_debt_short",
    "rl.metric.reserves_import_months",
    "rl.metric.real_rate",
    "rl.why.fiscal_balance",
    "rl.why.interest_revenue",
    "rl.why.current_account",
    "rl.why.external_debt_total",
    "rl.why.external_debt_short",
    "rl.why.reserves_import_months",
    "rl.need.fiscal_balance",
    "rl.need.interest_revenue",
    "rl.need.current_account",
    "rl.need.external_debt_total",
    "rl.need.external_debt_short",
    "rl.need.reserves_import_months",
    "rl.chip.estimated",
    "rl.chip.conflicting",
    "rl.badge.derived",
    "rl.badge.observed",
    "rl.q.observed",
    "rl.q.estimated",
    "rl.q.conflicting",
    "rl.q.stale",
    "rl.q.unverified",
    "rl.warn.vintage_mismatch",
    "rl.real.title",
    "rl.real.sub",
    "rl.real.aligned",
    "rl.real.band_label",
    "rl.real.outside_label",
    "rl.real.xaxis",
    "rl.real.kpi.policy",
    "rl.real.kpi.inflation",
    "rl.real.kpi.real",
    "rl.real.kpi.bandscore",
    "rl.dsa.title",
    "rl.dsa.sub",
    "rl.dsa.position.below_low",
    "rl.dsa.position.within",
    "rl.dsa.position.above_high",
    "rl.dsa.band_note",
    "rl.dsa.limitation",
    "rl.dsa.growth_line",
    "rl.summary.title",
    "rl.summary.sub",
    "rl.summary.debt",
    "rl.summary.reserves",
    "rl.summary.macro",
    "rl.summary.real",
    "rl.summary.real_band",
    "rl.summary.real_outside",
    "rl.comp.section",
    "rl.comp.section_sub",
    "rl.comp.select",
    "rl.comp.select_help",
    "rl.comp.min_two",
    "rl.comp.chart_metric",
    "rl.comp.no_data",
    "rl.comp.legend",
    "rl.real.unavailable",
    "rl.details.title",
    "rl.details.sub",
    "rl.details.period",
    "rl.details.source",
    "rl.details.status",
    "rl.details.as_of",
    "rl.missing.th.why",
    "rl.missing.th.source",
    "rl.method.title",
    "rl.method.real_rate",
    "rl.method.bands",
    "rl.method.debt",
    "rl.method.reserves",
    "rl.method.caveat",
    "rl.method.assumption",
    "me.risklab.title",
    "me.risklab.sub",
    "me.risklab.body",
    "me.risklab.caption",
]


def _country(cid: str) -> dict:
    country = country_by_id(cid)
    assert country is not None, cid
    return country


def country_by_id(cid: str) -> dict | None:
    return data.country_by_id(cid)


def production_fingerprint() -> dict[str, str]:
    files = sorted((ROOT / "data").rglob("*.json"))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


class RealRateCalculations(unittest.TestCase):
    """Taux réel : convention moteur, paliers existants, alignement."""

    def test_real_rate_matches_engine_convention(self):
        for cid in ("usa", "france", "china"):
            country = _country(cid)
            detail = risk_lab.real_rate_detail(country)
            policy = country["indicators"]["policy_rate"]["value"]
            inflation = country["indicators"]["inflation"]["value"]
            self.assertAlmostEqual(detail["real_rate"], policy - inflation, places=9, msg=cid)

    def test_lebanon_real_rate_falls_in_documented_band(self):
        # Known issue K1 : 20.0 (2024) − 14.6 (2025) = 5.4 → palier [−8, 6] → 40.
        detail = risk_lab.real_rate_detail(_country("lebanon"))
        self.assertAlmostEqual(detail["real_rate"], 5.4)
        self.assertEqual(detail["band"], [-8.0, 6.0, 40.0])
        self.assertAlmostEqual(detail["band_score"], 40.0)

    def test_bands_come_from_scoring_model_not_redefined(self):
        detail = risk_lab.real_rate_detail(_country("usa"))
        expected = scoring.model()["components"]["stabilite"]["real_rate_bands"]
        self.assertEqual(detail["bands"], [list(band) for band in expected])
        # USA : réel 1.43 → palier [−1, 2] (score 95) — lecture du modèle.
        self.assertEqual(detail["band"], [-1.0, 2.0, 95.0])
        self.assertAlmostEqual(detail["band_score"], 95.0)

    def test_outside_band_falls_back_to_engine_outside_score(self):
        country = copy.deepcopy(_country("syria"))
        # réel hors paliers (ex. taux 1 %, inflation 50 % → −49)
        country["indicators"]["policy_rate"]["value"] = 1.0
        detail = risk_lab.real_rate_detail(country)
        self.assertIsNone(detail["band"])
        self.assertAlmostEqual(
            detail["band_score"],
            scoring.model()["components"]["stabilite"]["real_rate_outside_score"],
        )


class VintageAlignment(unittest.TestCase):
    """Millésimes mélangés : warning, jamais de correction."""

    def test_lebanon_mixed_vintages_flagged(self):
        detail = risk_lab.real_rate_detail(_country("lebanon"))
        self.assertTrue(detail["vintage_mismatch"])  # taux 2024 × inflation 2025
        self.assertFalse(detail["aligned"])

    def test_japan_mixed_vintages_flagged(self):
        # policy_rate « janv. 2025 » × inflation 2024 → millésimes différents.
        detail = risk_lab.real_rate_detail(_country("japan"))
        self.assertTrue(detail["vintage_mismatch"], detail)

    def test_aligned_vintages_not_flagged(self):
        detail = risk_lab.real_rate_detail(_country("usa"))
        self.assertFalse(detail["vintage_mismatch"])
        self.assertTrue(detail["aligned"])

    def test_derived_metric_carries_warning(self):
        metrics = {m["key"]: m for m in risk_lab.build_metrics(_country("lebanon"))}
        self.assertIn("vintage_mismatch", metrics["real_rate"]["warnings"])
        self.assertEqual(metrics["real_rate"]["kind"], "derived")


class MissingDataHandling(unittest.TestCase):
    """Indisponible ≠ zéro : explication + source requise, jamais inventé."""

    def test_all_six_requested_absent_metrics_are_unavailable_in_production(self):
        for cid in [c["id"] for c in data.countries()]:
            metrics = {m["key"]: m for m in risk_lab.build_metrics(_country(cid))}
            for key in (
                "fiscal_balance",
                "interest_revenue",
                "current_account",
                "external_debt_total",
                "external_debt_short",
                "reserves_import_months",
            ):
                self.assertFalse(metrics[key]["available"], f"{cid}.{key}")
                self.assertIsNone(metrics[key]["value"], f"{cid}.{key} — doit rester None, jamais 0")

    def test_future_schema_field_is_read_through_aliases(self):
        country = copy.deepcopy(_country("usa"))
        country["indicators"]["fiscal_balance"] = {
            "value": -6.3,
            "unit": "% du PIB",
            "date": "2024",
            "source": "Test",
        }
        metrics = {m["key"]: m for m in risk_lab.build_metrics(country)}
        self.assertTrue(metrics["fiscal_balance"]["available"])
        self.assertAlmostEqual(metrics["fiscal_balance"]["value"], -6.3)

    def test_imports_alone_do_not_create_import_months_coverage(self):
        # Les réserves en mois d'importations exigent une donnée compatible :
        # une donnée « imports » seule ne devient pas une couverture inventée.
        country = copy.deepcopy(_country("usa"))
        country["indicators"]["imports"] = {"value": 3000, "unit": "Mds $", "date": "2024", "source": "Test"}
        metrics = {m["key"]: m for m in risk_lab.build_metrics(country)}
        self.assertFalse(metrics["reserves_import_months"]["available"])

    def test_missing_inputs_block_complete_dsa_in_production(self):
        for cid in [c["id"] for c in data.countries()]:
            debt = risk_lab.debt_sustainability(_country(cid))
            self.assertFalse(debt["dsa_complete"], cid)
            self.assertIn("fiscal_balance", debt["missing_inputs"], cid)
            self.assertIn("interest_revenue", debt["missing_inputs"], cid)

    def test_dsa_completes_when_inputs_exist(self):
        country = copy.deepcopy(_country("usa"))
        country["indicators"]["fiscal_balance"] = {"value": -6.3, "date": "2024", "source": "T"}
        country["indicators"]["interest_revenue"] = {"value": 8.0, "date": "2024", "source": "T"}
        debt = risk_lab.debt_sustainability(country)
        self.assertTrue(debt["dsa_complete"])
        self.assertEqual(debt["missing_inputs"], [])

    def test_debt_position_mapping(self):
        self.assertEqual(risk_lab.debt_sustainability(_country("usa"))["position"], "within")
        synthetic = copy.deepcopy(_country("usa"))
        synthetic["indicators"]["debt_gdp"]["value"] = 10.0
        self.assertEqual(risk_lab.debt_sustainability(synthetic)["position"], "below_low")
        synthetic["indicators"]["debt_gdp"]["value"] = 300.0
        self.assertEqual(risk_lab.debt_sustainability(synthetic)["position"], "above_high")


class AuditStatusReuse(unittest.TestCase):
    """Le lab réutilise les statuts de l'audit qualité (pas de doublon)."""

    def test_lebanon_gdp_conflict_is_red(self):
        metrics = {m["key"]: m for m in risk_lab.build_metrics(_country("lebanon"))}
        self.assertEqual(metrics["gdp_growth"]["audit_status"], "conflicting")
        self.assertIn("conflicting", metrics["gdp_growth"]["warnings"])

    def test_lebanon_debt_estimated_is_orange(self):
        metrics = {m["key"]: m for m in risk_lab.build_metrics(_country("lebanon"))}
        self.assertEqual(metrics["debt_gdp"]["audit_status"], "estimated")
        self.assertIn("estimated", metrics["debt_gdp"]["warnings"])

    def test_display_status_mapping(self):
        """Chip de statut DONNÉE : conflit → rouge, estimation → orange,
        fraîcheur seule → neutre (jamais de style piloté par la fraîcheur)."""
        metrics = {m["key"]: m for m in risk_lab.build_metrics(_country("lebanon"))}
        from views.risk_lab_page import _status_chip  # import tardif (streamlit)

        status, chip = _status_chip(metrics["gdp_growth"])
        self.assertEqual(status, "red")
        self.assertEqual(chip, i18n.STRINGS["fr"]["rl.chip.conflicting"])
        status, chip = _status_chip(metrics["debt_gdp"])
        self.assertEqual(status, "orange")
        self.assertEqual(chip, i18n.STRINGS["fr"]["rl.chip.estimated"])
        # inflation : stale seule → statut neutre, pas de style d'alerte
        status, chip = _status_chip(metrics["inflation"])
        self.assertEqual(status, "green")
        self.assertEqual(chip, i18n.STRINGS["fr"]["rl.badge.observed"])


class Localization(unittest.TestCase):
    """Clés FR/EN du lab présentes, non vides ; synthèse traduite."""

    def test_all_lab_keys_exist_in_both_languages(self):
        for key in RL_KEYS:
            for lang in ("fr", "en"):
                self.assertIn(key, i18n.STRINGS[lang], f"{lang}:{key}")
                self.assertTrue(i18n.STRINGS[lang][key].strip(), f"{lang}:{key}")

    def test_summary_contains_no_raw_keys(self):
        i18n.st.session_state["lang"] = "fr"
        try:
            for cid in [c["id"] for c in data.countries()]:
                for line in risk_lab.summary_lines(_country(cid)):
                    self.assertNotIn("rl.", line, f"{cid}: clé brute dans la synthèse : {line}")
                    # régression : aucun placeholder {…} non substitué
                    self.assertNotRegex(line, r"\{[a-z_]+\}", f"{cid}: placeholder brut : {line}")
        finally:
            i18n.st.session_state["lang"] = "fr"

    def test_summary_changes_with_language(self):
        lbn = _country("lebanon")
        i18n.st.session_state["lang"] = "fr"
        french = risk_lab.summary_lines(lbn)
        i18n.st.session_state["lang"] = "en"
        try:
            english = risk_lab.summary_lines(lbn)
        finally:
            i18n.st.session_state["lang"] = "fr"
        self.assertNotEqual(french, english)
        self.assertEqual(len(french), len(english))


class Coverage(unittest.TestCase):
    """Couverture : 12 métriques × 10 pays ; matrice comparative."""

    def test_twelve_metrics_per_country(self):
        for cid in [c["id"] for c in data.countries()]:
            metrics = risk_lab.build_metrics(_country(cid))
            self.assertEqual(len(metrics), 12, cid)
            sections = {m["section"] for m in metrics}
            self.assertEqual(sections, {"fiscal", "external", "macro"}, cid)

    def test_expected_available_metrics(self):
        # production v1 : 5 observés + 1 dérivé disponibles, 6 indisponibles
        for cid in [c["id"] for c in data.countries()]:
            metrics = risk_lab.build_metrics(_country(cid))
            available = sorted(m["key"] for m in metrics if m["available"])
            self.assertEqual(
                available,
                ["debt_gdp", "gdp_growth", "inflation", "policy_rate", "real_rate", "reserves"],
                cid,
            )

    def test_comparison_matrix_full_grid(self):
        selected = [_country("usa"), _country("lebanon"), _country("syria")]
        matrix = risk_lab.comparison_matrix(selected)
        self.assertEqual(len(matrix["columns"]), 3)
        self.assertEqual(len(matrix["rows"]), 12)
        for row in matrix["rows"]:
            self.assertEqual(set(row["cells"]), {"usa", "lebanon", "syria"})
            for cell in row["cells"].values():
                self.assertIn("available", cell)

    def test_comparison_real_rate_row_has_mismatch_warning_for_lebanon(self):
        matrix = risk_lab.comparison_matrix([_country("usa"), _country("lebanon")])
        row = next(r for r in matrix["rows"] if r["key"] == "real_rate")
        self.assertIn("vintage_mismatch", row["cells"]["lebanon"]["warnings"])
        # USA : millésimes alignés (seul le flag stale peut apparaître).
        self.assertNotIn("vintage_mismatch", row["cells"]["usa"]["warnings"])


class Isolation(unittest.TestCase):
    """Les fonctions du lab n'écrivent rien ; la page se rend sans erreur."""

    def test_lab_calls_leave_production_untouched(self):
        before = production_fingerprint()
        for c in data.countries():
            risk_lab.build_metrics(c)
            risk_lab.real_rate_detail(c)
            risk_lab.debt_sustainability(c)
            risk_lab.summary_lines(c)
            risk_lab.comparison_matrix([c, _country("usa") if c["id"] != "usa" else _country("france")])
        self.assertEqual(production_fingerprint(), before)

    def test_page_renders_without_exception_fr_and_en(self):
        from streamlit.testing.v1 import AppTest

        for lang in ("fr", "en"):
            at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
            at.session_state["lang"] = lang
            # nav posé avant le premier rendu : la page d'accueil (carte)
            # n'est pas rendue — AppTest ne sait pas relire l'état du
            # radio « profil » quand ses options sont formatées en EN
            # (limitation préexistante de la lib de test, hors périmètre).
            at.session_state["nav"] = "risk_lab"
            at.run()
            self.assertFalse(bool(at.exception), f"[{lang}] exception: {at.exception}")
            # le sélecteur pays est présent et la navigation contient le lab
            self.assertTrue(any("risk_lab_country" == w.key for w in at.selectbox), lang)


class RawKeyRegression(unittest.TestCase):
    """Régression (signalement utilisateur) : aucune clé brute i18n rendue.

    Symptômes rapportés : « nav.risk_lab » dans la navigation et « RL.title »
    en titre de page. Diagnostic : les clés existent dans les DEUX dictionnaires
    (fr/en) et AppTest rend partout des libellés traduits — les symptômes sont
    cohérents avec un serveur Streamlit de longue date ayant chargé
    ``views/risk_lab_page.py``/``app.py`` AVANT l'ajout des blocs de clés
    (Streamlit ne recharge pas reliably les modules importés). Résolution :
    redémarrer ``streamlit run app.py``. Ces tests figent l'invariant : en FR
    comme en EN, la navigation, le titre et tous les textes rendus ne
    contiennent aucune clé brute ``rl.`` / ``nav.`` / ``me.``.
    """

    def _rendered_text(self, at) -> str:
        parts = [w.value for w in at.markdown]
        parts += [w.value for w in at.title]
        parts += [w.value for w in at.header]
        parts += [w.value for w in at.subheader]
        parts += [w.value for w in getattr(at, "caption", [])]
        return "\n".join(str(part) for part in parts)

    def test_no_raw_i18n_keys_rendered_fr_and_en(self):
        import re

        from streamlit.testing.v1 import AppTest

        for lang in ("fr", "en"):
            at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
            at.session_state["lang"] = lang
            at.session_state["nav"] = "risk_lab"
            at.run()
            self.assertFalse(bool(at.exception), f"[{lang}] exception: {at.exception}")

            # 1. Navigation : options traduites, libellé du lab présent,
            #    aucune option ne contient de clé brute.
            nav_options = [opt for w in at.radio if w.key == "nav" for opt in w.options]
            self.assertTrue(nav_options, f"[{lang}] radio de navigation introuvable")
            lab_label = i18n.STRINGS[lang]["nav.risk_lab"]
            # les options portent le préfixe icône (« ⚖  Lab risque souverain »)
            self.assertTrue(
                any(lab_label in option for option in nav_options),
                f"[{lang}] libellé de nav du lab absent",
            )
            for option in nav_options:
                self.assertNotIn("nav.", option, f"[{lang}] clé brute dans la nav : {option}")

            # 2. Titre de page : traduit (dans un <h1> du page head).
            rendered = self._rendered_text(at)
            self.assertIn(i18n.STRINGS[lang]["rl.title"], rendered, f"[{lang}] titre non traduit")

            # 3. Section « indisponible » groupée : titre traduit présent.
            #    (section_title échappe le HTML : comparer un fragment sans
            #    apostrophe, rendu tel quel dans les deux cas.)
            title_head = i18n.STRINGS[lang]["rl.missing.title"].split(" — ")[0]
            self.assertIn(title_head, rendered, f"[{lang}] section n.d. absente")

            # 4. Zéro clé brute rl./nav./me. dans tout texte rendu.
            for hit in re.findall(r"\b(?:rl|nav|me)\.[a-z_.]+", rendered):
                self.fail(f"[{lang}] clé brute rendue : {hit}")


class PresentationRegression(unittest.TestCase):
    """Présentation professionnelle (retour utilisateur) : plus de messages
    de maintenance sur les cartes ; les statuts qui changent la lecture
    d'une valeur ou d'une conclusion restent visibles, une seule fois."""

    def _lab_page(self, lang: str, country_id: str = "usa"):
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
        at.session_state["lang"] = lang
        at.session_state["nav"] = "risk_lab"
        at.session_state["country_id"] = country_id
        at.run()
        self.assertFalse(bool(at.exception), f"[{lang}] exception: {at.exception}")
        return at

    def _rendered(self, at) -> str:
        parts = [w.value for w in at.markdown]
        parts += [w.value for w in at.title]
        parts += [w.value for w in getattr(at, "caption", [])]
        return "\n".join(str(part) for part in parts)

    def test_no_maintenance_wording_or_warning_icons(self):
        for lang in ("fr", "en"):
            at = self._lab_page(lang)
            rendered = self._rendered(at)
            self.assertNotIn("à rafraîchir", rendered, lang)
            self.assertNotIn("to be refreshed", rendered, lang)
            self.assertNotIn("⚠", rendered, f"[{lang}] icône d'avertissement rendue")

    def test_lebanon_material_statuses_stay_visible(self):
        for lang in ("fr", "en"):
            at = self._lab_page(lang, "lebanon")
            rendered = self._rendered(at)
            # dette estimée : chip « Estimation », jamais présentée confirmée
            self.assertIn(i18n.STRINGS[lang]["rl.chip.estimated"], rendered, lang)
            # PIB en conflit : chip « Sources divergentes »
            self.assertIn(i18n.STRINGS[lang]["rl.chip.conflicting"], rendered, lang)
            # millésimes mélangés : UNE seule occurrence (panneau taux réel)
            fragment = "années différentes" if lang == "fr" else "different years"
            self.assertEqual(rendered.count(fragment), 1, f"[{lang}] avertissement dupliqué ou absent")
            self.assertNotIn("confirmée", rendered, lang)
            self.assertNotIn("most recent confirmed", rendered, lang)

    def test_details_expander_lists_per_indicator_status(self):
        for lang in ("fr", "en"):
            at = self._lab_page(lang, "lebanon")
            details_title = i18n.STRINGS[lang]["rl.details.title"]
            self.assertTrue(
                any(w.label == details_title for w in at.expander),
                f"[{lang}] expander « Détails des données » absent",
            )
            rendered = self._rendered(at)
            # statut PRÉCIS par indicateur : estimation pour la dette libanaise
            self.assertIn(i18n.STRINGS[lang]["rl.q.estimated"], rendered, lang)
            # fraîcheur : uniquement pour les millésimes réellement anciens
            stale_head = i18n.STRINGS[lang]["rl.q.stale"].split("({")[0].strip()
            self.assertIn(stale_head, rendered, lang)

    def test_comparison_legend_present(self):
        for lang in ("fr", "en"):
            at = self._lab_page(lang, "lebanon")
            self.assertIn(i18n.STRINGS[lang]["rl.comp.legend"], self._rendered(at), lang)


if __name__ == "__main__":
    unittest.main()
