#!/usr/bin/env python3
"""Minna field kit. Commands:

  plan                         the Track P arithmetic, computed live
  render [--out DIR]           survey_en.md, survey_fr.md, survey_ar.md and codebook.csv
  synthetic OUT.csv [--n N]    planted-truth test data (describes nobody)
  analyze RESPONSES.csv        data-quality audit, estimates, decision aids -> report.md
  selftest                     run every test in tests/

Standard library only (scipy is used by the tests when installed).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import unittest

import minna_stats as ms
import survey_data as sd
import survey_forms as sf
import survey_report as sr
import survey_synth as ss

HERE = os.path.dirname(os.path.abspath(__file__))


def cmd_plan(args) -> int:
    meta, _ = sd.load_content()
    d = meta["design"]
    print("Track P arithmetic (every number below is computed now, not typed in)\n")
    print("Survey precision, 95%, worst case over all outcomes, exact interval")
    for n in (97, 105, d["n_min_exact"]):
        print(f"  n = {n:3d}: margin ±{100 * ms.worst_case_margin(n):.2f} pp")
    print(f"  textbook (normal approximation) ±10 pp: n = {ms.normal_n_for_margin(0.10)}; "
          f"exact ±10 pp: n = {ms.n_for_margin(0.10)}; exact ±15 pp: n = {ms.n_for_margin(0.15)}")
    print("\nInterviews, discovery (a trait seen at least once with 95% probability)")
    for p in (0.30, 0.20, 0.10, 0.05):
        print(f"  prevalence {100 * p:4.0f}%: {ms.n_to_detect(p):3d} interviews")
    for n in (10, 14, 20):
        print(f"  {n} interviews see any trait with prevalence >= {100 * ms.min_detectable_prevalence(n):.1f}%")
    print("\nInterviews, what a count proves (one-sided 95%, only inside the recruitment channel)")
    for k, n in ((0, 14), (5, 10), (7, 14), (10, 14)):
        lo, hi = ms.cp_lower_one_sided(k, n), ms.cp_upper_one_sided(k, n)
        print(f"  {k:2d} of {n:2d}: prevalence at least {100 * lo:4.1f}% and at most {100 * hi:5.1f}%")
    print("\nTwo prices, stated acceptance (80% power, 5% level, two-sided)")
    print(f"  50% vs 30%: exact Fisher test needs {ms.n_per_arm_for_power(0.5, 0.3)} respondents per price; "
          f"the textbook normal approximation says {ms.normal_n_per_arm(0.5, 0.3)}")
    normal = ms.normal_n_per_arm(0.5, 0.4)
    if args.slow:
        exact = ms.n_per_arm_for_power(0.5, 0.4, start=int(0.7 * normal), stop=900)
        print(f"  50% vs 40%: exact Fisher test needs {exact} respondents per price (scan starts at 70% of the "
              f"textbook figure {normal})")
    else:
        print(f"  50% vs 40%: textbook normal approximation says {normal} per price; exact not computed (add --slow, about 15 s)")
    print("\nCoverage of the nominal 95% interval when respondents come in clusters (2000 simulated surveys each)")
    print("  clusters x size   rho   naive exact   design-effect Wilson (true rho)")
    for nc, m, rho in ((100, 1, 0.0), (20, 5, 0.10), (10, 10, 0.10), (10, 10, 0.20)):
        r = ms.simulate_cluster_coverage(0.5, nc, m, rho, reps=2000, seed=11)
        print(f"  {nc:3d} x {m:<3d}         {rho:.2f}  {100 * r['naive_exact']:6.1f}%      {100 * r['design_effect_wilson']:6.1f}%")
    return 0


def cmd_render(args) -> int:
    meta, qs = sd.load_content()
    os.makedirs(args.out, exist_ok=True)
    for lang in meta["languages"]:
        path = os.path.join(args.out, f"survey_{lang}.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(sf.render_survey(meta, qs, lang))
        print("wrote", path)
    n = sf.write_codebook(meta, qs, os.path.join(args.out, "codebook.csv"))
    print(f"wrote {os.path.join(args.out, 'codebook.csv')} ({n} rows)")
    left = sf.placeholders(meta)
    print("UNFILLED PLACEHOLDERS (fill before fielding):", ", ".join(left))
    print("Price cells are placeholders:", meta["design"]["price_cells_dzd"], "DZD")
    return 0


def cmd_synthetic(args) -> int:
    table, _ = ss.generate(args.n, seed=args.seed, headers=args.headers,
                           price_layout=args.price_layout, path=args.out)
    truth_path = os.path.splitext(args.out)[0] + ".truth.json"
    with open(truth_path, "w", encoding="utf-8") as fh:
        json.dump(ss.truth(), fh, indent=1, ensure_ascii=False)
    print(f"wrote {args.out} ({len(table) - 1} rows, planted truth in {truth_path})")
    return 0


def cmd_analyze(args) -> int:
    meta, qs = sd.load_content()
    try:
        rows, audit = sd.load_responses(args.responses, qs, assume_screened=args.assume_screened)
    except sd.DataError as exc:
        print("REFUSED:", exc, file=sys.stderr)
        return 2
    report = sr.render(meta, rows, audit)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(report)
    print(f"wrote {args.out}: {audit['included']} of {audit['rows_read']} rows included")
    if args.estimates_csv:
        from survey_estimates import headline
        with open(args.estimates_csv, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(["id", "label", "k", "n", "share", "lo", "hi", "margin", "assumptions"])
            for i in headline(rows, meta):
                w.writerow([i["id"], i["label"], i["k"], i["n"], i["p"], i["lo"], i["hi"], i["margin"],
                            " ".join(i["assumption"])])
        print("wrote", args.estimates_csv)
    return 0


def cmd_selftest(_args) -> int:
    suite = unittest.defaultTestLoader.discover(os.path.join(HERE, "tests"), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    return 0 if result.wasSuccessful() else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--slow", action="store_true", help="also compute the exact 50%% vs 40%% sample size")
    p.set_defaults(fn=cmd_plan)
    p = sub.add_parser("render")
    p.add_argument("--out", default=os.path.join(HERE, "generated"))
    p.set_defaults(fn=cmd_render)
    p = sub.add_parser("synthetic")
    p.add_argument("out")
    p.add_argument("--n", type=int, default=300)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--headers", choices=["text", "id", "mixed"], default="text")
    p.add_argument("--price-layout", choices=["column", "headers"], default="column")
    p.set_defaults(fn=cmd_synthetic)
    p = sub.add_parser("analyze")
    p.add_argument("responses")
    p.add_argument("--out", default="report.md")
    p.add_argument("--estimates-csv")
    p.add_argument("--assume-screened", action="store_true",
                   help="only if consent and the 18+ screen were enforced before export")
    p.set_defaults(fn=cmd_analyze)
    sub.add_parser("selftest").set_defaults(fn=cmd_selftest)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
