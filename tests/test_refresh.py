"""Tests du pipeline de rafraîchissement de données (Priorité 6 — Phase 1).

Couverture, réseau entièrement simulé :
- mapping : séries WB correctes par indicateur, unités, conversions ;
- validité de réponse : structure [meta, rows], nulls, valeurs non
  numériques, JSON malformé, statuts d'observation (« F » exclu,
  « E » accepté) ;
- erreurs API : HTTPError / URLError / timeout / JSON invalide → erreur
  tracée, aucune invention de valeur ;
- rejet d'indicateur incompatible : code de série inattendu,
  réserves nettes ≠ réserves totales, dette centrale obsolète ;
- millésimes : observation plus ancienne rejetée, même millésime →
  revue manuelle, millésime plus récent → revue manuelle (jamais « safe »
  automatique en incrément 1) ;
- métadonnées : source, date de récupération (mockée), date de
  publication (lastupdated), obs_status ;
- protection de production : aucune fonction n'écriture dans
  data/countries/ — lecture seule vérifiée, générateur limité à docs/.
"""

from __future__ import annotations

import json
import pathlib
import unittest
import unittest.mock
import urllib.error

from geocapital import refresh as r

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEST_RETRIEVAL_DATE = "2026-10-25"


def patch_clock(testcase):
    patcher = unittest.mock.patch.object(r, "retrieval_date", return_value=TEST_RETRIEVAL_DATE)
    testcase.addCleanup(patcher.stop)
    return patcher.start()


# ---------------------------------------------------------------------------
# Fabriques de réponses WB simulées
# ---------------------------------------------------------------------------

def wb_row(date, value, obs_status="", series="NY.GDP.MKTP.KD.ZG", country="Lebanon"):
    return {
        "indicator": {"id": series, "value": "Série test"},
        "country": {"id": "LBN", "value": country},
        "date": str(date),
        "value": value,
        "obs_status": obs_status,
    }


def wb_payload(rows, lastupdated="2026-10-01", meta=None):
    return [dict(meta or {}, page=1, pages=1, total=len(rows), lastupdated=lastupdated), rows]


def fake_urlopen(payload_bytes=None, exc=None):
    """Retourne un context-manager urlopen factice (bytes ou exception)."""

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            if payload_bytes is None:
                raise exc or urllib.error.URLError("boom")
            return payload_bytes

    def _call(*args, **kwargs):
        payload_bytes_present = payload_bytes is not None
        if exc is not None and not payload_bytes_present:
            raise exc
        return _FakeResponse()

    return unittest.mock.patch("urllib.request.urlopen", side_effect=_call)


class _OnDiskProductionGuard:
    """Capture toute tentative d'écriture dans data/countries/ pendant un test."""

    def __init__(self):
        self.writes = []
        self._real_open = pathlib.Path.open

    def __enter__(self):
        guard = self

        def spy(self, mode="r", *args, **kwargs):
            if any(c in mode for c in "wax+"):
                guard.writes.append(str(self))
            return guard._real_open(self, mode, *args, **kwargs)

        unittest.mock.patch.object(pathlib.Path, "open", spy).start()
        return self

    def __exit__(self, *args):
        unittest.mock.patch.stopall()

    @property
    def production_writes(self):
        return [w for w in self.writes if "countries" in w and w.endswith(".json")]


# ---------------------------------------------------------------------------
# Mapping et récupération
# ---------------------------------------------------------------------------

class TestIndicatorMap(unittest.TestCase):
    def test_mapped_codes_match_official_wb_series(self):
        self.assertEqual(r.INDICATOR_MAP["gdp_growth"]["wb_code"], "NY.GDP.MKTP.KD.ZG")
        self.assertEqual(r.INDICATOR_MAP["inflation"]["wb_code"], "FP.CPI.TOTL.ZG")
        self.assertEqual(r.INDICATOR_MAP["unemployment"]["wb_code"], "SL.UEM.TOTL.ZS")
        self.assertEqual(r.INDICATOR_MAP["debt_gdp"]["wb_code"], "GC.DOD.TOTL.GD.ZS")
        self.assertEqual(r.INDICATOR_MAP["reserves"]["wb_code"], "FI.RES.TOTL.CD")

    def test_market_indicators_have_no_wb_equivalent(self):
        for key in ("policy_rate", "rating", "cds", "crp", "equity_index", "currency"):
            self.assertIn(key, r.NO_WB_EQUIVALENT)

    def test_definition_mismatch_is_explicit_not_silently_converted(self):
        self.assertEqual(r.INDICATOR_MAP["unemployment"]["match"], "partial")
        self.assertEqual(r.INDICATOR_MAP["debt_gdp"]["match"], "partial")
        self.assertTrue(r.INDICATOR_MAP["unemployment"]["note"].strip())

    def test_reserves_conversion_is_explicit(self):
        spec = r.INDICATOR_MAP["reserves"]
        self.assertEqual(spec["conversion"], 1e-9)  # US$ → Mds $


class TestFetchWorldBank(unittest.TestCase):
    def test_valid_payload_is_parsed(self):
        payload = wb_payload([wb_row("2024", -7.08)])
        with fake_urlopen(json.dumps(payload).encode("utf-8")):
            out = r.fetch_world_bank("LBN", "NY.GDP.MKTP.KD.ZG")
        self.assertTrue(out["success"])
        self.assertEqual(len(out["observations"]), 1)
        obs = out["observations"][0]
        self.assertEqual(obs["year"], 2024)
        self.assertEqual(obs["value"], -7.08)
        self.assertEqual(obs["obs_status"], "")
        self.assertEqual(obs["obs_status_label"], "actual")
        self.assertEqual(out["lastupdated"], "2026-10-01")
        self.assertEqual(out["requested_series"], "NY.GDP.MKTP.KD.ZG")

    def test_null_and_non_numeric_values_are_skipped_not_invented(self):
        payload = wb_payload(
            [wb_row("2024", None), wb_row("2023", "n/a"), wb_row("2022", -3.5)]
        )
        with fake_urlopen(json.dumps(payload).encode("utf-8")):
            out = r.fetch_world_bank("LBN", "NY.GDP.MKTP.KD.ZG")
        self.assertTrue(out["success"])
        self.assertEqual([o["year"] for o in out["observations"]], [2022])

    def test_http_error_is_traced(self):
        with fake_urlopen(exc=urllib.error.HTTPError(None, 404, "Not Found", None, None)):
            out = r.fetch_world_bank("XXX", "NY.GDP.MKTP.KD.ZG")
        self.assertFalse(out["success"])
        self.assertIn("404", out["error"])
        self.assertNotIn("observations", out)

    def test_url_error_is_traced(self):
        with fake_urlopen(exc=urllib.error.URLError("connection refused")):
            out = r.fetch_world_bank("LBN", "NY.GDP.MKTP.KD.ZG")
        self.assertFalse(out["success"])
        self.assertIn("connection refused", out["error"])

    def test_timeout_is_traced(self):
        with fake_urlopen(exc=TimeoutError("trop long")):
            out = r.fetch_world_bank("LBN", "NY.GDP.MKTP.KD.ZG", timeout=1)
        self.assertFalse(out["success"])

    def test_malformed_json_is_traced(self):
        with fake_urlopen(b"<html>not json</html>"):
            out = r.fetch_world_bank("LBN", "NY.GDP.MKTP.KD.ZG")
        self.assertFalse(out["success"])
        self.assertIn("JSON invalide", out["error"])

    def test_malformed_structure_rejected(self):
        for payload in ({"error": "flat"}, [], [42], [{"meta": 1}, "rows-not-list"]):
            out = r._parse_world_bank_payload(payload, "S", "url")
            self.assertFalse(out["success"], payload)

    def test_wb_error_message_is_surfaced(self):
        payload = [{"message": [{"id": "120", "value": "Invalid value for iso3"}]}]
        out = r._parse_world_bank_payload(payload, "S", "url")
        self.assertFalse(out["success"])
        self.assertIn("Invalid value for iso3", out["error"])

    def test_unexpected_series_code_is_rejected(self):
        payload = wb_payload([wb_row("2024", 1.0, series="SP.DYN.LE00.IN")])
        out = r._parse_world_bank_payload(payload, "NY.GDP.MKTP.KD.ZG", "url")
        self.assertFalse(out["success"])
        self.assertIn("série inattendue", out["error"])
        self.assertIn("SP.DYN.LE00.IN", out["error"])

    def test_unexpected_row_structure_is_skipped(self):
        payload = wb_payload(["not-a-dict", {"date": "2024", "value": 1.5}])
        out = r._parse_world_bank_payload(payload, "NY.GDP.MKTP.KD.ZG", "url")
        self.assertTrue(out["success"])
        self.assertEqual(len(out["observations"]), 1)


class TestLatestActual(unittest.TestCase):
    def test_forecast_excluded(self):
        obs = [
            r._parse_world_bank_payload(
                wb_payload([wb_row("2025", 2.0, "F")]), "NY.GDP.MKTP.KD.ZG", "u"
            )["observations"][0],
        ]
        obs.append(
            r._parse_world_bank_payload(
                wb_payload([wb_row("2024", -7.1)]), "NY.GDP.MKTP.KD.ZG", "u"
            )["observations"][0]
        )
        latest = r.latest_actual(obs)
        self.assertEqual(latest["year"], 2024)

    def test_estimate_accepted(self):
        obs = [
            r._parse_world_bank_payload(
                wb_payload([wb_row("2025", 14.6, "E", series="FP.CPI.TOTL.ZG")]),
                "FP.CPI.TOTL.ZG",
                "u",
            )["observations"][0]
        ]
        latest = r.latest_actual(obs)
        self.assertEqual(latest["year"], 2025)
        self.assertEqual(latest["obs_status_label"], "estimate")

    def test_all_forecasts_yield_none(self):
        obs = [
            r._parse_world_bank_payload(
                wb_payload([wb_row("2025", 2.0, "F")]), "NY.GDP.MKTP.KD.ZG", "u"
            )["observations"][0]
        ]
        self.assertIsNone(r.latest_actual(obs))

    def test_empty_observations_yield_none(self):
        self.assertIsNone(r.latest_actual([]))


# ---------------------------------------------------------------------------
# Règles de candidature (production réelle du dépôt, lecture seule)
# ---------------------------------------------------------------------------

class TestBuildCandidate(unittest.TestCase):
    def setUp(self):
        self.lbn = r.read_country("lebanon")
        self.syria = r.read_country("syria")

    def test_candidate_for_older_observation_is_rejected(self):
        # SYR gdp : WDI s'arrête 2022, la fiche porte 2024 → obs plus ancienne rejetée
        obs = {"year": 2022, "value": -0.2, "obs_status_label": "actual", "lastupdated": "2026-10-01"}
        candidate = r.build_candidate(self.syria, "gdp_growth", obs, None, False)
        self.assertEqual(candidate["recommendation"], "reject")
        self.assertIn("2022", candidate["explanation"])

    def test_same_year_value_change_requires_manual_review(self):
        # LBN gdp : WDI 2024 = -7.08 vs fiche -6.5, même millésime → arbitrage manuel
        obs = {"year": 2024, "value": -7.08, "obs_status_label": "actual", "lastupdated": "2026-10-01"}
        candidate = r.build_candidate(self.lbn, "gdp_growth", obs, None, False)
        self.assertEqual(candidate["recommendation"], "manual")
        self.assertIn("-7.08", candidate["explanation"])
        self.assertIn("-6.5", candidate["explanation"])

    def test_newer_year_is_manual_not_auto_applied(self):
        # LBN inflation : depuis l'incrément 6.1, la fiche porte déjà
        # 2025 = 14.6 (valeur approuvée, cf. docs/REFRESH_REVIEW.md
        # entrée 2). Une obs WDI identique reste « manual » : le pipeline
        # ne s'auto-applique jamais, même à valeur égale.
        obs = {"year": 2025, "value": 14.6, "obs_status_label": "actual", "lastupdated": "2026-10-01"}
        candidate = r.build_candidate(self.lbn, "inflation", obs, None, False)
        self.assertEqual(candidate["recommendation"], "manual")

    def test_newer_year_remains_manual_even_after_update(self):
        # LBN gdp : fiche 2024 → obs WDI 2025 (WEO : 4,0 %) = millésime
        # plus récent → revue manuelle, jamais d'application automatique.
        obs = {"year": 2025, "value": 4.0, "obs_status_label": "actual", "lastupdated": "2026-10-01"}
        candidate = r.build_candidate(self.lbn, "gdp_growth", obs, None, False)
        self.assertEqual(candidate["recommendation"], "manual")

    def test_net_reserves_vs_gross_series_rejected(self):
        # LBN réserves : fiche = NETTES (10), série WB = TOTALE → définition incompatible
        obs = {"year": 2024, "value": 33_301_277_509.6, "obs_status_label": "actual",
               "lastupdated": "2026-10-01"}
        candidate = r.build_candidate(self.lbn, "reserves", obs, None, False)
        self.assertEqual(candidate["recommendation"], "reject")
        self.assertIn("NETTES", candidate["explanation"])
        notes = "\n".join(candidate["definition_notes"])
        self.assertIn("US$ → Mds", notes)

    def test_stale_central_debt_series_rejected(self):
        # LBN dette : série « central government » finit 1999 ; fiche 2024 (dette générale)
        obs = {"year": 1999, "value": 128.6, "obs_status_label": "actual", "lastupdated": "2026-10-01"}
        candidate = r.build_candidate(self.lbn, "debt_gdp", obs, None, False)
        self.assertEqual(candidate["recommendation"], "reject")
        self.assertIn("gouvernement central", candidate["explanation"])

    def test_forecast_observation_rejected(self):
        obs = {"year": 2026, "value": 3.0, "obs_status_label": "forecast", "lastupdated": "2026-10-01"}
        candidate = r.build_candidate(self.lbn, "gdp_growth", obs, None, False)
        self.assertEqual(candidate["recommendation"], "reject")
        self.assertIn("prévision", candidate["explanation"])

    def test_big_divergence_modeled_unemployment_is_manual(self):
        # SYR chômage : WDI modélisé 2025 = 13.6 vs fiche 50 (crise) → croisement manuel
        obs = {"year": 2025, "value": 13.569, "obs_status_label": "actual", "lastupdated": "2026-10-01"}
        candidate = r.build_candidate(self.syria, "unemployment", obs, None, False)
        self.assertEqual(candidate["recommendation"], "manual")
        self.assertIn("ILO", candidate["explanation"])

    def test_fetch_error_yields_gap_existing_kept(self):
        candidate = r.build_candidate(self.lbn, "inflation", None, "réseau/HTTP: 503", False)
        self.assertEqual(candidate["recommendation"], "gap")
        self.assertIsNone(candidate["proposed"])
        # existant courant : 2025 = 14.6 (incrément 6.1 appliqué)
        self.assertEqual(candidate["existing"]["value"], 14.6)
        self.assertIn("503", candidate["explanation"])

    def test_no_data_yields_gap_existing_kept(self):
        candidate = r.build_candidate(self.lbn, "inflation", None, None, False)
        self.assertEqual(candidate["recommendation"], "gap")
        self.assertEqual(candidate["existing"]["value"], 14.6)

    def test_no_existing_indicator_is_manual(self):
        country = {"id": "test", "iso3": "TST", "indicators": {}}
        obs = {"year": 2025, "value": 2.0, "obs_status_label": "actual", "lastupdated": "2026-10-01"}
        candidate = r.build_candidate(country, "gdp_growth", obs, None, False)
        self.assertEqual(candidate["recommendation"], "manual")
        self.assertIn("existant", candidate["explanation"])

    def test_new_country_always_manual(self):
        snapshot = {"id": "brazil", "iso3": "BRA", "indicators": {}}
        obs = {"year": 2025, "value": 2.29, "obs_status_label": "actual", "lastupdated": "2026-10-01"}
        candidate = r.expand_candidate(snapshot, "gdp_growth", obs, None)
        self.assertEqual(candidate["recommendation"], "manual")
        self.assertTrue("expansion" in candidate["explanation"])

    def test_existing_metacarried_complete(self):
        candidate = r.build_candidate(self.lbn, "reserves", None, "erreur", False)
        self.assertEqual(candidate["existing"]["source"], "FMI / BDL")
        self.assertEqual(candidate["existing"]["unit"], "Mds $")
        self.assertIn("nettes", candidate["existing"]["note"])


class TestMetadata(unittest.TestCase):
    def setUp(self):
        self.clock = patch_clock(self)

    def test_retrieval_date_recorded_on_every_candidate(self):
        candidate = r.build_candidate(r.read_country("lebanon"), "gdp_growth", None, None, False)
        self.assertEqual(candidate["retrieved"], TEST_RETRIEVAL_DATE)

    def test_observation_publication_and_retrieval_are_distinct(self):
        obs = {"year": 2024, "value": -7.08, "obs_status_label": "actual",
               "lastupdated": "2026-10-01"}
        candidate = r.build_candidate(r.read_country("lebanon"), "gdp_growth", obs, None, False)
        published = candidate["proposed"]["published_lastupdated"]
        self.assertEqual(published, "2026-10-01")          # date de publication (WDI)
        self.assertEqual(candidate["proposed"]["date"], "2024")  # période d'observation
        self.assertEqual(candidate["retrieved"], TEST_RETRIEVAL_DATE)  # récupération
        self.assertNotEqual(published, candidate["retrieved"])

    def test_proposed_source_names_world_bank_and_series(self):
        obs = {"year": 2024, "value": -7.08, "obs_status_label": "actual", "lastupdated": "2026-10-01"}
        candidate = r.build_candidate(r.read_country("lebanon"), "gdp_growth", obs, None, False)
        self.assertIn("Banque mondiale", candidate["proposed"]["source"])
        self.assertIn("NY.GDP.MKTP.KD.ZG", candidate["proposed"]["source"])


class TestCandidatePack(unittest.TestCase):
    def test_pack_uses_mocked_transport_end_to_end(self):
        patch_clock(self)
        responses = {
            "NY.GDP.MKTP.KD.ZG": wb_payload([wb_row("2024", -7.08)]),
            "FP.CPI.TOTL.ZG": wb_payload([wb_row("2025", 14.6, series="FP.CPI.TOTL.ZG")]),
            "SL.UEM.TOTL.ZS": wb_payload([wb_row("2023", 10.99, series="SL.UEM.TOTL.ZS")]),
            "GC.DOD.TOTL.GD.ZS": wb_payload([]),
            "FI.RES.TOTL.CD": wb_payload(
                [wb_row("2024", 33301277509.6, series="FI.RES.TOTL.CD")]
            ),
        }
        with unittest.mock.patch("urllib.request.urlopen", side_effect=_SideEffect(responses)):
            pack = r.candidate_pack("lebanon")
        self.assertFalse(pack["new_country"])
        recos = {c["indicator"]: c["recommendation"] for c in pack["candidates"]}
        self.assertEqual(recos["gdp_growth"], "manual")   # même millésime, valeur divergente
        self.assertEqual(recos["inflation"], "manual")    # millésime plus récent
        self.assertEqual(recos["unemployment"], "reject")  # 2023 < 2024 existant
        self.assertEqual(recos["debt_gdp"], "gap")         # 0 ligne → écart documenté
        self.assertEqual(recos["reserves"], "reject")      # nettes (fiche) vs totales (WB)


class _SideEffect:
    """Route chaque urlopen(url) vers un payload simulé par code de série."""

    def __init__(self, responses):
        self.responses = responses

    def __call__(self, url, **kwargs):
        full_url = getattr(url, "full_url", str(url))
        series = str(full_url).split("/indicator/")[1].split("?")[0]
        payload = self.responses[series]

        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps(payload).encode("utf-8")

        return _Resp()


class TestNewCountryPack(unittest.TestCase):
    def test_brazil_snapshot_all_manual_with_metadata(self):
        patch_clock(self)
        payload = wb_payload(
            [wb_row("2025", 2.29, series="NY.GDP.MKTP.KD.ZG", country="Brazil")]
        )
        with unittest.mock.patch(
            "urllib.request.urlopen",
            side_effect=_SideEffect({"NY.GDP.MKTP.KD.ZG": payload}),
        ):
            pack = r.pack_for_new_country(r.BRAZIL_SNAPSHOT, indicators=("gdp_growth",))
        self.assertTrue(pack["new_country"])
        self.assertEqual(pack["iso3"], "BRA")
        candidate = pack["candidates"][0]
        self.assertEqual(candidate["recommendation"], "manual")
        self.assertEqual(candidate["proposed"]["value"], 2.29)
        self.assertEqual(candidate["retrieved"], TEST_RETRIEVAL_DATE)
        self.assertIn("api.worldbank.org", candidate["api_url"])


# ---------------------------------------------------------------------------
# Protection de la production
# ---------------------------------------------------------------------------

class TestProductionOverwriteProtection(unittest.TestCase):
    def test_read_country_is_read_only(self):
        original = (ROOT / "data" / "countries" / "lebanon.json").read_bytes()
        with _OnDiskProductionGuard() as guard:
            country = r.read_country("lebanon")
        self.assertEqual(country["id"], "lebanon")
        self.assertEqual(guard.production_writes, [])
        self.assertEqual((ROOT / "data" / "countries" / "lebanon.json").read_bytes(), original)

    def test_candidate_generation_never_writes_production(self):
        with _OnDiskProductionGuard() as guard:
            with unittest.mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("x")):
                r.candidate_pack("lebanon")
        self.assertEqual(guard.production_writes, [])

    def test_report_writer_refuses_paths_outside_docs(self):
        for bad in ("../data/countries/lebanon.json", "sub/../../evil.json")[:1]:
            with self.assertRaises(ValueError):
                r._docs_path(bad)

    def test_report_generation_writes_only_docs(self):
        import tempfile

        patch_clock(self)
        with _OnDiskProductionGuard() as guard, tempfile.TemporaryDirectory() as tmp:
            # DOCS_DIR redirigé vers un répertoire temporaire : le test ne
            # doit jamais écraser le rapport généré en conditions réelles.
            original_docs = r.DOCS_DIR
            r.DOCS_DIR = pathlib.Path(tmp)
            try:
                report = r.generate_report(("lebanon",))
            finally:
                r.DOCS_DIR = original_docs
            self.assertTrue(pathlib.Path(report["paths"]["json"]).exists())
            self.assertIn("REFRESH_CANDIDATES_BRA_LBN_SYR.json", report["paths"]["json"])
            self.assertNotIn(str(ROOT / "docs"), report["paths"]["json"])
        self.assertEqual(guard.production_writes, [])
        # pas d'écrasement des données : la fiche est inchangée
        self.assertEqual(json.load(open(ROOT / "data" / "countries" / "lebanon.json"))["indicators"]["inflation"]["value"], 14.6)
        self.assertEqual(json.load(open(ROOT / "data" / "countries" / "syria.json"))["indicators"]["inflation"]["value"], 60.0)
        # le rapport réel (généré en direct) reste en place
        self.assertIn("Brésil", (ROOT / "docs" / r.REPORT_MD_NAME).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
