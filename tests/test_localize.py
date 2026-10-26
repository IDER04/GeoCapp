"""Tests de la couche de localisation des données (overlays EN).

Garanties :
- complétude des overlays vs données source (pays, événements, meta) ;
- identité de tout ce qui n'est pas affichable (numériques, IDs, clés,
  indice de réponse du quiz, énumérations) entre donnée FR et donnée EN ;
- repli FR clé à clé si une traduction est absente ou vide ;
- résultats de scoring identiques avant et après localisation ;
- hygiène EN : pas d'accents typiquement français dans les textes traduits.
"""

import copy
import re
import unittest

from geocapital import data, i18n, scoring

COUNTRY_IDS = [c["id"] for c in data.countries()]
EVENT_IDS = [e["id"] for e in data.load_events()]
ID_FIELDS = ("id", "iso3", "flag", "group_key")
# Champs affichés sortis volontairement du périmètre de traduction :
# noms d'instruments en anglais (S&P 500, CAC 40, JSE All Share…), agences
# et valeurs de notation (A+, NR) identiques par nature dans les deux
# langues, codes monétaires (USD…).
UNTRANSLATED_FIELDS = {
    "indicators.rating.agency",
    "indicators.rating.value",
    "indicators.equity_index.name",  # noms d'indices strictement identiques
}
ACCENT = re.compile(r"[àâçéèêëîïôùûüœ]", re.IGNORECASE)


def set_lang(lang: str) -> None:
    """Force la langue en mode « hors Streamlit » (session_state direct)."""
    i18n.st.session_state["lang"] = lang


class TestOverlayCompleteness(unittest.TestCase):
    """Chaque overlay EN couvre tous les champs narratifs de la source FR."""

    def test_one_overlay_per_country(self):
        for cid in COUNTRY_IDS:
            self.assertTrue(i18n._overlay(f"{cid}.json"), f"overlay manquant: {cid}")

    def test_country_overlay_covers_all_narrative_paths(self):
        for country in data.countries():
            overlay = i18n._overlay(f"{country['id']}.json")
            for path, _value in narrative_paths(country):
                if path in UNTRANSLATED_FIELDS:
                    continue
                translated = dig(overlay, path.split("."))
                self.assertIsNotNone(translated, f"{country['id']}: {path} absent de l'overlay EN")
                self.assertTrue(translated.strip(), f"{country['id']}: {path} traduction vide")

    def test_events_overlay_covers_all_events(self):
        overlay = i18n._overlay("events.json")
        for eid in EVENT_IDS:
            self.assertIn(eid, overlay, f"événement manquant dans l'overlay EN: {eid}")

    def test_meta_overlay_covers_sources_and_methodology(self):
        meta = data.load_data()
        overlay = i18n._overlay("meta.json")
        self.assertEqual(len(overlay.get("sources", [])), len(meta.get("sources", [])))
        for key in ("score", "ke", "missing", "disclaimer"):
            self.assertIn(key, overlay.get("methodology", {}))
        for key in ("risk_free_source", "erp_source"):
            self.assertIn(key, overlay.get("financial_params", {}))
        for key in ("tagline", "last_update"):
            self.assertIn(key, overlay.get("app", {}))


class TestLocalizedIdentity(unittest.TestCase):
    """La traduction ne touche ni les valeurs numériques ni les identifiants."""

    def setUp(self):
        set_lang("en")
        self.addCleanup(set_lang, "fr")

    def test_identity_fields_unchanged(self):
        for country in data.countries():
            loc = i18n.localize_country(copy.deepcopy(country))
            for field in ID_FIELDS:
                self.assertEqual(country[field], loc[field], f"{country['id']}.{field}")
            self.assertTrue(loc.get("name"), f"{country['id']}: nom vide")
        # Au moins une fiche doit voir son nom changer (sinon l'overlay est
        # ignoré en EN), hors les noms FR déjà anglais (France, Japon).
        translatable = [c for c in data.countries() if c["name"] not in {"France", "Japon"}]
        changed = sum(1 for c in translatable if i18n.localize_country(copy.deepcopy(c))["name"] != c["name"])
        self.assertEqual(changed, len(translatable))

    def test_quiz_answer_index_unchanged(self):
        for country in data.countries():
            loc = i18n.localize_country(copy.deepcopy(country))
            self.assertEqual(country["quiz"]["answer"], loc["quiz"]["answer"], country["id"])
            self.assertEqual(len(country["quiz"]["options"]), len(loc["quiz"]["options"]))

    def test_numeric_subtree_identical(self):
        """Sous-arbre numérique des indicateurs : strictement identique."""
        for country in data.countries():
            src = country.get("indicators", {})
            loc = i18n.localize_country(copy.deepcopy(country)).get("indicators", {})
            self.assertEqual(set(src.keys()), set(loc.keys()), country["id"])
            for key, meta in src.items():
                for path, value in walk_numeric(meta):
                    self.assertEqual(
                        dig_value(loc.get(key, {}), path),
                        value,
                        f"{country['id']}.indicators.{key}." + ".".join(map(str, path)),
                    )

    def test_event_id_and_structure_unchanged(self):
        for event in data.load_events():
            loc = i18n.localize_event(copy.deepcopy(event))
            self.assertEqual(event["id"], loc["id"], event["id"])
            self.assertEqual(event.get("country"), loc.get("country"), event["id"])
            self.assertEqual(len(event.get("chain", [])), len(loc.get("chain", [])), event["id"])
            self.assertEqual(len(event.get("winners", [])), len(loc.get("winners", [])), event["id"])
            self.assertEqual(len(event.get("losers", [])), len(loc.get("losers", [])), event["id"])
            self.assertEqual(len(event.get("concepts", [])), len(loc.get("concepts", [])), event["id"])

    def test_scoring_results_identical(self):
        """Le score ne dépend que des nombres : identique avant/après traduction."""
        set_lang("fr")
        fr_scores = [scoring.overall_score(c, "Équilibré")["score"] for c in data.countries()]
        fr_ke = [scoring.required_return(c)["ke"] for c in data.countries()]
        set_lang("en")
        en_countries = [i18n.localize_country(c) for c in data.countries()]
        en_scores = [scoring.overall_score(c, "Équilibré")["score"] for c in en_countries]
        en_ke = [scoring.required_return(c)["ke"] for c in en_countries]
        self.assertEqual(fr_scores, en_scores)
        self.assertEqual(fr_ke, en_ke)

    def test_french_mode_returns_source_object(self):
        set_lang("fr")
        country = data.countries()[0]
        self.assertIs(country, i18n.localize_country(country))
        meta = data.load_data()
        self.assertIs(meta, i18n.localize_meta(meta))


class TestFrenchFallback(unittest.TestCase):
    """Une traduction absente ou vide retombe sur la valeur FR, jamais un vide."""

    def setUp(self):
        set_lang("en")
        self.addCleanup(set_lang, "fr")

    def test_empty_overlay_value_falls_back_to_french(self):
        country = copy.deepcopy(data.countries()[0])
        name = f"{country['id']}.json"
        i18n._OVERLAYS[name] = {**i18n._overlay(name), "headline": ""}
        try:
            self.assertEqual(i18n.localize_country(country)["headline"], country["headline"])
        finally:
            i18n._OVERLAYS.pop(name, None)

    def test_localized_output_never_empty(self):
        for country in data.countries():
            loc = i18n.localize_country(copy.deepcopy(country))
            for path, _v in narrative_paths(country):
                if path in UNTRANSLATED_FIELDS:
                    continue
                translated = dig(loc, path.split("."))
                self.assertTrue(translated and translated.strip(), f"{country['id']}.{path}")


class TestEnglishHygiene(unittest.TestCase):
    """Aucun texte traduit ne garde un caractère accentué typiquement FR."""

    def setUp(self):
        set_lang("en")
        self.addCleanup(set_lang, "fr")

    def test_no_accented_french_in_country_overlays(self):
        for cid in COUNTRY_IDS:
            for path, value in flatten(i18n._overlay(f"{cid}.json")):
                self.assertIsNone(ACCENT.search(value), f"{cid}: '{value}' ({path})")

    def test_no_accented_french_in_events_overlay(self):
        for path, value in flatten(i18n._overlay("events.json")):
            self.assertIsNone(ACCENT.search(value), f"events: '{value}' ({path})")

    def test_no_accented_french_in_meta_overlay(self):
        for path, value in flatten(i18n._overlay("meta.json")):
            self.assertIsNone(ACCENT.search(value), f"meta: '{value}' ({path})")


# --- utilitaires locaux (scoring.py et data.py ne sont jamais touchés) ---


def walk_numeric(obj, path=()):
    """Feuilles (chemin, valeur) non textuelles d'une donnée indicateur."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_numeric(v, (*path, k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_numeric(v, (*path, i))
    elif not isinstance(obj, str):
        yield path, obj


def dig_value(obj, path):
    for key in path:
        if isinstance(key, str) and key.isdigit():
            key = int(key)
        if isinstance(obj, dict) and key in obj:
            obj = obj[key]
        elif isinstance(obj, list) and isinstance(key, int) and key < len(obj):
            obj = obj[key]
        else:
            return None
    return obj


def dig(obj, path):
    out = dig_value(obj, path)
    return out if isinstance(out, str) else None


def narrative_paths(country: dict) -> list[tuple[str, str]]:
    """Chemins + valeurs des feuilles textuelles affichables d'une fiche."""
    out: list[tuple[str, str]] = []
    for key in ("name", "official_name", "region", "group", "headline", "summary"):
        value = country.get(key)
        if isinstance(value, str) and re.search(r"[A-Za-zÀ-ÿ]{3,}", value):
            out.append((key, value))
    for index, item in enumerate(country.get("history", [])):
        out.append((f"history.{index}.title", item["title"]))
        out.append((f"history.{index}.text", item["text"]))
    for key, value in country.get("institutions", {}).items():
        out.append((f"institutions.{key}", value))
    rel = country.get("relations", {})
    for section in ("allies", "rivals", "dependencies"):
        for index, item in enumerate(rel.get(section, [])):
            out.append((f"relations.{section}.{index}.name", item["name"]))
            out.append((f"relations.{section}.{index}.note", item["note"]))
    for ikey, meta in country.get("indicators", {}).items():
        for field in ("note", "date", "name", "source"):
            value = meta.get(field)
            if isinstance(value, str) and re.search(r"[A-Za-zÀ-ÿ]{3,}", value):
                out.append((f"indicators.{ikey}.{field}", value))
    for section in ("strengths", "risks", "opportunities"):
        for index, item in enumerate(country.get(section, [])):
            out.append((f"{section}.{index}", item))
    quiz = country.get("quiz", {})
    if quiz:
        out.append(("quiz.question", quiz["question"]))
        for index, option in enumerate(quiz["options"]):
            out.append((f"quiz.options.{index}", option))
        out.append(("quiz.explanation", quiz["explanation"]))
    return out


def flatten(obj, prefix=""):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.extend(flatten(v, f"{prefix}.{k}" if prefix else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(flatten(v, f"{prefix}[{i}]"))
    elif isinstance(obj, str):
        out.append((prefix, obj))
    return out


if __name__ == "__main__":
    unittest.main()
