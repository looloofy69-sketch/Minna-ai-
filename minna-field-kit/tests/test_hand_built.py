"""Hand-built respondents: small cases whose right answer can be worked out by hand.

The planted-truth tests (test_pipeline) show that the estimates come back right on realistic
data. These tests pin the individual rules: who counts in a denominator, what the audit and
the report must say, which branch of a decision aid fires. Each one exists because the
mutation check (scripts/mutate_kit.py) showed that breaking that rule left every earlier
test green.
"""
import contextlib
import csv
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import minna_stats as ms  # noqa: E402
import minna_text as mt  # noqa: E402
import survey_cli as cli  # noqa: E402
import survey_data as sd  # noqa: E402
import survey_estimates as se  # noqa: E402
import survey_forms as sf  # noqa: E402
import survey_report as sr  # noqa: E402
import survey_synth as ss  # noqa: E402

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
META, QUESTIONS = sd.load_content()
QMAP = {q["id"]: q for q in QUESTIONS}
CB = mt.Codebook(QUESTIONS)
EST = {e["id"]: e for e in META["estimates"]}
SELLER = ["yes", "yes", "regular"]            # S1, S2, S3


def respondent(**raw):
    """A respondent whose answers are exactly `raw` (question id -> cell text); the rest are missing.
    Built directly, so it bypasses the loader's validation on purpose."""
    row = {qid: CB.map_value(qid, None) for qid in QMAP}
    for qid, cell in raw.items():
        row[qid] = CB.map_value(qid, cell)
    row["_line"] = 2
    row["_price"] = row["price_cell"]["number"]
    return row


class Files(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def load(self, header, body, **kw):
        path = os.path.join(self.dir.name, "d.csv")
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            w.writerows(body)
        return sd.load_responses(path, QUESTIONS, **kw)

    def report(self, header, body):
        rows, audit = self.load(header, body)
        return sr.render(META, rows, audit)


class LoaderRules(Files):
    def test_each_screen_column_is_required_on_its_own(self):
        for header in (["S1", "S3"], ["S2", "S3"], ["S3"]):
            with self.assertRaises(sd.DataError, msg=header):
                self.load(header, [["yes"] * len(header)])
        rows, _ = self.load(["S1", "S2", "S3"], [SELLER])
        self.assertEqual(len(rows), 1)

    def test_all_parcels_refused_is_a_valid_answer(self):
        rows, audit = self.load(["S1", "S2", "S3", "O2", "O5a", "O5b"], [SELLER + ["courier", "5", "5"]])
        self.assertEqual(audit["issues"], {})
        r = se.refusal(rows)
        self.assertEqual((r["respondents"], r["parcels"], r["refused"], r["ratio"]), (1, 5, 5, 1.0))
        _, audit = self.load(["S1", "S2", "S3", "O2", "O5a", "O5b"], [SELLER + ["courier", "5", "6"]])
        self.assertEqual(audit["issues"], {"O5b greater than O5a (both ignored)": 1})

    def test_an_answer_without_a_known_price_is_flagged_in_the_audit(self):
        _, audit = self.load(["S1", "S2", "S3", "W2"], [SELLER + ["yes"]])
        self.assertEqual(audit["issues"],
                         {"W2 answered but the price cell is unknown (excluded from price comparison)": 1})

    def test_an_invalid_answer_is_not_an_answer_even_if_it_has_free_text(self):
        base = {"missing": False, "invalid": False, "codes": [], "number": None, "other": None}
        self.assertTrue(sd.answered({**base, "codes": ["yes"]}))
        self.assertTrue(sd.answered({**base, "number": 0.0}))          # zero is an answer
        self.assertTrue(sd.answered({**base, "other": "text"}))
        self.assertFalse(sd.answered({**base, "invalid": True, "other": "text"}))
        self.assertFalse(sd.answered({**base, "missing": True}))
        self.assertFalse(sd.answered(base))

    def test_skip_logic_follows_the_whole_chain_and_any_of_her_codes(self):
        courier = respondent(S1="yes", S2="yes", S3="regular", O2="hand, courier")
        self.assertTrue(sd.is_expected("O3", courier, QMAP))             # one of two codes is enough
        no_courier = respondent(S1="yes", S2="yes", S3="regular", O2="hand")
        self.assertFalse(sd.is_expected("O3", no_courier, QMAP))
        planner = respondent(S1="yes", S2="yes", S3="planning", O2="courier")   # should never have seen O2
        self.assertFalse(sd.is_expected("O2", planner, QMAP))
        self.assertFalse(sd.is_expected("O3", planner, QMAP))            # O3 -> O2 -> S3: the chain breaks
        self.assertFalse(sd.is_expected("O2", respondent(S1="yes", S2="yes"), QMAP))   # parent unanswered

    def test_per_question_audit_separates_non_response_from_unexpected_answers(self):
        _, audit = self.load(["S1", "S2", "S3", "C1"], [
            SELLER + ["whatsapp"],                    # expected, answered
            SELLER + [""],                            # expected, not answered
            ["yes", "yes", "planning", "facebook"]])  # not expected, answered anyway
        q = audit["questions"]["C1"]
        self.assertEqual((q["expected"], q["answered"], q["nonresponse"], q["unexpected_answers"]), (2, 1, 1, 1))

    def test_the_first_non_empty_duplicate_column_wins(self):
        rows, audit = self.load(["S1", "S2", "S3", "D1", "D1"],
                                [SELLER + ["android", "iphone"], SELLER + ["", "iphone"]])
        self.assertEqual([r["D1"]["codes"] for r in rows], [["android"], ["iphone"]])
        self.assertEqual(audit["duplicate_columns"], ["D1"])

    def test_an_empty_file_is_refused_not_crashed_on(self):
        path = os.path.join(self.dir.name, "empty.csv")
        open(path, "w", encoding="utf-8").close()
        with self.assertRaises(sd.DataError):
            sd.load_responses(path, QUESTIONS)

    def test_rows_shorter_than_the_header_are_read_with_missing_cells(self):
        rows, _ = self.load(["S1", "S2", "S3", "D1", "D2"],
                            [SELLER, SELLER + ["android", "daily"]])
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[0]["D1"]["missing"] and rows[0]["D2"]["missing"])
        self.assertEqual((rows[1]["D1"]["codes"], rows[1]["D2"]["codes"]), (["android"], ["daily"]))

    def test_price_headers_are_not_duplicates_and_the_hidden_price_wins_over_a_header_price(self):
        w2 = QMAP["W2"]["text"]["en"]
        header = ["S1", "S2", "S3", w2.replace("{PRICE}", "500"), w2.replace("{PRICE}", "1000")]
        rows, audit = self.load(header, [SELLER + ["", "yes"], SELLER + ["no", ""]])
        self.assertEqual(audit["duplicate_columns"], [])
        self.assertEqual([(r["W2"]["codes"], r["_price"]) for r in rows], [(["yes"], 1000.0), (["no"], 500.0)])
        rows, _ = self.load(header + ["price_cell"], [SELLER + ["yes", "", "700"]])
        self.assertEqual(rows[0]["_price"], 700.0)          # price_cell says 700, the header says 500

    def test_blank_rows_are_skipped_and_not_counted(self):
        rows, audit = self.load(["S1", "S2", "S3"], [SELLER, ["", "", ""], ["  ", "", ""]])
        self.assertEqual((audit["rows_read"], audit["included"], audit["excluded"]), (1, 1, {}))


class EstimateRules(unittest.TestCase):
    def test_invalid_answers_never_enter_a_denominator(self):
        a, b, c = respondent(O6="replying"), respondent(O6="replying"), respondent(O6="packing")
        b["O6"]["invalid"] = True                      # codes are still present: invalid must win
        self.assertEqual(se.tally([a, b, c], EST["pain_replying"])[:2], (1, 2))

    def test_excluded_codes_and_missing_answers_leave_the_denominator(self):
        rows = [respondent(D3=x) for x in ("often", "never", "pnts", "sometimes", "pnts")] + [respondent()]
        self.assertEqual(se.tally(rows, EST["shared_phone"])[:2], (2, 3))

    def test_cluster_size_needs_80_percent_coded_respondents_and_two_clusters(self):
        item = lambda refs, n: {"n": n, "refs": refs}  # noqa: E731
        self.assertIsNone(se.mean_cluster_size(item(["a", "a", "b", "b", "a"] + [None] * 5, 10)))   # 50% coded
        self.assertIsNone(se.mean_cluster_size(item(["a", "a", "b", "b", "a", "c", "c"] + [None] * 3, 10)))  # 70%
        self.assertEqual(se.mean_cluster_size(item(["a", "a", "b", "b", "a", "c", "c", "d"] + [None] * 2, 10)), 2.0)
        self.assertIsNone(se.mean_cluster_size(item(["a"] * 10, 10)))                                # one cluster
        self.assertIsNone(se.mean_cluster_size(item([], 0)))

    def test_the_price_test_is_lowest_against_highest_and_maybe_counts_as_not_yes(self):
        def priced(price, answer, n):
            return [respondent(W2=answer, price_cell=str(price)) for _ in range(n)]
        rows = (priced(500, "yes", 8) + priced(500, "maybe", 4) + priced(500, "no", 3)
                + priced(1000, "yes", 5) + priced(1000, "no", 10)
                + priced(1500, "yes", 2) + priced(1500, "maybe", 6) + priced(1500, "no", 7))
        w = se.price_cells(rows)
        self.assertEqual([c["price"] for c in w["cells"]], [500.0, 1000.0, 1500.0])
        low = w["cells"][0]
        self.assertEqual((low["n"], low["yes"], low["maybe"], low["no"]), (15, 8, 4, 3))
        self.assertEqual((w["test"]["low"], w["test"]["high"]), (500.0, 1500.0))
        self.assertAlmostEqual(w["test"]["p_value"], ms.fisher_exact(8, 7, 2, 13), places=12)
        self.assertNotAlmostEqual(w["test"]["p_value"], ms.fisher_exact(8, 3, 2, 7), places=6)
        self.assertEqual(se.price_cells([respondent(W2="yes")])["unpriced"], 1)

    def test_refusal_ignores_respondents_who_recall_no_parcels(self):
        rows = [respondent(O5a="10", O5b="2"), respondent(O5a="0", O5b="0"), respondent(O5a="20", O5b="0")]
        r = se.refusal(rows)       # built directly: the loader would have blanked O5a = 0
        self.assertEqual((r["respondents"], r["parcels"], r["refused"], r["zero_refusals"]), (2, 30, 2, 1))
        self.assertIsNone(se.refusal([respondent()]))

    def test_pick_two_counts_each_respondent_by_what_she_chose(self):
        rows = ([respondent(O6="replying") for _ in range(5)] + [respondent(O6="packing") for _ in range(2)]
                + [respondent(O6="replying; packing") for _ in range(3)]
                + [respondent(O6="records") for _ in range(4)] + [respondent()])
        t = se.pick2_test(rows, "replying", "packing")
        self.assertEqual((t["only_a"], t["only_b"], t["both"]), (5, 2, 3))
        self.assertAlmostEqual(t["p_value"], ms.mcnemar_exact(5, 2), places=12)

    def test_top_pains_are_ordered_by_share_and_leave_out_the_derived_estimate(self):
        items = [{"id": "pain_a", "n": 10, "p": 0.2}, {"id": "pain_orderflow", "n": 10, "p": 0.9},
                 {"id": "pain_c", "n": 10, "p": 0.5}, {"id": "pain_b", "n": 10, "p": 0.5},
                 {"id": "pain_empty", "n": 0, "p": None}, {"id": "android", "n": 10, "p": 0.8}]
        self.assertEqual([i["id"] for i in se.top_pains(items)], ["pain_b", "pain_c", "pain_a"])

    def test_the_verdict_is_decided_by_the_right_bound_with_the_right_strictness(self):
        self.assertTrue(se._verdict(0.80, 0.95, 0.80).startswith("PASS"))             # lower bound equal: pass
        self.assertTrue(se._verdict(0.60, 0.95, 0.80).startswith("INCONCLUSIVE"))     # upper bound is high enough
        self.assertTrue(se._verdict(0.50, 0.79, 0.80).startswith("FAIL"))
        self.assertTrue(se._verdict(0.50, 0.80, 0.80).startswith("INCONCLUSIVE"))     # upper bound equal: not fail

    def test_the_clustered_verdict_uses_the_90_percent_wilson_bounds(self):
        refs = [c for c in "abcde" for _ in range(20)]
        out = se.android_decision({"k": 90, "n": 100, "refs": refs}, {"android_lower_bound": 0.80}, rho=0.05)
        lo, hi = ms.wilson_deff(90, 100, 20.0, 0.05, conf=0.90)    # one-sided 95% = two-sided 90%
        self.assertEqual(out["m_bar"], 20.0)
        self.assertAlmostEqual(out["clustered_lower"], lo, places=12)
        self.assertAlmostEqual(out["clustered_upper"], hi, places=12)
        self.assertGreater(out["clustered_lower"], ms.wilson_deff(90, 100, 20.0, 0.05, conf=0.95)[0])

    def test_the_planned_sample_size_is_exact_at_the_boundary(self):
        for n, ok in ((105, False), (106, True)):
            chk = se.sample_check([{"S3": {"codes": ["regular"]}} for _ in range(n)], META)
            self.assertEqual((chk["all"]["meets_target"], chk["sellers"]["meets_target"]), (ok, ok), n)
            self.assertEqual((chk["n"], chk["sellers"]["n"], chk["n_needed"]), (n, n, 106))
        mixed = ["regular"] * 3 + ["occasional"] * 2 + ["planning"] * 4 + ["no"]
        chk = se.sample_check([{"S3": {"codes": [c]}} for c in mixed], META)
        self.assertEqual((chk["n"], chk["sellers"]["n"]), (10, 5))
        self.assertIsNone(se.sample_check([], META)["all"]["margin"])

    def test_the_wide_flag_follows_the_design_block_in_every_table(self):
        loose = {**META, "design": {**META["design"], "wide_margin": 0.30}}
        rows = ([respondent(S3="regular", D1="android") for _ in range(10)]
                + [respondent(S3="regular", D1="iphone") for _ in range(10)])         # 10 of 20: margin about 0.23
        for meta, wide in ((META, True), (loose, False)):
            head = next(i for i in se.headline(rows, meta) if i["id"] == "android")
            seg = next(s for s in se.segment_split(rows, meta, ["android"]) if s["group"] == "sellers")
            self.assertEqual((head["wide"], seg["wide"]), (wide, wide), meta["design"]["wide_margin"])

    def test_hypothetical_and_observed_cluster_views(self):
        guess = se.cluster_view({"k": 40, "n": 100, "refs": []}, [0.02, 0.05, 0.10])
        self.assertFalse(guess["observed"])
        self.assertEqual([r["m"] for r in guess["rows"]], [5, 5, 5, 10, 10, 10, 20, 20, 20])
        last = guess["rows"][-1]
        lo, hi = ms.wilson_deff(40, 100, 20, 0.10)
        self.assertAlmostEqual(last["deff"], 1 + 19 * 0.10)
        self.assertAlmostEqual(last["lo"], lo, places=12)
        self.assertAlmostEqual(last["hi"], hi, places=12)
        self.assertAlmostEqual(last["margin"], max(hi - 0.4, 0.4 - lo))
        # 90 of 100 respondents carry a code (3 clusters of 30): the share is of respondents WITH a code
        refs = [c for c in "abc" for _ in range(30)] + [None] * 10
        seen = se.cluster_view({"k": 40, "n": 100, "refs": refs}, [0.05])
        self.assertTrue(seen["observed"])
        self.assertEqual((seen["clusters"], [r["m"] for r in seen["rows"]]), (3, [30.0]))
        self.assertAlmostEqual(seen["max_share"], 1 / 3, places=12)

    def test_sellers_and_planners_are_split_as_defined(self):
        rows = ([respondent(S3="regular", D1="android") for _ in range(3)] + [respondent(S3="occasional", D1="iphone")]
                + [respondent(S3="planning", D1="android") for _ in range(2)]
                + [respondent(S3="planning", D1="iphone") for _ in range(2)]
                + [respondent(S3="no", D1="android")])
        got = {s["group"]: (s["k"], s["n"]) for s in se.segment_split(rows, META, ["android"])}
        self.assertEqual(got, {"sellers": (3, 4), "planning": (2, 4)})


class ReportRules(Files):
    def test_the_report_prints_what_the_audit_found(self):
        text = self.report(["S1", "S2", "S3", "O2", "O5a", "O5b", "Favourite colour"],
                           [SELLER + ["courier", "4", "9", "blue"], ["yes", "yes", "Maybe", "", "", "", ""]])
        self.assertIn("- Columns not recognised (ignored): 'Favourite colour'", text)
        self.assertIn("- **Issue:** O5b greater than O5a (both ignored): 1 respondent(s)", text)
        self.assertIn("**Unmapped answers in S3** (not counted): 'Maybe' x1", text)
        self.assertIn("- Questions with no column in the file:", text)

    def test_duplicate_columns_misspelled_labels_unexpected_answers_and_unpriced_answers_are_listed(self):
        header = ["S1", "S2", "S3", "S3", "C1", "W2", "price_cell"]
        text = self.report(header, [
            ["yes", "yes", "planning", "", "Whatsap, Facebook", "yes", ""],   # planner answers C1; W2 without a price
            ["yes", "yes", "regular", "", "whatsapp", "no", "500"]])
        self.assertIn("- Questions that appear in several columns (first non-empty used): S3", text)
        self.assertIn("- **Possible misspelled labels in C1** (counted as 'other'): 'Whatsap' looks like 'whatsapp' x1", text)
        self.assertIn("- Answers to C1 from respondents who should not have seen it: 1", text)
        self.assertIn("Answers to W2 from respondents who should not have seen it: 1", text)
        self.assertNotIn("1 W2 answers had no price cell and were left out.", text)

    def test_item_non_response_is_flagged_above_ten_percent_and_not_at_ten(self):
        header = ["S1", "S2", "S3", "C1"]
        at_ten = self.report(header, [SELLER + ["whatsapp"]] * 9 + [SELLER + [""]])
        self.assertNotIn("High item non-response in C1", at_ten)
        over = self.report(header, [SELLER + ["whatsapp"]] * 8 + [SELLER + [""]] * 2)
        self.assertIn("**High item non-response in C1:** 2 of 10 (20.0%)", over)

    def test_one_dominant_referral_cluster_is_flagged_above_a_quarter(self):
        header = ["S1", "S2", "S3", "ref"]
        spread = [SELLER + [c] for c in ("A", "A", "B", "C", "D", "E", "F", "G", "H", "I")]      # largest 20%
        self.assertNotIn("One cluster dominates", self.report(header, spread))
        heavy = [SELLER + [c] for c in ("A", "A", "A", "B", "C", "D", "E", "F", "G", "H")]       # largest 30%
        self.assertIn("**One cluster dominates (over 25%).**", self.report(header, heavy))

    def test_the_target_column_follows_the_exact_sample_size(self):
        for n, flag in ((105, "**no**"), (106, "yes")):
            text = self.report(["S1", "S2", "S3"], [SELLER] * n)
            self.assertIn(f"| all | {n} | ±10.0 pp | {flag} |", text)
            self.assertIn(f"| sellers | {n} | ±10.0 pp | {flag} |", text)

    def test_wide_estimates_carry_the_flag_and_narrow_ones_do_not(self):
        def android_line(n_android, n):
            text = self.report(["S1", "S2", "S3", "D1"],
                               [SELLER + ["android"]] * n_android + [SELLER + ["iphone"]] * (n - n_android))
            return next(line for line in text.splitlines() if line.startswith("| Main phone is an Android smartphone"))
        self.assertTrue(android_line(10, 20).endswith("| WIDE |"))
        self.assertNotIn("WIDE", android_line(200, 400))

    def test_the_price_note_and_the_top_two_wording_follow_the_p_values(self):
        header = ["S1", "S2", "S3", "W2", "price_cell"]
        apart = ([SELLER + ["yes", "500"]] * 30 + [SELLER + ["yes", "1000"]] * 3 + [SELLER + ["no", "1000"]] * 27)
        text = self.report(header, apart)
        self.assertIn("Stated acceptance differs between the two prices; stated is not paid.", text)
        self.assertNotIn("is not evidence of no price effect", text)
        same = ([SELLER + ["yes", "500"]] * 15 + [SELLER + ["no", "500"]] * 15
                + [SELLER + ["yes", "1000"]] * 15 + [SELLER + ["no", "1000"]] * 15)
        text = self.report(header, same)
        self.assertIn("A p-value above 0.05 here is not evidence of no price effect.", text)
        self.assertNotIn("Stated acceptance differs", text)

        header = ["S1", "S2", "S3", "O6"]
        clear = [SELLER + ["replying"]] * 40 + [SELLER + ["packing"]] * 10 + [SELLER + ["records"]] * 5
        self.assertIn("40 picked only the first, 10 only the second", self.report(header, clear))
        self.assertIn("the first is picked more often than the second", self.report(header, clear))
        # 9 against 3: p = 0.146, above 0.05 but well below 0.5
        close = [SELLER + ["replying"]] * 9 + [SELLER + ["packing"]] * 3 + [SELLER + ["records"]]
        text = self.report(header, close)
        self.assertIn("p = 0.146: the first two are not distinguishable", text)

    def test_every_caveat_is_in_the_report(self):
        text = self.report(["S1", "S2", "S3"], [SELLER])
        for phrase in ("Who the numbers describe", "What the intervals mean",
                       "A survey sent online cannot measure who is offline", "Stated is not done",
                       "Many intervals at once", "Free-text answers and language"):
            self.assertIn(f"**{phrase}.**", text)
        self.assertIn(f"With {len(META['estimates'])} estimates at 95% each, about 2 are expected", text)
        self.assertIn("WIDE = margin above 15 pp: the data cannot support a decision on that number.", text)

    def test_the_planning_number_is_the_exact_one_and_the_textbook_one_is_called_too_small(self):
        text = self.report(["S1", "S2", "S3"], [SELLER])
        self.assertIn("Planning number: 106 respondents per group for ±10 pp in the worst case with the exact "
                      "interval (97 is the normal-approximation figure and is not enough).", text)


class CommandLineRules(unittest.TestCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_plan_slow_computes_the_exact_ten_point_drop_and_plain_plan_does_not(self):
        calls = []

        def fake_power(p1, p2, **kw):
            calls.append((p1, p2, kw))
            return 404 if kw else 102
        cheap = [mock.patch.object(ms, "n_per_arm_for_power", fake_power),
                 mock.patch.object(ms, "n_for_margin", lambda m, *a, **k: {0.10: 106, 0.15: 49}[m]),
                 mock.patch.object(ms, "simulate_cluster_coverage",
                                   lambda *a, **k: {"naive_exact": 0.9, "design_effect_wilson": 0.95})]
        for patch in cheap:
            patch.start()
            self.addCleanup(patch.stop)
        _, out, _ = self.run_cli("plan", "--slow")
        self.assertIn("50% vs 40%: exact Fisher test needs 404 respondents per price", out)
        self.assertEqual(calls[-1], (0.5, 0.4, {"start": 269, "stop": 900}))
        calls.clear()
        _, out, _ = self.run_cli("plan")
        self.assertIn("exact not computed (add --slow", out)
        self.assertEqual(calls, [(0.5, 0.3, {})])

    def test_analyze_writes_no_estimates_file_unless_asked(self):
        with tempfile.TemporaryDirectory() as d:
            data = os.path.join(d, "s.csv")
            self.run_cli("synthetic", data, "--n", "40", "--seed", "1")
            code, out, _ = self.run_cli("analyze", data, "--out", os.path.join(d, "r.md"))
            self.assertEqual(code, 0)
            self.assertNotIn("est", out)
            self.assertEqual(sorted(os.listdir(d)), ["r.md", "s.csv", "s.truth.json"])

    def test_selftest_exit_code_reflects_the_result(self):
        class Fails(unittest.TestCase):          # local classes: the loader must not discover them
            def runTest(self):
                self.fail("deliberate failure")

        class Passes(unittest.TestCase):
            def runTest(self):
                pass

        real = unittest.TextTestRunner
        for case, expected in ((Fails, 1), (Passes, 0)):
            suite = unittest.TestSuite([case()])
            with mock.patch.object(unittest.defaultTestLoader, "discover", return_value=suite), \
                    mock.patch.object(unittest, "TextTestRunner",
                                      lambda verbosity=1: real(stream=io.StringIO(), verbosity=0)):
                self.assertEqual(cli.cmd_selftest(None), expected, case.__name__)


class Reproducibility(unittest.TestCase):
    def test_the_same_seed_gives_the_same_file_under_any_hash_randomisation(self):
        # Found while packaging the examples: a set of answers was written in hash order, so the
        # same seed gave different files in different runs. Each run below has its own hash seed.
        code = ("import hashlib, json, survey_synth as ss\n"
                "t, _ = ss.generate(150, seed=3)\n"
                "print(hashlib.sha256(json.dumps(t, ensure_ascii=False).encode()).hexdigest())\n")
        digests = set()
        for hash_seed in ("1", "2", "3"):
            run = subprocess.run([sys.executable, "-B", "-c", code], cwd=HERE, capture_output=True, text=True,
                                 env=dict(os.environ, PYTHONHASHSEED=hash_seed), timeout=120)
            self.assertEqual(run.returncode, 0, run.stderr)
            digests.add(run.stdout.strip())
        self.assertEqual(len(digests), 1, digests)


class ShippedFiles(unittest.TestCase):
    """What ships in generated/ and examples/ must be what the code produces today.
    (Skipped in a copy that does not contain those folders.)"""

    def test_the_printed_surveys_and_the_codebook_are_current(self):
        gen = os.path.join(HERE, "generated")
        if not os.path.isdir(gen):
            self.skipTest("generated/ is not part of this copy")
        for lang in META["languages"]:
            with open(os.path.join(gen, f"survey_{lang}.md"), encoding="utf-8") as fh:
                self.assertEqual(fh.read(), sf.render_survey(META, QUESTIONS, lang), lang)
        with tempfile.TemporaryDirectory() as d:
            fresh = os.path.join(d, "codebook.csv")
            sf.write_codebook(META, QUESTIONS, fresh)
            with open(fresh, "rb") as a, open(os.path.join(gen, "codebook.csv"), "rb") as b:
                self.assertEqual(a.read(), b.read())

    def test_the_example_data_report_and_estimates_are_reproducible(self):
        ex = os.path.join(HERE, "examples")
        if not os.path.isdir(ex):
            self.skipTest("examples/ is not part of this copy")
        data = os.path.join(ex, "synthetic_n300.csv")
        table, _ = ss.generate(300, seed=7)
        with open(data, newline="", encoding="utf-8-sig") as fh:
            self.assertEqual(list(csv.reader(fh)), [[str(c) for c in row] for row in table])
        with open(os.path.join(ex, "synthetic_n300.truth.json"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), json.loads(json.dumps(ss.truth())))
        rows, audit = sd.load_responses(data, QUESTIONS)
        with open(os.path.join(ex, "report_n300.md"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), sr.render(META, rows, audit))
        with open(os.path.join(ex, "estimates_n300.csv"), newline="", encoding="utf-8-sig") as fh:
            shipped = list(csv.DictReader(fh))
        items = se.headline(rows, META)
        self.assertEqual([r["id"] for r in shipped], [i["id"] for i in items])
        for r, i in zip(shipped, items):
            self.assertEqual((int(r["k"]), int(r["n"])), (i["k"], i["n"]), i["id"])
            self.assertAlmostEqual(float(r["share"]), i["p"], places=12)
            self.assertAlmostEqual(float(r["lo"]), i["lo"], places=12)
            self.assertAlmostEqual(float(r["hi"]), i["hi"], places=12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
