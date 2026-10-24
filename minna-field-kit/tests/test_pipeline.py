"""End-to-end tests. Planted answers must come back exactly, planted truth must be recovered,
and corrupt data must be reported rather than absorbed."""
import contextlib
import csv
import io
import os
import sys
import tempfile
import unittest
from fractions import Fraction

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import survey_cli as cli  # noqa: E402
import survey_data as sd  # noqa: E402
import survey_estimates as se  # noqa: E402
import survey_report as sr  # noqa: E402
import survey_synth as ss  # noqa: E402

META, QUESTIONS = sd.load_content()


def generate_and_load(seed, n=400, **kw):
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "r.csv")
        _, planted = ss.generate(n, seed=seed, path=path, **kw)
        rows, audit = sd.load_responses(path, QUESTIONS)
    return planted, rows, audit


def write_csv(path, header, body):
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(body)


class CellRecovery(unittest.TestCase):
    CONFIGS = [(1, "text", "column", True), (2, "id", "column", True), (3, "mixed", "column", True),
               (4, "text", "headers", False), (5, "mixed", "headers", True)]

    def test_every_planted_cell_comes_back_exactly(self):
        for seed, headers, layout, with_price in self.CONFIGS:
            planted, rows, audit = generate_and_load(seed, headers=headers, price_layout=layout,
                                                     include_price_cell=with_price)
            compared = 0
            for row in rows:
                plant = planted[row["_line"] - 2]
                for qid, info in plant.items():
                    if qid == "price_cell":
                        continue
                    m = row[qid]
                    compared += 1
                    where = (seed, headers, layout, row["_line"], qid, info, m)
                    if info.get("missing"):
                        self.assertTrue(m["missing"], where)
                    elif "codes" in info:
                        self.assertEqual(sorted(m["codes"]), sorted(info["codes"]), where)
                        self.assertEqual(m["unmapped"], [], where)
                    else:
                        self.assertEqual(m["number"], info["number"], where)
                    if qid == "W2":
                        # The price is recoverable unless the answer is missing AND there is no
                        # price_cell column: then nothing in the file says which price was shown.
                        if info.get("missing") and not with_price and layout == "headers":
                            self.assertIsNone(row["_price"], where)
                        else:
                            self.assertEqual(row["_price"], float(info["price"]), where)
            self.assertGreater(compared, 7000, (seed, compared))

    def test_exclusions_match_what_was_planted(self):
        for seed, headers, layout, with_price in self.CONFIGS[:3]:
            planted, rows, audit = generate_and_load(seed, headers=headers, price_layout=layout)
            no_consent = sum(p["S1"]["codes"] == ["no"] for p in planted)
            underage = sum(p["S1"]["codes"] == ["yes"] and p["S2"]["codes"] == ["no"] for p in planted)
            self.assertEqual(audit["excluded"].get("no consent (S1 not yes)", 0), no_consent)
            self.assertEqual(audit["excluded"].get("not confirmed 18 or older (S2 not yes)", 0), underage)
            self.assertEqual(audit["included"], len(planted) - no_consent - underage)
            self.assertEqual(audit["unmatched_headers"], ["Timestamp"])
            self.assertEqual(audit["issues"], {})

    def test_generation_is_deterministic(self):
        a, _ = ss.generate(80, seed=9)
        b, _ = ss.generate(80, seed=9)
        c, _ = ss.generate(80, seed=10)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)


class RecoversTruth(unittest.TestCase):
    SEEDS = range(200, 224)

    @classmethod
    def setUpClass(cls):
        cls.truth = ss.truth()
        cls.runs = []
        for seed in cls.SEEDS:
            _, rows, _ = generate_and_load(seed, n=300, headers=("text", "id", "mixed")[seed % 3])
            cls.runs.append((se.headline(rows, META), se.refusal(rows), se.price_cells(rows)))

    def test_exact_intervals_cover_the_planted_truth(self):
        hit = total = 0
        for items, _, _ in self.runs:
            for it in items:
                total += 1
                hit += it["lo"] <= self.truth["estimates"][it["id"]] <= it["hi"]
        self.assertGreaterEqual(hit / total, 0.93, f"coverage {hit}/{total}")

    def test_point_estimates_are_unbiased_enough_to_notice_a_denominator_bug(self):
        for est in META["estimates"]:
            ps = [next(i for i in items if i["id"] == est["id"])["p"] for items, _, _ in self.runs]
            mean = sum(ps) / len(ps)
            self.assertAlmostEqual(mean, self.truth["estimates"][est["id"]], delta=0.03, msg=est["id"])

    def test_refusal_ratio_and_price_cells(self):
        ratios = [r["ratio"] for _, r, _ in self.runs]
        self.assertAlmostEqual(sum(ratios) / len(ratios), self.truth["refusal_ratio"], delta=0.02)
        for price, planted_yes in self.truth["wtp_yes"].items():
            shares = []
            for _, _, w in self.runs:
                cell = next(c for c in w["cells"] if c["price"] == float(price))
                shares.append(cell["p"])
            self.assertAlmostEqual(sum(shares) / len(shares), planted_yes, delta=0.04, msg=price)


class PlantedTruthIsExact(unittest.TestCase):
    """truth() gives each estimate's true value by formula from the generator's settings. The 24-run
    check above only sees errors larger than about 2.5 pp (a dropped denominator worth 2.1 pp got
    through it), so each formula is also compared with a second derivation that enumerates every
    possible outcome with exact fractions."""
    TRUTH = ss.truth()["estimates"]
    QTYPE = {q["id"]: q["type"] for q in QUESTIONS}

    @staticmethod
    def frac(x):
        return Fraction(str(x))

    def test_single_choice_truths_are_the_listed_codes_over_everyone_not_excluded(self):
        checked = 0
        for e in META["estimates"]:
            if self.QTYPE[e["q"]] != "single":
                continue
            dist = {k: self.frac(v) for k, v in ss.P[e["q"]].items()}
            self.assertEqual(sum(dist.values()), 1, e["q"])
            counted = sum(v for c, v in dist.items() if c not in e.get("exclude", []))
            share = sum(dist[c] for c in e["codes"]) / counted
            self.assertAlmostEqual(self.TRUTH[e["id"]], float(share), places=12, msg=e["id"])
            checked += 1
        self.assertGreaterEqual(checked, 12)

    def test_multi_choice_truths_equal_an_enumeration_of_every_subset(self):
        def marginals(p):
            """P(code chosen) when each code is chosen independently and the draw is repeated until
            at least one code is chosen: add up every non-empty subset."""
            keys = list(p)
            chosen, total = {k: Fraction(0) for k in keys}, Fraction(0)
            for mask in range(1, 2 ** len(keys)):
                prob = Fraction(1)
                for i, k in enumerate(keys):
                    prob *= self.frac(p[k]) if mask >> i & 1 else 1 - self.frac(p[k])
                total += prob
                for i, k in enumerate(keys):
                    if mask >> i & 1:
                        chosen[k] += prob
            return {k: v / total for k, v in chosen.items()}

        def reference(e):
            (code,) = e["codes"]
            qid = e["q"]
            if qid == "C1":      # her main app is always listed; every other app is added independently
                extra = self.frac(ss.P["C1_extra"][code])
                return sum(self.frac(pm) * (1 if main == code else extra) for main, pm in ss.P["C2"].items())
            if qid in ("C3", "O2"):
                return marginals(ss.P[qid])[code]
            if qid == "M2":      # "allow all" replaces the whole list for 15% of respondents
                return (1 - self.frac(ss.P["M2_allow_all"])) * marginals(ss.P["M2"])[code]
            if qid == "M4":      # "nobody" replaces the whole list for 8% of respondents
                nobody = self.frac(ss.P["M4_nobody"])
                return nobody if code == "nobody" else (1 - nobody) * marginals(ss.P["M4"])[code]
            return None

        checked = 0
        for e in META["estimates"]:
            want = reference(e) if self.QTYPE[e["q"]] == "multi" and e["q"] != "O6" else None
            if want is not None:
                self.assertAlmostEqual(self.TRUTH[e["id"]], float(want), places=12, msg=e["id"])
                checked += 1
        self.assertGreaterEqual(checked, 17)

    def test_pick_two_truths_equal_a_sum_over_every_ordered_draw(self):
        # The generator picks 1 task (40%) or 2 (60%); each pick takes a task with probability
        # proportional to its weight, and the task is then removed from the pool.
        w = {k: self.frac(v) for k, v in ss.P["O6_w"].items()}
        one, two = self.frac(ss.P["O6_k"][1]), self.frac(ss.P["O6_k"][2])
        total = sum(w.values())

        def exact(tasks):
            first = sum(w[t] for t in tasks) / total
            both = sum(w[u] / total * w[v] / (total - w[u])
                       for u in w for v in w if u != v and (u in tasks or v in tasks))
            return float(one * first + two * both)

        checked = 0
        for e in META["estimates"]:
            if e["q"] == "O6":
                self.assertAlmostEqual(self.TRUTH[e["id"]], exact(e["codes"]), places=12, msg=e["id"])
                checked += 1
        self.assertGreaterEqual(checked, 8)


class BadData(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def path(self, name="d.csv"):
        return os.path.join(self.dir.name, name)

    def test_impossible_answers_are_reported_and_kept_out_of_the_estimates(self):
        header = ["S1", "S2", "S3", "O2", "O5a", "O5b", "O6", "M2"]
        body = [
            ["yes", "yes", "regular", "courier", "10", "12", "replying", "send_messages, allow_all"],
            ["yes", "yes", "regular", "courier", "25", "3", "replying; packing; records", "handle_money"],
            ["yes", "yes", "regular", "courier", "10", "2", "replying", "handle_money"],
            ["no", "", "", "", "", "", "", ""],
            ["yes", "no", "", "", "", "", "", ""],
        ]
        write_csv(self.path(), header, body)
        rows, audit = sd.load_responses(self.path(), QUESTIONS)
        self.assertEqual(audit["included"], 3)
        self.assertEqual(audit["excluded"], {"no consent (S1 not yes)": 1,
                                             "not confirmed 18 or older (S2 not yes)": 1})
        self.assertEqual(audit["issues"], {
            "O5b greater than O5a (both ignored)": 1,
            "O5a: number outside 1-20": 1,
            "O6: more than 2 choices (answer ignored)": 1,
            "M2: 'allow all' together with refusals (kept, contradictory)": 1})
        refusal = se.refusal(rows)
        self.assertEqual((refusal["respondents"], refusal["parcels"], refusal["refused"]), (1, 10, 2))
        pain = next(e for e in META["estimates"] if e["id"] == "pain_replying")
        self.assertEqual(se.tally(rows, pain)[:2], (2, 2))      # the 3-choice answer is not counted

    def test_missing_consent_columns_are_refused_unless_screening_is_asserted(self):
        write_csv(self.path(), ["S3", "D1"], [["regular", "android"], ["planning", "iphone"]])
        with self.assertRaises(sd.DataError):
            sd.load_responses(self.path(), QUESTIONS)
        rows, audit = sd.load_responses(self.path(), QUESTIONS, assume_screened=True)
        self.assertEqual(len(rows), 2)

    def test_unmapped_values_and_misspelled_labels_are_surfaced(self):
        write_csv(self.path(), ["S1", "S2", "S3", "C1"],
                  [["yes", "yes", "regular", "Whatsap, Facebook"], ["yes", "yes", "Maybe", "WhatsApp"]])
        rows, audit = sd.load_responses(self.path(), QUESTIONS)
        self.assertEqual(audit["questions"]["S3"]["unmapped"]["Maybe"], 1)
        self.assertEqual(audit["questions"]["C1"]["near"]["'Whatsap' looks like 'whatsapp'"], 1)
        self.assertEqual(audit["questions"]["C1"]["other"]["Whatsap"], 1)

    def test_duplicate_and_unknown_columns_are_listed(self):
        write_csv(self.path(), ["S1", "S1", "S2", "S3", "Favourite colour"],
                  [["", "yes", "yes", "regular", "blue"]])
        rows, audit = sd.load_responses(self.path(), QUESTIONS)
        self.assertEqual(audit["duplicate_columns"], ["S1"])
        self.assertEqual(audit["unmatched_headers"], ["Favourite colour"])
        self.assertEqual(len(rows), 1)                      # first non-empty S1 value is used

    def test_a_price_without_a_price_cell_is_left_out_and_counted(self):
        write_csv(self.path(), ["S1", "S2", "S3", "W2"], [["yes", "yes", "regular", "yes"]])
        rows, _ = sd.load_responses(self.path(), QUESTIONS)
        w = se.price_cells(rows)
        self.assertEqual((w["cells"], w["unpriced"]), ([], 1))


class Reports(unittest.TestCase):
    def test_report_contains_the_decision_aids_and_matches_the_estimates(self):
        _, rows, audit = generate_and_load(7, n=300)
        text = sr.render(META, rows, audit)
        for needle in ("Read this first", "1. Data quality", "2. Sample and precision", "3. Estimates",
                       "D2: does an Android-only pilot reach current sellers?", "D1: which job first?", "exact McNemar",
                       "Willingness to pay", "exact Fisher", "5. If respondents came in clusters",
                       "Allowing for clustering", "6. Sellers"):
            self.assertIn(needle, text)
        self.assertNotIn("None", text)
        self.assertNotIn("nan", text.lower().replace("finance", ""))
        android = next(i for i in se.headline(rows, META) if i["id"] == "android")
        self.assertIn(f"{android['k']} / {android['n']}", text)
        self.assertIn(f"respondents included: **{audit['included']}**", text)

    def test_android_pilot_decision_uses_current_sellers_not_planners(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "r.csv")
            write_csv(path, ["S1", "S2", "S3", "D1"], [
                ["yes", "yes", "regular", "android"],
                ["yes", "yes", "occasional", "iphone"],
                ["yes", "yes", "planning", "android"],
            ])
            rows, audit = sd.load_responses(path, QUESTIONS)
            text = sr.render(META, rows, audit)
        self.assertIn("Among current sellers only (S3 = regular or occasional)", text)
        self.assertIn("(1 of 2)", text)
        self.assertNotIn("(2 of 3). Threshold", text)

    def test_answers_to_questions_behind_a_skip_gate_do_not_enter_estimates(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "r.csv")
            write_csv(path, ["S1", "S2", "S3", "C1"], [
                ["yes", "yes", "regular", "whatsapp"],
                ["yes", "yes", "planning", "whatsapp"],
            ])
            rows, audit = sd.load_responses(path, QUESTIONS)
        item = next(i for i in se.headline(rows, META) if i["id"] == "whatsapp_any")
        self.assertEqual((item["k"], item["n"]), (1, 1))
        self.assertEqual(audit["questions"]["C1"]["unexpected_answers"], 1)

    def test_tiny_and_empty_datasets_render_without_crashing(self):
        with tempfile.TemporaryDirectory() as d:
            ss.generate(6, seed=3, path=os.path.join(d, "a.csv"))
            write_csv(os.path.join(d, "b.csv"), ["S1", "S2"], [["No, I do not agree", ""], ["لا، لا أوافق", ""]])
            write_csv(os.path.join(d, "c.csv"), ["S1", "S2", "S3"], [])
            for name in ("a.csv", "b.csv", "c.csv"):
                rows, audit = sd.load_responses(os.path.join(d, name), QUESTIONS)
                text = sr.render(META, rows, audit)
                self.assertIn("Data quality", text, name)

    def test_the_two_android_verdicts_follow_the_bounds(self):
        item = {"k": 90, "n": 100, "refs": ["a"] * 50 + ["b"] * 50}
        d = {"android_lower_bound": 0.80}
        out = se.android_decision(item, d)
        self.assertTrue(out["status"].startswith("PASS"))          # one-sided lower bound ~ 83%
        self.assertIn("clustered_status", out)
        item = {"k": 60, "n": 100, "refs": []}
        self.assertTrue(se.android_decision(item, d)["status"].startswith("FAIL"))
        item = {"k": 82, "n": 100, "refs": []}
        self.assertTrue(se.android_decision(item, d)["status"].startswith("INCONCLUSIVE"))
        self.assertEqual(se.android_decision({"k": 0, "n": 0, "refs": []}, d)["status"], "NO DATA")


class CommandLine(unittest.TestCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_synthetic_then_analyze_then_render(self):
        with tempfile.TemporaryDirectory() as d:
            data, report, est = (os.path.join(d, n) for n in ("s.csv", "report.md", "est.csv"))
            self.assertEqual(self.run_cli("synthetic", data, "--n", "120", "--seed", "2")[0], 0)
            self.assertTrue(os.path.exists(os.path.join(d, "s.truth.json")))
            code, out, _ = self.run_cli("analyze", data, "--out", report, "--estimates-csv", est)
            self.assertEqual(code, 0)
            self.assertIn("rows included", out)
            with open(est, newline="", encoding="utf-8-sig") as fh:
                self.assertEqual(len(list(csv.DictReader(fh))), len(META["estimates"]))
            code, out, _ = self.run_cli("render", "--out", os.path.join(d, "gen"))
            self.assertEqual(code, 0)
            self.assertIn("UNFILLED PLACEHOLDERS", out)
            self.assertEqual(sorted(os.listdir(os.path.join(d, "gen"))),
                             ["codebook.csv", "survey_ar.md", "survey_en.md", "survey_fr.md"])

    def test_analyze_refuses_a_file_without_consent_columns(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.csv")
            write_csv(path, ["S3"], [["regular"]])
            code, _, err = self.run_cli("analyze", path, "--out", os.path.join(d, "r.md"))
            self.assertEqual(code, 2)
            self.assertIn("REFUSED", err)
            self.assertFalse(os.path.exists(os.path.join(d, "r.md")))

    def test_plan_prints_the_computed_track_p_numbers(self):
        code, out, _ = self.run_cli("plan")
        self.assertEqual(code, 0)
        for needle in ("exact ±10 pp: n = 106", "textbook (normal approximation) ±10 pp: n = 97",
                       "exact ±15 pp: n = 49",
                       "50% vs 30%: exact Fisher test needs 102 respondents per price; the textbook normal approximation says 91",
                       "50% vs 40%: textbook normal approximation says 385 per price; exact not computed",
                       "n = 105: margin ±10.03 pp", "n =  97: margin ±10.45 pp",
                       "20%: ", "14 interviews", " 0 of 14: prevalence at least  0.0% and at most  19.3%",
                       " 5 of 10: prevalence at least 22.2%"):
            self.assertIn(needle, out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
