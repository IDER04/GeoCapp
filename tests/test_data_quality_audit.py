"""Incrément 7.1 — tests de l'audit qualité des données (revue-first).

Garanties :
1. COUVERTURE : la matrice contient chaque pays de production × chaque
   clef d'indicateur (10 données + crp calculé + 6 qualitatifs) —
   aucune valeur manquante omise silencieusement.
2. CONFORMITÉ AU DISQUE : chaque ligne (valeur, période, source)
   provient réellement des fichiers de production, pas d'une copie.
3. STATUTS : vocabulaire contrôlé ; les absences (CDS non cotés) sont
   distinguées des blocs structurés sans valeur scalaire (indice,
   devise) ; les conflits listés sont exactement ceux documentés.
4. INFLUENCE SCORING : les sous-poids affichés correspondent à
   data/meta.json::scoring_model (aucun poids inventé) ; les clefs
   « display only » ne sont référencées dans aucune formule.
5. ISOLATION : la génération n'écrit que sous docs/ et data/audit/ et
   ne modifie aucun fichier de production (hachés avant/après).
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import pathlib
import tempfile
import unittest
import unittest.mock

from geocapital import data, scoring

_spec = importlib.util.spec_from_file_location(
    "data_quality_audit",
    pathlib.Path(__file__).resolve().parents[1] / "geocapital" / "data_quality_audit.py",
)
assert _spec is not None
dqa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dqa)

ROOT = pathlib.Path(__file__).resolve().parents[1]


def production_fingerprint() -> dict[str, str]:
    files = sorted((ROOT / "data").rglob("*.json"))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


class AuditMatrixCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = dqa.build_audit()

    def test_all_production_countries_present(self):
        self.assertEqual(self.audit["scope"]["countries"], 10)
        self.assertEqual(
            set(self.audit["scope"]["country_ids"]),
            {c["id"] for c in data.countries()},
        )

    def test_full_pair_coverage(self):
        scope = self.audit["scope"]
        self.assertEqual(scope["pairs"]["data"], 100)  # 10 pays × 10 indicateurs
        self.assertEqual(scope["pairs"]["computed"], 10)  # crp
        self.assertEqual(scope["pairs"]["qualitative"], 60)  # 10 × 6
        self.assertEqual(scope["pairs"]["total"], 170)

    def test_no_silently_omitted_missing_values(self):
        """Toute valeur absente du disque porte value_present=False et un statut."""
        countries = {c["id"]: c for c in data.countries()}
        for row in self.audit["matrix"]["data"]:
            block = countries[row["country_id"]]["indicators"].get(row["indicator_key"], {})
            self.assertEqual(row["value_present"], block.get("value") is not None, row)
            self.assertIn(row["data_status"], dqa.ALL_STATUSES)
        for row in self.audit["matrix"]["qualitative"]:
            self.assertTrue(row["value_present"], row)  # 60/60 évaluations présentes


class AuditMatrixAgreesWithDisk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = dqa.build_audit()
        cls.countries = {c["id"]: c for c in data.countries()}

    def test_data_rows_match_source_files(self):
        for row in self.audit["matrix"]["data"]:
            block = self.countries[row["country_id"]]["indicators"].get(row["indicator_key"], {})
            self.assertEqual(row["value"], block.get("value"), row)
            self.assertEqual(row["obs_period"], None if block.get("date") is None else str(block.get("date")), row)
            self.assertEqual(row["provenance"]["source"], block.get("source"), row)
            self.assertEqual(row["provenance"]["source_url"], block.get("source_url"), row)

    def test_computed_crp_matches_scoring(self):
        for row in self.audit["matrix"]["computed"]:
            crp, _ = scoring.country_risk_premium(self.countries[row["country_id"]])
            self.assertEqual(row["value"], crp, row)

    def test_qualitative_rows_match_files(self):
        for row in self.audit["matrix"]["qualitative"]:
            key = row["indicator_key"].split(":", 1)[1]
            self.assertEqual(row["value"], self.countries[row["country_id"]]["qualitative"].get(key), row)


class StatusVocabulary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = dqa.build_audit()
        cls.rows = [row for section in ("data", "computed", "qualitative") for row in cls.audit["matrix"][section]]

    def test_statuses_within_vocabulary(self):
        for row in self.rows:
            self.assertIn(row["data_status"], dqa.ALL_STATUSES, row)
            self.assertIn(row["confidence"], ("high", "medium", "low"), row)

    def test_missing_is_exactly_unquoted_cds(self):
        missing = [(r["country_id"], r["indicator_key"]) for r in self.rows if r["data_status"] == dqa.STATUS_MISSING]
        self.assertEqual(sorted(missing), [("lebanon", "cds"), ("syria", "cds")])
        for row in self.rows:
            if row["data_status"] == dqa.STATUS_MISSING:
                self.assertIn("documented_absence", row["status_flags"], row)

    def test_structured_blocks_without_scalar_not_missing(self):
        """equity_index/currency : pas de `value` scalaire mais des données — jamais 'missing'."""
        for row in self.rows:
            if row["indicator_key"] in ("equity_index", "currency"):
                self.assertNotEqual(row["data_status"], dqa.STATUS_MISSING, row)

    def test_conflicts_exactly_documented(self):
        conflicts = [(r["country_id"], r["indicator_key"]) for r in self.rows if r["data_status"] == dqa.STATUS_CONFLICTING]
        self.assertEqual(
            sorted(conflicts),
            sorted(dqa.DOCUMENTED_CONFLICTS.keys()),
        )
        for row in self.rows:
            if row["data_status"] == dqa.STATUS_CONFLICTING:
                self.assertIn("conflict_documented", row["status_flags"], row)

    def test_verified_is_lbn_inflation_plus_computed(self):
        verified = [
            (r["country_id"], r["indicator_key"])
            for r in self.rows
            if r["data_status"] == dqa.STATUS_VERIFIED and r["indicator_key"] != "crp"
        ]
        self.assertEqual(verified, [("lebanon", "inflation")])


class ScoringInfluenceMap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta = json.loads((ROOT / "data" / "meta.json").read_text(encoding="utf-8"))
        cls.audit = dqa.build_audit()

    def test_sub_weights_match_meta(self):
        sm = self.meta["scoring_model"]
        expected = {
            "gdp_growth": ("dynamisme", sm["components"]["dynamisme"]["weights"]["growth"]),
            "unemployment": ("dynamisme", sm["components"]["dynamisme"]["weights"]["unemployment"]),
            "inflation": ("stabilite", sm["components"]["stabilite"]["weights"]["inflation"]),
            "policy_rate": ("stabilite", sm["components"]["stabilite"]["weights"]["policy_rate"]),
            "debt_gdp": ("solvabilite", sm["components"]["solvabilite"]["weights"]["debt"]),
            "rating": ("solvabilite", sm["components"]["solvabilite"]["weights"]["rating"]),
            "cds": ("solvabilite", sm["components"]["solvabilite"]["weights"]["cds"]),
        }
        for key, (component, weight) in expected.items():
            influence = dqa.scoring_influence(key, self.meta)
            self.assertEqual(influence["component"], component, key)
            self.assertEqual(influence["sub_weight"], weight, key)

    def test_display_only_keys_enter_no_formula(self):
        for key in ("reserves", "equity_index", "currency"):
            influence = dqa.scoring_influence(key, self.meta)
            self.assertEqual(influence["role"], "display_only", key)
            self.assertIsNone(influence["component"], key)

    def test_profile_weights_influence_matches_meta(self):
        influence = dqa.scoring_influence("inflation", self.meta)
        self.assertEqual(
            influence["profile_component_weights"],
            {p: self.meta["scoring_model"]["profiles"][p]["weights"]["stabilite"] for p in ("Prudent", "Équilibré", "Audacieux")},
        )


class KnownIssues(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = dqa.build_audit()

    def test_real_rate_temporal_issue_is_recorded(self):
        k1 = next(f for f in self.audit["known_issues"] if f["id"] == "K1")
        self.assertIn("lebanon", k1["countries"])
        self.assertEqual(k1["tier"], 1)
        self.assertIn("20.0", k1["finding"])  # policy rate 2024
        self.assertIn("14.6", k1["finding"])  # inflation 2025

    def test_documented_conflicts_cite_their_source(self):
        for finding in self.audit["known_issues"]:
            if finding["id"] in ("K3", "K4"):
                self.assertIn("docs/", finding["evidence_required"])


class GenerationIsolation(unittest.TestCase):
    def test_generate_writes_only_audit_outputs(self):
        """La génération ne touche aucun fichier de production (hachés avant/après)."""
        before = production_fingerprint()
        with tempfile.TemporaryDirectory() as tmp:
            md_target = pathlib.Path(tmp) / "DATA_QUALITY_AUDIT.md"
            json_target = pathlib.Path(tmp) / "data_quality_audit.json"
            with unittest.mock.patch.object(dqa, "AUDIT_MD", md_target), unittest.mock.patch.object(dqa, "AUDIT_JSON", json_target), unittest.mock.patch.object(dqa, "AUDIT_DIR", json_target.parent):
                paths = dqa.generate()
            self.assertTrue(json_target.exists())
            loaded = json.loads(json_target.read_text(encoding="utf-8"))  # JSON valide
            self.assertIn("matrix", loaded)
            self.assertTrue(md_target.exists())
        self.assertEqual(production_fingerprint(), before, "production files must be byte-identical")

    def test_written_outputs_are_current_and_valid(self):
        """Les sorties livrées existent, sont valides et cohérentes."""
        loaded = json.loads((ROOT / "data" / "audit" / "data_quality_audit.json").read_text(encoding="utf-8"))
        self.assertEqual(loaded["scope"]["pairs"]["total"], 170)
        self.assertEqual(sum(loaded["status_counts"].values()), 170)
        md = (ROOT / "docs" / "DATA_QUALITY_AUDIT.md").read_text(encoding="utf-8")
        self.assertIn("Data Quality Audit", md)
        self.assertIn("K1", md)  # known issue du taux réel Liban


if __name__ == "__main__":
    unittest.main()
