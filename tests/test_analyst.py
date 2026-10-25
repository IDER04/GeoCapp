"""Tests du module d'analyste : récupération, cadrage, troncature d'historique.

Aucun appel réseau : ai.chat est simulé dans les tests qui l'exercent.
"""

from __future__ import annotations

import json
import unittest
from unittest import mock

from geocapital import analyst, data, scoring


class TestRetrieval(unittest.TestCase):
    def test_ten_countries_available(self):
        countries = data.countries()
        self.assertEqual(len(countries), 10)

    def test_detect_country_by_name_and_alias(self):
        self.assertEqual(analyst.detect_country("Explique le verdict de la France."), "france")
        self.assertEqual(analyst.detect_country("Analyse les États-Unis."), "usa")
        self.assertEqual(analyst.detect_country("Parle-moi du Maroc."), "morocco")
        self.assertEqual(analyst.detect_country("La croissance chinoise"), "china")
        self.assertEqual(analyst.detect_country("Et l'Arabie saoudite ?"), "saudi")

    def test_detect_country_ignores_accents_and_case(self):
        self.assertEqual(analyst.detect_country("ETATS-UNIS"), "usa")
        self.assertEqual(analyst.detect_country("EMIRATS DU GOLFE"), "uae")

    def test_no_country_detected_returns_none(self):
        self.assertIsNone(analyst.detect_country("Quelle heure est-il ?"))

    def test_detect_event_by_title(self):
        events = data.load_events()
        event = events[0]
        self.assertEqual(analyst.detect_event(event["title"]), event["id"])

    def test_payload_country_grounds_and_marks_missing(self):
        country = data.country_by_id("usa")
        payload = analyst.payload_country(country)
        self.assertIn("score_geo_capital", payload)
        self.assertIn("informations_manquantes", payload)
        ke = payload["score_geo_capital"]["rendement_exige"]
        self.assertEqual(ke["risk_free"], scoring.RISK_FREE_RATE)
        # Les chiffres viennent des fonctions déterministes, pas de l'IA.
        self.assertEqual(
            ke["ke"],
            scoring.required_return(country)["ke"],
        )

    def test_payload_comparison_contains_only_selected(self):
        selected = [data.country_by_id("france"), data.country_by_id("japan")]
        payload = analyst.payload_comparison(selected)
        self.assertEqual(payload["pays_selectionnes"], ["France", "Japon"])
        self.assertIn("France", payload["indicateurs_comparables"]["Croissance du PIB"])

    def test_payload_event_separates_facts_from_consequences(self):
        event = data.load_events()[0]
        payload = analyst.payload_event(event, data.country_by_id(event["country"]))
        self.assertIn("faits_etablis", payload)
        self.assertIn("consequences_potentielles", payload)
        faits = payload["faits_etablis"]
        self.assertTrue(faits["source"] and faits["date"])

    def test_payload_capital_keeps_limitations_and_python_ke(self):
        country = data.country_by_id("saudi")
        payload = analyst.payload_capital(country)
        self.assertGreaterEqual(len(payload["limites_explicites_du_modele"]), 3)
        ke = payload["cout_du_capital"]
        self.assertEqual(ke["ke"], scoring.required_return(country)["ke"])
        self.assertEqual(payload["parametres_methode"]["beta"], scoring.BETA)

    def test_payload_portfolio_weights_sum_to_100(self):
        amounts = {"usa": 30000, "china": 20000, "france": 50000, "syria": 0}
        payload = analyst.payload_portfolio(amounts)
        total = sum(p["poids_pct"] for p in payload["positions"])
        self.assertAlmostEqual(total, 100.0, delta=0.2)
        names = [p["pays"] for p in payload["positions"]]
        self.assertIn("États-Unis", names)
        self.assertNotIn("Syrie", names)
        self.assertEqual(payload["montant_investi_eur"], 100000)


class TestMultilingual(unittest.TestCase):
    """Comportement multilingue : langue de la question (pas de l'interface)."""

    # 1. Question française → consigne de réponse en français
    def test_french_question_directs_french_answer(self):
        payload = analyst.payload_country(data.country_by_id("usa"))
        messages = analyst.build_messages(payload, "Explique le verdict de la France.")
        system = messages[0]["content"]
        self.assertIn("- Écris ta réponse en français clair", system)
        self.assertNotIn("clear English", system)
        # Les règles d'analyse financière restent intactes.
        self.assertIn("Pas de conseil financier personnalisé", system)
        self.assertIn("FAITS VALIDÉS", messages[-1]["content"])

    # 2. Question anglaise → consigne de réponse en anglais
    def test_english_question_directs_english_answer(self):
        payload = analyst.payload_country(data.country_by_id("usa"))
        messages = analyst.build_messages(payload, "What explains the France verdict?")
        system = messages[0]["content"]
        self.assertIn("- Write your answer in clear English", system)
        self.assertNotIn("français clair", system)
        # Les règles d'analyse financière restent intactes (données, sources,
        # données manquantes, registres fait/interprétation/hypothèse).
        for rule in ("FAITS VALIDÉS", "Hypothèse", "Interprétation", "informations_manquantes"):
            self.assertIn(rule, system)

    # 3. La question prime sur la langue d'interface : analyst.py ne lit
    #    jamais la langue session (aucune dépendance session_state/i18n).
    def test_question_language_independent_of_interface(self):
        import inspect

        source = inspect.getsource(analyst)
        self.assertNotIn("session_state", source)
        self.assertNotIn("geocapital.i18n", source)
        # Même question anglaise → consigne anglaise, quels que soient
        # l'appel, l'ordre ou l'état : detection dépend du texte seul.
        first = analyst.build_messages({}, "Why did rates drop?", history=[])
        second = analyst.build_messages({}, "Why did rates drop?", history=[])
        self.assertEqual(first[0]["content"], second[0]["content"])
        self.assertIn("clear English", first[0]["content"])

    # 4. Ambiguïté : langue dominante ou défaut français déterministe
    def test_mixed_question_uses_dominant_language(self):
        self.assertEqual(analyst.detect_question_language("Show me le CDS du Maroc."), "fr")
        self.assertEqual(
            analyst.detect_question_language("Explain the US versus China scores"),
            "en",
        )

    def test_ambiguous_or_empty_question_defaults_to_french(self):
        # Aucun indice exploitable → défaut de l'application.
        self.assertEqual(analyst.detect_question_language(""), "fr")
        self.assertEqual(analyst.detect_question_language(None), "fr")
        self.assertEqual(analyst.detect_question_language("Verdict France Chine Japon."), "fr")
        # Mélange réel avec accents français forts.
        self.assertEqual(analyst.detect_question_language("Résumé of USA"), "fr")

    # 5. Fallback déterministe anglais : sans prose explicative française
    def test_english_fallback_has_no_french_prose(self):
        # La Syrie a des données manquantes : ligne de divulgation attendue.
        payload = analyst.payload_country(data.country_by_id("syria"))
        text = analyst.editorial_answer(payload, question="What explains the Syria verdict?")
        self.assertIn("Editorial mode", text)
        self.assertIn("GeoCapital score:", text)
        self.assertIn("Data not available:", text)
        for fr_prose in ("Mode éditorial", "Rendement exigé calculé", "Données non disponibles"):
            self.assertNotIn(fr_prose, text)

    def test_english_fallback_portfolio_and_capital_prose(self):
        payload = analyst.payload_capital(data.country_by_id("saudi"))
        text = analyst.editorial_answer(payload, question="Explain the cost of capital?")
        self.assertIn("Required return:", text)
        self.assertIn("country risk premium", text)
        self.assertNotIn("Rendement exigé", text)

        amounts = {"usa": 30000, "china": 20000, "france": 50000}
        payload2 = analyst.payload_portfolio(amounts)
        text2 = analyst.editorial_answer(payload2, question="How is my portfolio doing?")
        self.assertIn("Portfolio: weighted required return", text2)
        self.assertIn("largest position:", text2)
        self.assertNotIn("Portefeuille", text2)

    # 6. Le fallback français reste correct (comportement historique)
    def test_french_fallback_unchanged(self):
        payload = analyst.payload_country(data.country_by_id("usa"))
        text = analyst.editorial_answer(payload)
        self.assertIn("Mode éditorial", text)
        self.assertIn("Score GeoCapital", text)
        self.assertIn("Rendement exigé calculé en Python", text)

    # 7. Les faits, sources, dates et la structure restent identiques :
    #    build_messages/editorial_answer ne mutent pas le payload, et le
    #    message utilisateur embarque le JSON complet des faits validés.
    def test_payload_not_mutated_and_fully_grounded(self):
        payload = analyst.payload_country(data.country_by_id("usa"))
        snapshot = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        analyst.build_messages(payload, "What explains the US verdict?")
        analyst.editorial_answer(payload, question="What explains the US verdict?")
        self.assertEqual(json.dumps(payload, ensure_ascii=False, sort_keys=True), snapshot)

        payload_with_date = analyst.payload_event(data.load_events()[0], data.country_by_id("usa"))
        snapshot2 = json.dumps(payload_with_date, ensure_ascii=False, sort_keys=True)
        analyst.build_messages(payload_with_date, "What changed after the Fed cut?")
        self.assertEqual(json.dumps(payload_with_date, ensure_ascii=False, sort_keys=True), snapshot2)

        # Sources et dates toujours présentes dans les faits validés.
        self.assertIn("Notation souveraine", payload["chiffres_clefs"])
        self.assertTrue(payload["chiffres_clefs"]["Notation souveraine"].get("date"))

    # 8. La troncature d'historique fonctionne dans les deux langues.
    def test_history_truncation_language_agnostic(self):
        payload = analyst.payload_overview()
        flooded = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"turn {i}"}
            for i in range(40)
        ]
        messages = analyst.build_messages(payload, "Why did the Fed cut?", history=flooded)
        kept = [m for m in messages if m["role"] != "system"]
        self.assertEqual(len(kept), analyst.MAX_EXCHANGES * 2 + 1)


class TestViewFallbackLanguage(unittest.TestCase):
    """Régression : la vue transmet la question à la réponse éditoriale."""

    def test_handle_question_passes_prompt_to_editorial_answer(self):
        from streamlit.testing.v1 import AppTest

        script = '''
import json, streamlit as st
from geocapital import ai, analyst
from views.analyst_page import _handle_question, _init_state, PAGE_KEY

captured = {}
original = analyst.editorial_answer
def spy(payload, question=None):
    captured["payload"] = payload
    captured["question"] = question
    return original(payload, question)
analyst.editorial_answer = spy
ai.is_available = lambda: False
_init_state()
_handle_question("What explains the Syria verdict?")
st.code(json.dumps(captured, ensure_ascii=False))
'''
        at = AppTest.from_string(script)
        at.run()
        captured = json.loads([c.value for c in at.code][0])
        self.assertEqual(captured["question"], "What explains the Syria verdict?")
        # La langue de la question pilote la rédaction (USA par défaut du sélecteur).
        self.assertIn("identite", captured["payload"])

    def test_english_question_yields_english_fallback_through_view(self):
        from streamlit.testing.v1 import AppTest

        script = '''
import streamlit as st
from geocapital import ai
from views.analyst_page import _handle_question, _init_state, PAGE_KEY
ai.is_available = lambda: False
st.session_state["country_id"] = "syria"  # pays par défaut du sélecteur
_init_state()
_handle_question("What explains the Syria verdict?")
st.code(st.session_state[PAGE_KEY][-1]["content"])
'''
        at = AppTest.from_string(script)
        at.run()
        text = [c.value for c in at.code][0]
        self.assertIn("Editorial mode", text)
        self.assertIn("Data not available:", text)
        self.assertNotIn("Mode éditorial", text)

    def test_french_question_yields_french_fallback_through_view(self):
        from streamlit.testing.v1 import AppTest

        script = '''
import streamlit as st
from geocapital import ai
from views.analyst_page import _handle_question, _init_state, PAGE_KEY
ai.is_available = lambda: False
st.session_state["country_id"] = "syria"  # pays par défaut du sélecteur
_init_state()
_handle_question("Explique le verdict de la Syrie ?")
st.code(st.session_state[PAGE_KEY][-1]["content"])
'''
        at = AppTest.from_string(script)
        at.run()
        text = [c.value for c in at.code][0]
        self.assertIn("Mode éditorial", text)
        self.assertIn("Données non disponibles", text)
        self.assertNotIn("Editorial mode", text)


class TestMissingData(unittest.TestCase):
    def test_missing_indicator_reported_for_nr_country(self):
        fake = {
            "id": "x",
            "name": "Pays fictif",
            "indicators": {},
            "qualitative": {},
        }
        missing = analyst.missing_indicators(fake)
        labels = [item["label"] for item in missing]
        self.assertIn("Notation souveraine", labels)
        self.assertIn("CDS 5 ans", labels)

    def test_missing_indicators_vanish_when_present(self):
        country = data.country_by_id("usa")
        labels = [item["label"] for item in analyst.missing_indicators(country)]
        self.assertNotIn("Notation souveraine", labels)
        self.assertNotIn("CDS 5 ans", labels)

    def test_editorial_answer_names_missing_data(self):
        fake = {
            "id": "x",
            "name": "Pays fictif",
            "indicators": {},
            "qualitative": {},
        }
        payload = analyst.payload_country(fake)
        text = analyst.editorial_answer(payload)
        self.assertIn("Données non disponibles", text)


class TestPromptConstruction(unittest.TestCase):
    def test_system_rule_present_and_french(self):
        payload = analyst.payload_country(data.country_by_id("usa"))
        messages = analyst.build_messages(payload, "Question ?")
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("analyste IA de GeoCapital", messages[0]["content"])
        self.assertIn("FAITS VALIDÉS", messages[-1]["content"])
        self.assertIn("QUESTION DE L'UTILISATEUR", messages[-1]["content"])

    def test_history_truncated_to_six_exchanges(self):
        payload = analyst.payload_overview()
        flooded = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"tour {i}"}
            for i in range(40)
        ]
        messages = analyst.build_messages(payload, "Question ?", history=flooded)
        kept = [m for m in messages if m["role"] != "system"]
        self.assertEqual(len(kept), analyst.MAX_EXCHANGES * 2 + 1)
        self.assertEqual(kept[-1]["role"], "user")
        self.assertNotIn("tour 0", json.dumps(messages))

    def test_context_by_intent(self):
        payload = analyst.build_context("country", "Bonjour")
        self.assertIn("identite", payload)
        payload = analyst.build_context(
            "compare", "Bonjour", compare_ids=["usa", "china"]
        )
        self.assertEqual(len(payload["pays_selectionnes"]), 2)
        payload = analyst.build_context("portfolio", "", amounts={"usa": 50000})
        self.assertEqual(payload["metriques"]["top_country"], "États-Unis")
        payload = analyst.build_context("unknown-intent", "Rien de précis")
        self.assertIn("pays_disponibles", payload)


if __name__ == "__main__":
    unittest.main()
