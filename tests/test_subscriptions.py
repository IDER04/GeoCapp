"""Tests de la page Abonnements (prototype frontend, formules brouillon)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from geocapital import i18n, subscriptions as subs

ROOT = Path(__file__).resolve().parent.parent


class TestPlanData(unittest.TestCase):
    def test_free_plan_costs_nothing_in_both_cycles(self):
        for billing in subs.BILLING_CYCLES:
            self.assertEqual(subs.plan_price("free", billing)["total"], 0)

    def test_annual_applies_placeholder_discount(self):
        price = subs.plan_price("student", "annual")
        full = subs.PLAN_PRICES["student"] * 12
        self.assertAlmostEqual(price["total"], full * (1 - subs.ANNUAL_DISCOUNT), places=2)
        self.assertAlmostEqual(price["saving"], full - price["total"], places=2)
        self.assertLess(price["per_month"], subs.PLAN_PRICES["student"])

    def test_monthly_has_no_saving(self):
        self.assertEqual(subs.plan_price("pro", "monthly")["saving"], 0)

    def test_unknown_plan_or_cycle_rejected(self):
        with self.assertRaises(ValueError):
            subs.plan_price("gold", "monthly")
        with self.assertRaises(ValueError):
            subs.plan_price("pro", "weekly")

    def test_every_row_covers_every_plan_and_group(self):
        for key, group, row in subs.FEATURES:
            self.assertEqual(set(row), set(subs.PLANS), key)
            self.assertIn(group, subs.GROUPS, key)
        self.assertIn(subs.RECOMMENDED_PLAN, subs.PLANS)
        keys = {key for key, _g, _r in subs.FEATURES}
        self.assertTrue(set(subs.HIGHLIGHTS) <= keys)

    def test_is_differing(self):
        self.assertTrue(subs.is_differing({"free": True, "student": True, "pro": False}))
        self.assertFalse(subs.is_differing({"free": True, "student": True, "pro": True}))


class TestLabels(unittest.TestCase):
    def test_every_label_exists_in_both_languages(self):
        needed = {"nav.subscriptions", "sub.title", "sub.draft", "sub.cmp.draft"}
        for plan in subs.PLANS:
            needed |= {f"sub.plan.{plan}", f"sub.audience.{plan}", f"sub.tagline.{plan}", f"sub.cta.{plan}"}
        for key, group, row in subs.FEATURES:
            needed |= {f"sub.f.{key}", f"sub.group.{group}"}
            for value in row.values():
                if not isinstance(value, bool):
                    needed.add(f"sub.v.{value[0]}")
        for lang in i18n.LANGS:
            missing = needed - set(i18n.STRINGS[lang])
            self.assertFalse(missing, f"[{lang}] {sorted(missing)}")


class TestPage(unittest.TestCase):
    def _run(self, lang: str = "fr", **state):
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
        at.session_state["lang"] = lang
        at.session_state["nav"] = "subscriptions"
        for key, value in state.items():
            at.session_state[key] = value
        at.run()
        self.assertFalse(bool(at.exception), at.exception)
        return at

    def _text(self, at) -> str:
        return "\n".join(str(w.value) for w in at.markdown)

    def test_renders_in_both_languages_without_raw_keys(self):
        for lang in ("fr", "en"):
            at = self._run(lang)
            text = self._text(at)
            self.assertIn(i18n.STRINGS[lang]["sub.cmp.draft"], text)
            self.assertIsNone(re.search(r"\bsub\.[a-z_.]+", text), f"[{lang}] clé brute")
            nav = [o for w in at.radio if w.key == "nav" for o in w.options]
            self.assertTrue(any(i18n.STRINGS[lang]["nav.subscriptions"] in o for o in nav))

    def test_plan_buttons_select_and_clear(self):
        at = self._run()
        self.assertIsNone(at.session_state["sub_selected"])
        next(b for b in at.button if b.key == "sub_pick_student").click().run()
        self.assertEqual(at.session_state["sub_selected"], "student")
        self.assertIn("✓", [b.label for b in at.button if b.key == "sub_pick_student"][0])
        next(b for b in at.button if b.key == "sub_clear").click().run()
        self.assertIsNone(at.session_state["sub_selected"])

    def test_billing_toggle_changes_displayed_price(self):
        at = self._run()
        monthly = self._text(at)
        at.radio(key="sub_billing").set_value("annual").run()
        annual = self._text(at)
        self.assertNotEqual(monthly, annual)
        self.assertIn("facturés par an", annual)

    def _rows(self, at) -> set[str]:
        """Libellés des lignes de comparaison réellement rendues."""
        html = next(w.value for w in at.markdown if "gc-cmp" in str(w.value) and "<table" in str(w.value))
        return set(re.findall(r'<td class="gc-table-label">(.*?)</td>', html))

    def test_comparison_toggle_filters_rows(self):
        labels = i18n.STRINGS["fr"]
        shared = {labels[f"sub.f.{k}"] for k, _g, row in subs.FEATURES if not subs.is_differing(row)}
        differing = {labels[f"sub.f.{k}"] for k, _g, row in subs.FEATURES if subs.is_differing(row)}
        self.assertTrue(shared and differing)

        at = self._run()
        self.assertFalse(at.toggle(key="sub_diff_only").value)
        full = {r.replace("&#x27;", "'") for r in self._rows(at)}
        self.assertEqual(full, shared | differing)

        at.toggle(key="sub_diff_only").set_value(True).run()
        filtered = {r.replace("&#x27;", "'") for r in self._rows(at)}
        self.assertEqual(filtered, differing)
        self.assertFalse(filtered & shared)

        at.toggle(key="sub_diff_only").set_value(False).run()
        self.assertEqual({r.replace("&#x27;", "'") for r in self._rows(at)}, shared | differing)

    def test_faq_removed(self):
        for lang in ("fr", "en"):
            at = self._run(lang)
            self.assertEqual(len(at.expander), 0)
            self.assertNotIn("Questions fréquentes", self._text(at))
            self.assertNotIn("Frequently asked", self._text(at))
        self.assertFalse([k for k in i18n.STRINGS["fr"] if k.startswith("sub.faq")])

    def test_summary_follows_selected_plan(self):
        at = self._run()
        for plan in subs.PLANS:
            next(b for b in at.button if b.key == f"sub_pick_{plan}").click().run()
            text = self._text(at)
            self.assertIn(f'<div class="gc-sel-name">{i18n.STRINGS["fr"][f"sub.plan.{plan}"]}</div>', text)

    def test_card_styling_classes(self):
        at = self._run(sub_selected="student")
        html = "\n".join(str(w.value) for w in at.markdown)
        cards = re.findall(r'<div class="(gc-plan(?: [^"]*)?)">', html)
        self.assertEqual(len(cards), 3)
        free, student, pro = cards
        self.assertIn("gc-dark", pro)
        self.assertNotIn("gc-dark", student)
        self.assertTrue({"recommended", "selected"} <= set(student.split()))
        self.assertNotIn("selected", free)

    def test_continue_does_not_change_state_beyond_toast(self):
        at = self._run(sub_selected="pro")
        before = at.session_state["sub_selected"]
        next(b for b in at.button if b.key == "sub_continue").click().run()
        self.assertEqual(at.session_state["sub_selected"], before)
        self.assertFalse(bool(at.exception))


if __name__ == "__main__":
    unittest.main()
