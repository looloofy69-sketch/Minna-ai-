"""The numbers printed in the interview guides must equal the computed ones."""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import minna_stats as ms  # noqa: E402
import survey_data as sd  # noqa: E402

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
META, _ = sd.load_content()


def read(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        return fh.read()


def table_rows(text, word, decimal):
    """{(k, n): (lower, upper)} parsed from rows like '| 7 of 14 | 26.4% | 73.6% |'."""
    pct = r"([\d.]+)%" if decimal == "." else r"([\d,]+) %"
    pattern = re.compile(rf"^\| (\d+) {word} (14|10) \| {pct} \| {pct} \|$", re.M)
    return {(int(k), int(n)): (lo.replace(",", "."), hi.replace(",", ".")) for k, n, lo, hi in pattern.findall(text)}


class GuideNumbers(unittest.TestCase):
    def check(self, text, word, decimal):
        rows = table_rows(text, word, decimal)
        self.assertEqual(len(rows), 15 + 11)
        for (k, n), (lo, hi) in rows.items():
            self.assertEqual(lo, f"{100 * ms.cp_lower_one_sided(k, n):.1f}", (k, n))
            self.assertEqual(hi, f"{100 * ms.cp_upper_one_sided(k, n):.1f}", (k, n))

    def test_english_tables_equal_the_computed_bounds(self):
        self.check(read("interview_guide_en.md"), "of", ".")

    def test_french_tables_equal_the_computed_bounds(self):
        self.check(read("interview_guide_fr.md"), "sur", ",")

    def test_prose_does_not_treat_discovery_interviews_as_prevalence(self):
        self.assertEqual(META["design"]["n_min_exact"], 106)
        en = read("interview_guide_en.md")
        fr = read("interview_guide_fr.md")
        self.assertIn("5** distinct channels", en)
        self.assertIn("5 canaux distincts", fr)
        self.assertIn("not valid prevalence estimates for this recruitment protocol", en)
        self.assertIn("pas des estimations de prévalence valides pour ce recrutement", fr)
        self.assertIn("not to estimate prevalence", en)
        self.assertIn("pas pour estimer leur prévalence", fr)
        for name, text in (("interview_guide_en.md", en), ("interview_guide_fr.md", fr)):
            for needle in ("106", "20", "14"):
                self.assertIn(needle, text, name)

    def test_both_guides_have_the_same_sections_and_placeholders(self):
        en, fr = read("interview_guide_en.md"), read("interview_guide_fr.md")
        heads = lambda t: re.findall(r"^## (\d+)\.", t, re.M)  # noqa: E731
        self.assertEqual(heads(en), heads(fr))
        self.assertEqual(heads(en), [str(i) for i in range(12)])
        placeholders = lambda t: sorted(set(re.findall(r"\[[A-ZÀ-Ý][A-ZÀ-Ý' /]+\]", t)))  # noqa: E731
        self.assertEqual(len(placeholders(en)), len(placeholders(fr)))
        self.assertGreaterEqual(len(placeholders(en)), 4)

    def test_the_guides_never_ask_for_identifiers(self):
        for name in ("interview_guide_en.md", "interview_guide_fr.md"):
            text = read(name).lower()
            self.assertTrue("not ask for your name" in text or "ne demanderai ni votre nom" in text, name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
