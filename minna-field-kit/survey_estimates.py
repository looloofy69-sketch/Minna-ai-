"""survey_estimates: every number in the report comes from here (standard library only).

Each function takes the rows returned by survey_data.load_responses and returns
plain dicts. Intervals are exact (Clopper-Pearson) unless stated otherwise, and
they describe sampling noise inside the recruitment channel only.
"""
from __future__ import annotations

from collections import Counter

import minna_stats as ms

SELLERS = ("regular", "occasional")


def _counted(m: dict, exclude: set) -> list[str] | None:
    """Codes of one answer that count toward a denominator, or None if it does not."""
    if m["missing"] or m.get("invalid") or not m["codes"]:
        return None
    codes = [c for c in m["codes"] if c not in exclude]
    return codes or None


def tally(rows: list[dict], est: dict, keep=None) -> tuple[int, int, list]:
    """(k, n, refs): respondents whose answer holds any of est['codes'], respondents
    who answered (minus excluded codes), and the referral code of each of the latter."""
    k = n = 0
    refs = []
    exclude = set(est.get("exclude", []))
    for row in rows:
        if keep is not None and not keep(row):
            continue
        if est["q"] in row.get("_unexpected_questions", ()):
            continue
        codes = _counted(row[est["q"]], exclude)
        if codes is None:
            continue
        n += 1
        k += any(c in est["codes"] for c in codes)
        refs.append(row["ref"]["other"])
    return k, n, refs


def headline(rows: list[dict], meta: dict) -> list[dict]:
    conf, wide = meta["design"]["conf"], meta["design"]["wide_margin"]
    out = []
    for est in meta["estimates"]:
        k, n, refs = tally(rows, est)
        item = {**est, "k": k, "n": n, "refs": refs}
        item.update(ms.proportion(k, n, conf, wide) if n else {"p": None, "lo": None, "hi": None,
                                                               "margin": None, "wide": True})
        out.append(item)
    return out


def segment_split(rows: list[dict], meta: dict, ids: list[str]) -> list[dict]:
    """The same estimates for sellers and for women who only plan to sell."""
    groups = {"sellers": lambda r: r["S3"]["codes"][:1] and r["S3"]["codes"][0] in SELLERS,
              "planning": lambda r: r["S3"]["codes"] == ["planning"]}
    out = []
    for est in meta["estimates"]:
        if est["id"] not in ids:
            continue
        for name, keep in groups.items():
            k, n, _ = tally(rows, est, keep)
            item = {"id": est["id"], "label": est["label"], "group": name, "k": k, "n": n}
            item.update(ms.proportion(k, n, meta["design"]["conf"], meta["design"]["wide_margin"]) if n
                        else {"p": None, "lo": None, "hi": None, "margin": None, "wide": True})
            out.append(item)
    return out


def mean_cluster_size(item: dict) -> float | None:
    """Mean respondents per referral code, or None when fewer than 80% of the
    respondents behind this estimate carry a code (or there is only one code)."""
    refs = [r for r in item["refs"] if r]
    sizes = Counter(refs)
    if item["n"] and len(refs) >= 0.8 * item["n"] and len(sizes) >= 2:
        return len(refs) / len(sizes)
    return None


def cluster_view(item: dict, rhos: list[float], assumed_sizes=(5, 10, 20)) -> dict:
    """How the interval for one estimate widens if respondents came in clusters.
    Observed cluster size comes from the 'ref' codes when at least 80% of the
    respondents who answered have one; otherwise hypothetical sizes are shown."""
    k, n = item["k"], item["n"]
    refs = [r for r in item["refs"] if r]
    sizes = Counter(refs)
    m_obs = mean_cluster_size(item)
    observed = m_obs is not None
    mbars = [m_obs] if observed else list(assumed_sizes)
    rows = []
    for m in mbars:
        for rho in rhos:
            lo, hi = ms.wilson_deff(k, n, m, rho)
            rows.append({"m": m, "rho": rho, "deff": ms.design_effect(m, rho), "lo": lo, "hi": hi,
                         "margin": max(hi - k / n, k / n - lo)})
    return {"observed": observed, "clusters": len(sizes), "rows": rows,
            "max_share": (max(sizes.values()) / len(refs)) if observed else None}


def price_cells(rows: list[dict]) -> dict:
    """Stated acceptance by the price each respondent was shown, and an exact test
    between the lowest and the highest price (yes versus not-yes; 'maybe' counts as not-yes)."""
    cells: dict[float, Counter] = {}
    unpriced = 0
    for row in rows:
        if "W2" in row.get("_unexpected_questions", ()):
            continue
        m = row["W2"]
        if m["missing"] or m.get("invalid") or not m["codes"]:
            continue
        if row["_price"] is None:
            unpriced += 1
            continue
        cells.setdefault(row["_price"], Counter())[m["codes"][0]] += 1
    table = []
    for price in sorted(cells):
        c = cells[price]
        n = sum(c.values())
        item = {"price": price, "n": n, "yes": c["yes"], "maybe": c["maybe"], "no": c["no"]}
        item.update({"lo": ms.cp_interval(c["yes"], n)[0], "hi": ms.cp_interval(c["yes"], n)[1],
                     "p": c["yes"] / n})
        table.append(item)
    test = None
    if len(table) >= 2:
        lo, hi = table[0], table[-1]
        test = {"low": lo["price"], "high": hi["price"],
                "p_value": ms.fisher_exact(lo["yes"], lo["n"] - lo["yes"], hi["yes"], hi["n"] - hi["yes"])}
    return {"cells": table, "test": test, "unpriced": unpriced}


def refusal(rows: list[dict]) -> dict | None:
    """Pooled share of recalled parcels that were refused, resampling respondents."""
    pairs = [(r["O5b"]["number"], r["O5a"]["number"]) for r in rows
             if not ({"O5a", "O5b"} & r.get("_unexpected_questions", set()))
             and not r["O5a"].get("invalid") and not r["O5b"].get("invalid")
             and r["O5a"]["number"] is not None and r["O5b"]["number"] is not None]
    pairs = [(b, a) for b, a in pairs if a > 0]
    if not pairs:
        return None
    est, lo, hi = ms.bootstrap_ratio([b for b, _ in pairs], [a for _, a in pairs])
    return {"respondents": len(pairs), "parcels": sum(a for _, a in pairs),
            "refused": sum(b for b, _ in pairs), "ratio": est, "lo": lo, "hi": hi,
            "zero_refusals": sum(b == 0 for b, _ in pairs)}


def pick2_test(rows: list[dict], a: str, b: str) -> dict:
    """Do equally many respondents pick task a and task b? Exact McNemar on O6."""
    only_a = only_b = both = 0
    for row in rows:
        if "O6" in row.get("_unexpected_questions", ()):
            continue
        codes = _counted(row["O6"], set())
        if codes is None:
            continue
        in_a, in_b = a in codes, b in codes
        only_a += in_a and not in_b
        only_b += in_b and not in_a
        both += in_a and in_b
    return {"a": a, "b": b, "only_a": only_a, "only_b": only_b, "both": both,
            "p_value": ms.mcnemar_exact(only_a, only_b)}


def top_pains(items: list[dict]) -> list[dict]:
    """Single-task pain estimates, most frequent first (the derived order-flow
    estimate is excluded)."""
    singles = [i for i in items if i["id"].startswith("pain_") and i["id"] != "pain_orderflow" and i["n"]]
    return sorted(singles, key=lambda i: (-i["p"], i["id"]))


def _verdict(lower: float, upper: float, thr: float) -> str:
    return ("PASS: Android share is at least the threshold" if lower >= thr else
            "FAIL: Android share is below the threshold" if upper < thr else
            "INCONCLUSIVE: the threshold lies inside the one-sided bounds")


def android_decision(item: dict, design: dict, rho: float = 0.05) -> dict:
    """One-sided decision aid for D2 against a threshold fixed BEFORE fielding.
    'status' treats respondents as independent. When referral codes show clusters,
    'clustered_status' repeats it with Wilson bounds at the effective sample size
    (one-sided 95% = Wilson at 90% two-sided); use that one for a referral sample.
    The Wilson bounds are approximate and rho is an assumption, not an estimate."""
    k, n, thr = item["k"], item["n"], design["android_lower_bound"]
    if not n:
        return {"status": "NO DATA", "threshold": thr}
    lower, upper = ms.cp_lower_one_sided(k, n), ms.cp_upper_one_sided(k, n)
    out = {"status": _verdict(lower, upper, thr), "threshold": thr, "lower": lower, "upper": upper,
           "k": k, "n": n}
    m = mean_cluster_size(item)
    if m is not None and m > 1:
        lo, hi = ms.wilson_deff(k, n, m, rho, conf=0.90)
        out.update({"m_bar": m, "rho": rho, "clustered_lower": lo, "clustered_upper": hi,
                    "clustered_status": _verdict(lo, hi, thr)})
    return out


def sample_check(rows: list[dict], meta: dict) -> dict:
    """Does the sample reach the planned precision? Reports the exact worst-case margin."""
    n = len(rows)
    sellers = sum(1 for r in rows if r["S3"]["codes"][:1] and r["S3"]["codes"][0] in SELLERS)
    target = meta["design"]["margin_target"]
    out = {"n": n, "sellers": sellers, "target": target, "n_needed": meta["design"]["n_min_exact"]}
    for key, count in (("all", n), ("sellers", sellers)):
        out[key] = {"n": count, "margin": ms.worst_case_margin(count) if count >= 2 else None}
        out[key]["meets_target"] = bool(count >= 2 and out[key]["margin"] <= target)
    return out
