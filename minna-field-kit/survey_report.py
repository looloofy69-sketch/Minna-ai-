"""survey_report: turn rows + audit into one markdown report (standard library only)."""
from __future__ import annotations

import minna_stats as ms
import survey_estimates as se

CAVEATS = [
    "**Who the numbers describe.** Respondents reached through the channels in section 2 who chose to answer. Not Algerian women in general, and not even all women in those groups.",
    "**What the intervals mean.** Exact 95% intervals for sampling noise if respondents were drawn at random from that channel. A convenience or referral sample is not; section 5 shows how much wider the honest interval can be.",
    "**A survey sent online cannot measure who is offline.** A-01 (reach) is not testable this way; it needs a sample frame that does not depend on being online.",
    "**Stated is not done.** Interest, willingness to pay and the recalled refusal rate overstate or distort behaviour. Treat them as screens. The pilot's payments and logs are the evidence.",
    "**Many intervals at once.** With {n_est} estimates at 95% each, about {expected_miss:.0f} are expected to miss the truth by chance. Decide which numbers matter before reading them, not after.",
    "**Free-text answers and language.** Self-reported writing language is weak evidence; the dialect evaluation set (M1) must be built from real, consented messages.",
]


def pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def span(lo, hi) -> str:
    return "n/a" if lo is None else f"{100 * lo:.1f} to {100 * hi:.1f}"


def table(head: list[str], rows: list[list]) -> list[str]:
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return out + [""]


def render(meta: dict, rows: list[dict], audit: dict) -> str:
    d = meta["design"]
    items = se.headline(rows, meta)
    byid = {i["id"]: i for i in items}
    L: list[str] = [f"# Survey analysis report", "",
                    f"Source file: `{audit['file']}` · respondents included: **{audit['included']}**", "",
                    "## Read this first", ""]
    L += [f"- {c.format(n_est=len(items), expected_miss=len(items) * (1 - d['conf']))}" for c in CAVEATS] + [""]

    # ---- 1. data quality
    L += ["## 1. Data quality (read before the estimates)", ""]
    L += table(["Item", "Count"], [["Rows read", audit["rows_read"]], ["Included", audit["included"]]]
               + [[f"Excluded: {k}", v] for k, v in audit["excluded"].items()])
    if audit["unmatched_headers"]:
        L += [f"- Columns not recognised (ignored): {', '.join(repr(h) for h in audit['unmatched_headers'])}"]
    if audit["questions_without_column"]:
        L += [f"- Questions with no column in the file: {', '.join(audit['questions_without_column'])}"]
    if audit["duplicate_columns"]:
        L += [f"- Questions that appear in several columns (first non-empty used): {', '.join(audit['duplicate_columns'])}"]
    for msg, c in audit["issues"].items():
        L += [f"- **Issue:** {msg}: {c} respondent(s)"]
    for qid, s in audit["questions"].items():
        if s["unmapped"]:
            L += [f"- **Unmapped answers in {qid}** (not counted): " + "; ".join(
                f"{t!r} x{c}" for t, c in s["unmapped"].most_common(5))]
        if s["near"]:
            L += [f"- **Possible misspelled labels in {qid}** (counted as 'other'): " + "; ".join(
                f"{t} x{c}" for t, c in s["near"].most_common(5))]
        if s["other"]:
            L += [f"- Free-text 'other' in {qid}: " + "; ".join(
                f"{t[:40]!r} x{c}" for t, c in s["other"].most_common(5))]
        if s["expected"] and s["nonresponse"] / s["expected"] > 0.10:
            L += [f"- **High item non-response in {qid}:** {s['nonresponse']} of {s['expected']} "
                  f"({pct(s['nonresponse'] / s['expected'])}); estimates from it may be biased."]
        if s["unexpected_answers"]:
            L += [f"- Answers to {qid} from respondents who should not have seen it: {s['unexpected_answers']}"]
    L += [""]

    # ---- 2. sample
    chk = se.sample_check(rows, meta)
    L += ["## 2. Sample and precision", ""]
    L += table(["Group", "n", "Worst-case exact margin", f"Meets ±{100 * d['margin_target']:.0f} pp"],
               [[g, chk[g]["n"], "n/a" if chk[g]["margin"] is None else f"±{100 * chk[g]['margin']:.1f} pp",
                 "yes" if chk[g]["meets_target"] else "**no**"] for g in ("all", "sellers")])
    L += [f"Planning number: {d['n_min_exact']} respondents per group for ±{100 * d['margin_target']:.0f} pp "
          f"in the worst case with the exact interval ({d['n_min_textbook']} is the normal-approximation figure and is not enough). "
          "Most estimates are far from 50%, so their margins are smaller; the table below shows each one.", ""]
    for qid, name in (("S3", "Segment (S3)"), ("P3", "How reached (P3)")):
        counts: dict[str, int] = {}
        for r in rows:
            for c in r[qid]["codes"][:1]:
                counts[c] = counts.get(c, 0) + 1
        L += [f"- {name}: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))]
    refs = [r["ref"]["other"] for r in rows if r["ref"]["other"]]
    if refs:
        top = max(refs.count(x) for x in set(refs))
        L += [f"- Referral codes: {len(set(refs))} clusters; the largest holds {pct(top / len(refs))} of respondents with a code."
              + (" **One cluster dominates (over 25%).**" if top / len(refs) > 0.25 else "")]
    L += [""]

    # ---- 3. estimates
    L += ["## 3. Estimates (exact 95% intervals, percentage points)", ""]
    L += table(["Estimate", "k / n", "Share", "95% interval", "± (pp)", "Assumption", "Flag"],
               [[i["label"], f"{i['k']} / {i['n']}", pct(i["p"]), span(i["lo"], i["hi"]),
                 "n/a" if i["margin"] is None else f"{100 * i['margin']:.1f}", ", ".join(i["assumption"]),
                 "WIDE" if i["wide"] else ""] for i in items])
    L += [f"WIDE = margin above {100 * d['wide_margin']:.0f} pp: the data cannot support a decision on that number.", ""]

    # ---- 4. decision aids
    L += ["## 4. Decision aids", "", "### D2: does an Android-only pilot reach current sellers?", ""]
    # The pilot decision is about current sellers, not planners or other respondents.
    android_est = next(e for e in meta["estimates"] if e["id"] == "android")
    current_seller = lambda r: bool(r["S3"]["codes"][:1] and r["S3"]["codes"][0] in se.SELLERS)
    seller_k, seller_n, seller_refs = se.tally(rows, android_est, current_seller)
    seller_android = {"k": seller_k, "n": seller_n, "refs": seller_refs}
    a = se.android_decision(seller_android, d)
    if "lower" in a:
        L += [f"Among current sellers only (S3 = regular or occasional), the one-sided 95% bounds for Android share are "
              f"at least **{pct(a['lower'])}** and at most **{pct(a['upper'])}** "
              f"({a['k']} of {a['n']}). Threshold {pct(a['threshold'])} ({d['android_status']})", "",
              f"**Treating respondents as independent: {a['status']}.** These bounds describe sampling uncertainty under an idealised independent-sampling model; they do not correct selection bias from convenience/referral recruitment.", ""]
        if "clustered_status" in a:
            L += [f"**Allowing for clustering** (mean {a['m_bar']:.1f} respondents per referral code, assumed rho = {a['rho']}): "
                  f"at least {pct(a['clustered_lower'])} and at most {pct(a['clustered_upper'])}: "
                  f"**{a['clustered_status']}.** This is only a clustering sensitivity analysis; it does not correct selection bias from convenience/referral recruitment.", ""]
    else:
        L += ["No usable Android-phone answers from current sellers.", ""]

    L += ["### D1: which job first?", ""]
    pains = se.top_pains(items)
    L += table(["Task (top-2 pick)", "Share of sellers", "95% interval"],
               [[p["label"], pct(p["p"]), span(p["lo"], p["hi"])] for p in pains[:5]])
    if len(pains) >= 2:
        t = se.pick2_test(rows, pains[0]["id"][5:], pains[1]["id"][5:])
        verdict = ("the first two are not distinguishable" if t["p_value"] >= 0.05
                   else "the first is picked more often than the second")
        L += [f"Top two compared on the same respondents (exact McNemar): {t['only_a']} picked only the first, "
              f"{t['only_b']} only the second, p = {t['p_value']:.3f}: {verdict}.", ""]
    of = byid["pain_orderflow"]
    L += [f"Any part of the order-to-parcel flow (confirming, parcels, tracking) is a top-2 pain for "
          f"{pct(of['p'])} of sellers ({span(of['lo'], of['hi'])}). The plan sets no numeric rule for wedge A; "
          "decide the rule before reading this number, and use the interviews to explain it.", ""]

    L += ["### Parcels refused (recall of the last 20)", ""]
    rf = se.refusal(rows)
    if rf:
        L += [f"{rf['respondents']} respondents, {int(rf['parcels'])} parcels, {int(rf['refused'])} refused: pooled "
              f"**{pct(rf['ratio'])}** (resampling respondents: {span(rf['lo'], rf['hi'])}). "
              f"{rf['zero_refusals']} respondents reported none. Recall is imperfect and the percentile interval is approximate; "
              "A-08 is settled only by pilot data.", ""]
    else:
        L += ["No usable pairs.", ""]

    L += ["### Willingness to pay (stated, by randomly assigned price)", ""]
    w = se.price_cells(rows)
    if w["cells"]:
        L += table(["Price (DZD / month)", "n", "yes", "maybe", "no", "Yes share", "95% interval"],
                   [[int(c["price"]), c["n"], c["yes"], c["maybe"], c["no"], pct(c["p"]), span(c["lo"], c["hi"])]
                    for c in w["cells"]])
        if w["test"]:
            n_arm = ms.n_per_arm_for_power(0.5, 0.3)
            L += [f"Lowest vs highest price, yes vs not-yes (exact Fisher): p = {w['test']['p_value']:.3f}. "
                  f"For scale: detecting a drop from 50% to 30% with 80% power needs {n_arm} respondents per price; "
                  f"you have {min(c['n'] for c in w['cells'])} in the smaller cell. "
                  + ("A p-value above 0.05 here is not evidence of no price effect." if w["test"]["p_value"] >= 0.05
                     else "Stated acceptance differs between the two prices; stated is not paid.") , ""]
        if w["unpriced"]:
            L += [f"{w['unpriced']} W2 answers had no price cell and were left out.", ""]
    else:
        L += ["No price-cell data.", ""]

    # ---- 5. clustering
    L += ["## 5. If respondents came in clusters", "",
          "Wilson interval at the effective sample size n / (1 + (m - 1) * rho). rho is unknown, so three values are shown. "
          "A cluster is everyone reached through one referral code, trainer or group.", ""]
    for key in ("android", "whatsapp_any", "interest_high"):
        if not byid[key]["n"]:
            L += [f"**{byid[key]['label']}**: no answers, nothing to show.", ""]
            continue
        v = se.cluster_view(byid[key], d["icc_sensitivity"])
        src = (f"observed: {v['clusters']} clusters" if v["observed"]
               else "no usable referral codes: hypothetical cluster sizes")
        L += [f"**{byid[key]['label']}**: {byid[key]['k']} / {byid[key]['n']} = {pct(byid[key]['p'])} ({src}); "
              f"naive exact interval {span(byid[key]['lo'], byid[key]['hi'])}", ""]
        L += table(["Mean cluster size", "rho", "Design effect", "95% interval", "± (pp)"],
                   [[f"{r['m']:.1f}", r["rho"], f"{r['deff']:.2f}", span(r["lo"], r["hi"]), f"{100 * r['margin']:.1f}"]
                    for r in v["rows"]])

    # ---- 6. segments
    L += ["## 6. Sellers and women planning to sell", ""]
    seg = se.segment_split(rows, meta, ["android", "whatsapp_any", "interest_high", "privacy_yes", "privacy_no"])
    L += table(["Estimate", "Group", "k / n", "Share", "95% interval", "Flag"],
               [[s["label"], s["group"], f"{s['k']} / {s['n']}", pct(s["p"]), span(s["lo"], s["hi"]),
                 "WIDE" if s["wide"] else ""] for s in seg if s["n"]])
    return "\n".join(L) + "\n"
