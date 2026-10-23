"""Integrity tests for the survey content (content/*.json) and what is generated from it."""
import csv
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import minna_stats as ms  # noqa: E402
import minna_text as mt  # noqa: E402
import survey_data as sd  # noqa: E402
import survey_forms as sf  # noqa: E402
import survey_synth as ss  # noqa: E402

META, QUESTIONS = sd.load_content()
QMAP = {q["id"]: q for q in QUESTIONS}
ARABIC = re.compile(r"[؀-ۿ]")
LETTER = re.compile(r"[A-Za-z؀-ۿ]")
SEPARATORS = re.compile(r"[,;|\n،؛]")
REGISTER_IDS = {f"A-{i:02d}" for i in range(1, 22)}   # docs/ASSUMPTION_REGISTER.md, A-01..A-21
LANGS = ("en", "fr", "ar")


class Structure(unittest.TestCase):
    def test_ids_are_unique_and_the_codebook_builds_without_collisions(self):
        ids = [q["id"] for q in QUESTIONS]
        self.assertEqual(len(ids), len(set(ids)))
        mt.Codebook(QUESTIONS)   # raises on any collision across the three languages

    def test_every_text_exists_in_all_three_languages(self):
        for q in QUESTIONS:
            for lang in LANGS:
                self.assertTrue(q["text"].get(lang, "").strip(), (q["id"], lang))
            for o in q.get("options", []):
                for lang in LANGS:
                    self.assertTrue(o.get(lang, "").strip(), (q["id"], o["code"], lang))
        for key in ("title", "consent", "concept_card", "closing"):
            for lang in LANGS:
                self.assertTrue(META[key][lang].strip(), (key, lang))
        for sec in {q["section"] for q in QUESTIONS}:
            for lang in LANGS:
                self.assertTrue(META["sections"][sec][lang].strip(), (sec, lang))

    def test_languages_are_not_swapped(self):
        def texts(q):
            yield "text", q["text"]
            for o in q.get("options", []):
                yield o["code"], o
        for q in QUESTIONS:
            for what, t in texts(q):
                for lang in ("en", "fr"):
                    self.assertFalse(ARABIC.search(t[lang]), (q["id"], what, lang, t[lang]))
                if LETTER.search(t["ar"]):
                    self.assertTrue(ARABIC.search(t["ar"]), (q["id"], what, t["ar"]))
        for key in ("consent", "concept_card", "closing"):
            self.assertFalse(ARABIC.search(META[key]["en"]) or ARABIC.search(META[key]["fr"]), key)
            self.assertTrue(ARABIC.search(META[key]["ar"]), key)

    def test_option_codes_are_unique_ascii_identifiers(self):
        for q in QUESTIONS:
            codes = [o["code"] for o in q.get("options", [])]
            self.assertEqual(len(codes), len(set(codes)), q["id"])
            for c in codes:
                self.assertRegex(c, r"^[A-Za-z0-9_]+$", (q["id"], c))
            if q["type"] in ("single", "multi"):
                self.assertGreaterEqual(len(codes), 2, q["id"])

    def test_multi_select_labels_contain_no_separator(self):
        # The loader splits a multi-select cell on , ; | newline and the Arabic comma and semicolon.
        for q in QUESTIONS:
            if q["type"] == "multi":
                for o in q["options"]:
                    for lang in LANGS:
                        self.assertIsNone(SEPARATORS.search(o[lang]), (q["id"], o["code"], o[lang]))

    def test_skip_logic_points_backwards_at_real_codes(self):
        seen = set()
        for q in QUESTIONS:
            cond = q.get("show_if")
            if cond:
                self.assertIn(cond["q"], seen, f"{q['id']} depends on a question defined later or missing")
                parent = QMAP[cond["q"]]
                self.assertNotEqual(parent["type"], "hidden")
                valid = {o["code"] for o in parent["options"]}
                self.assertTrue(set(cond["in"]) <= valid, (q["id"], cond))
            seen.add(q["id"])

    def test_everything_asked_sits_behind_the_consent_and_the_adult_screen(self):
        # Walk every question's show_if chain to its root. The root must be S1 (consent) and the
        # chain must pass through S1 = yes and, for every question after S2, through S2 = yes.
        for q in QUESTIONS:
            if q["type"] == "hidden" or q["id"] == "S1":
                continue
            chain, cur = [], q
            while cur.get("show_if"):
                cond = cur["show_if"]
                chain.append((cond["q"], tuple(cond["in"])))
                cur = QMAP[cond["q"]]
            self.assertEqual(cur["id"], "S1", f"{q['id']} can be reached without answering the consent question")
            self.assertIn(("S1", ("yes",)), chain, q["id"])
            if q["id"] != "S2":
                self.assertIn(("S2", ("yes",)), chain, f"{q['id']} can be reached without the 18+ screen")

    def test_types_and_required_fields(self):
        for q in QUESTIONS:
            self.assertIn(q["type"], sf.TYPES, q["id"])
            self.assertIsInstance(q["required"], bool)
            self.assertTrue(q["purpose"].strip(), q["id"])
            self.assertTrue(set(q["assumption"]) <= REGISTER_IDS, (q["id"], q["assumption"]))
            if q["type"] in ("single", "multi"):
                self.assertTrue(q["options"])
            if q.get("max_select"):
                self.assertEqual(q["type"], "multi")
            if q.get("range"):
                self.assertIn(q["type"], ("number", "money"))

    def test_the_price_placeholder_lives_only_in_the_price_question(self):
        for q in QUESTIONS:
            for lang in LANGS:
                has = "{PRICE}" in q["text"][lang]
                self.assertEqual(has, q["id"] == "W2", (q["id"], lang))

    def test_the_survey_has_no_free_text_question_and_only_known_numeric_inputs(self):
        # Structural guard against collecting identifiers: respondents can only pick options or
        # type one of these numbers. Free text enters only through 'other' options.
        self.assertEqual([q["id"] for q in QUESTIONS if q["type"] == "text"], [])
        numeric = {q["id"] for q in QUESTIONS if q["type"] in ("number", "money") or q.get("numeric")}
        self.assertEqual(numeric, {"O5a", "O5b", "W1", "price_cell"})
        hidden = {q["id"] for q in QUESTIONS if q["type"] == "hidden"}
        self.assertEqual(hidden, {"ref", "price_cell"})

    def test_location_is_asked_as_a_locality_type_not_a_place(self):
        # Exact wilaya would make small cells re-identifiable; the register lists it as not asked.
        self.assertEqual({o["code"] for o in QMAP["P2"]["options"]}, {"big_city", "town", "rural", "pnts"})


class Estimates(unittest.TestCase):
    def test_every_estimate_points_at_real_questions_and_codes(self):
        ids = [e["id"] for e in META["estimates"]]
        self.assertEqual(len(ids), len(set(ids)))
        for e in META["estimates"]:
            q = QMAP[e["q"]]
            valid = {o["code"] for o in q["options"]}
            self.assertTrue(set(e["codes"]) <= valid, (e["id"], e["codes"]))
            self.assertTrue(set(e.get("exclude", [])) <= valid, (e["id"], e.get("exclude")))
            self.assertTrue(set(e["assumption"]) <= REGISTER_IDS, e["id"])
            self.assertIn(q["type"], ("single", "multi"))
            self.assertTrue(e["label"].strip())

    def test_the_synthetic_truth_covers_every_estimate_exactly(self):
        truth = ss.truth()["estimates"]
        self.assertEqual({e["id"] for e in META["estimates"]}, set(truth))
        for k, v in truth.items():
            self.assertTrue(0 < v < 1, (k, v))


class DesignNumbers(unittest.TestCase):
    def test_the_stated_sample_sizes_are_the_computed_ones(self):
        d = META["design"]
        self.assertEqual(d["n_min_textbook"], ms.normal_n_for_margin(d["margin_target"]))
        self.assertGreater(ms.worst_case_margin(d["n_min_exact"] - 1), d["margin_target"])
        self.assertLessEqual(ms.worst_case_margin(d["n_min_exact"]), d["margin_target"])
        self.assertGreater(ms.worst_case_margin(d["n_min_textbook"]), d["margin_target"])

    def test_parameters_are_sane(self):
        d = META["design"]
        self.assertEqual(META["languages"], list(LANGS))
        self.assertTrue(0.5 < d["conf"] < 1 and 0 < d["margin_target"] < d["wide_margin"] < 0.5)
        cells = d["price_cells_dzd"]
        self.assertEqual(cells, sorted(set(cells)))
        self.assertGreaterEqual(len(cells), 2)
        self.assertTrue(all(c > 0 for c in cells))
        self.assertTrue(0 < d["android_lower_bound"] < 1)
        self.assertTrue(all(0 < r < 1 for r in d["icc_sensitivity"]))
        self.assertIn("PLACEHOLDER", d["price_cells_status"])
        self.assertIn("PLACEHOLDER", d["android_status"])


class Rendering(unittest.TestCase):
    def test_placeholders_are_present_in_every_language_so_none_can_be_forgotten(self):
        for key, want in (("consent", 3), ("closing", 1)):
            for lang in LANGS:
                self.assertEqual(len(sf.PLACEHOLDER.findall(META[key][lang])), want, (key, lang))
        self.assertTrue(sf.placeholders(META))

    def test_every_question_and_option_appears_in_each_printed_survey(self):
        for lang in LANGS:
            text = sf.render_survey(META, QUESTIONS, lang)
            self.assertIn("DRAFT, do not field", text)
            for q in QUESTIONS:
                self.assertIn(f"**{q['id']}.**", text)
                for o in q.get("options", []):
                    self.assertIn(o[lang], text, (lang, q["id"], o["code"]))
            self.assertEqual(text.startswith('<div dir="rtl">'), lang == "ar")

    def test_optional_questions_are_marked_optional_and_required_ones_are_not(self):
        text = sf.render_survey(META, QUESTIONS, "en")
        for q in QUESTIONS:
            m = re.search(rf"\*\*{re.escape(q['id'])}\.\*\* [^\n]*\n\n\*([^\n]*)\*\n", text)
            self.assertIsNotNone(m, q["id"])
            self.assertEqual(", optional" in m.group(1), not (q["required"] or q["type"] == "hidden"), q["id"])
        self.assertTrue(any(not q["required"] and q["type"] != "hidden" for q in QUESTIONS))

    def test_translations_carry_the_review_warning_and_english_does_not(self):
        for lang in LANGS:
            text = sf.render_survey(META, QUESTIONS, lang)
            self.assertEqual("needs native-speaker review and a pretest" in text, lang != "en", lang)
            self.assertIn("DRAFT, do not field yet", text)
            self.assertIn("Fill in:", text)

    def test_the_closing_text_placeholders_are_listed_too(self):
        found = sf.placeholders(META)
        for token in ("[INTERVIEW LINK]", "[LIEN ENTRETIEN]", "[رابط المقابلة]", "[CONTACT]", "[WHERE]"):
            self.assertIn(token, found)

    def test_codebook_csv_has_one_row_per_option_or_open_question(self):
        expected = sum(max(1, len(q.get("options", []))) for q in QUESTIONS)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "codebook.csv")
            self.assertEqual(sf.write_codebook(META, QUESTIONS, path), expected)
            with open(path, newline="", encoding="utf-8-sig") as fh:
                rows = list(csv.DictReader(fh))
        self.assertEqual(len(rows), expected)
        self.assertEqual({r["question_id"] for r in rows}, set(QMAP))
        self.assertTrue(all(r["label_ar"] and r["label_fr"] and r["label_en"] for r in rows))


if __name__ == "__main__":
    unittest.main(verbosity=2)
