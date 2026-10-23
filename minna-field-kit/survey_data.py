"""survey_data: load the survey content and a responses CSV, map answers to codes,
audit the data. Standard library only.

Rule: nothing is dropped silently. Every excluded row, unmatched header,
unmapped value, skip-logic violation and impossible number is counted in the
audit, and the report prints it before any estimate.
"""
from __future__ import annotations

import csv
import glob
import json
import os
from collections import Counter

import minna_text as mt

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(HERE, "content")


class DataError(ValueError):
    """The file cannot be analysed responsibly (for example no consent column)."""


def load_content(content_dir: str = CONTENT_DIR) -> tuple[dict, list[dict]]:
    with open(os.path.join(content_dir, "meta.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    questions: list[dict] = []
    for path in sorted(glob.glob(os.path.join(content_dir, "part*.json"))):
        with open(path, encoding="utf-8") as fh:
            questions.extend(json.load(fh)["questions"])
    return meta, questions


def is_expected(qid: str, row: dict, qmap: dict) -> bool:
    """Was this respondent supposed to see the question, given her earlier answers?"""
    cond = qmap[qid].get("show_if")
    if not cond:
        return True
    if not is_expected(cond["q"], row, qmap):
        return False
    parent = row[cond["q"]]
    return (not parent["missing"]) and any(c in cond["in"] for c in parent["codes"])


def answered(m: dict) -> bool:
    return not m["missing"] and not m.get("invalid") and bool(
        m["codes"] or m["number"] is not None or m["other"])


def load_responses(path: str, questions: list[dict], assume_screened: bool = False):
    """Return (rows, audit). rows holds only respondents who consented and are adults;
    each row maps question id -> mapped answer (see Codebook.map_value) plus
    '_price' (the price cell seen in W2) and '_line' (line number in the file)."""
    cb = mt.Codebook(questions)
    qmap = {q["id"]: q for q in questions}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        table = [r for r in csv.reader(fh)]
    if len(table) < 1:
        raise DataError("the file is empty")
    header, body = table[0], table[1:]

    columns, unmatched, methods = [], [], Counter()
    for i, h in enumerate(header):
        qid, how = cb.map_header(h)
        if qid is None:
            unmatched.append(h)
            continue
        hit = cb.price_in_header(h)
        columns.append((i, qid, hit[1] if hit else None))
        methods[how] += 1
    present = {qid for _, qid, _ in columns}
    dup = sorted(qid for qid, c in Counter(q for _, q, _ in columns).items()
                 if c > 1 and qid != "W2")
    if not {"S1", "S2"} <= present and not assume_screened:
        raise DataError("columns for S1 (consent) and S2 (18 or older) are missing; "
                        "refusing to analyse data whose consent cannot be checked "
                        "(use assume_screened=True only if both were enforced upstream)")

    audit = {"file": os.path.basename(path), "rows_read": 0, "columns": len(header),
             "unmatched_headers": unmatched, "header_methods": dict(methods),
             "duplicate_columns": dup,
             "questions_without_column": sorted(set(qmap) - present),
             "excluded": Counter(), "issues": Counter(), "questions": {}}
    rows = []
    for line_no, raw in enumerate(body, start=2):
        if not any(c.strip() for c in raw):
            continue
        audit["rows_read"] += 1
        row = {qid: cb.map_value(qid, None) for qid in qmap}
        price_from_header = None
        for i, qid, price in columns:
            m = cb.map_value(qid, raw[i] if i < len(raw) else None)
            if row[qid]["missing"] and not m["missing"]:
                row[qid] = m
                if price is not None:
                    price_from_header = price
        row["_line"] = line_no
        row["_price"] = row["price_cell"]["number"] if row["price_cell"]["number"] is not None \
            else price_from_header
        if not assume_screened:
            if row["S1"]["codes"] != ["yes"]:
                audit["excluded"]["no consent (S1 not yes)"] += 1
                continue
            if row["S2"]["codes"] != ["yes"]:
                audit["excluded"]["not confirmed 18 or older (S2 not yes)"] += 1
                continue
        rows.append(row)

    _validate(rows, qmap, audit)
    audit["included"] = len(rows)
    audit["excluded"] = dict(audit["excluded"])
    audit["issues"] = dict(audit["issues"])
    _per_question(rows, qmap, audit)
    return rows, audit


def _validate(rows: list[dict], qmap: dict, audit: dict) -> None:
    issues = audit["issues"]
    for row in rows:
        for qid, q in qmap.items():
            m = row[qid]
            if "range" in q and m["number"] is not None:
                lo, hi = q["range"]
                if not lo <= m["number"] <= hi:
                    issues[f"{qid}: number outside {lo}-{hi}"] += 1
                    m["invalid"], m["number"] = True, None
            limit = q.get("max_select")
            if limit and len(m["codes"]) > limit:
                issues[f"{qid}: more than {limit} choices (answer ignored)"] += 1
                m["invalid"], m["codes"] = True, []
        a, b = row["O5a"], row["O5b"]
        if a["number"] is not None and b["number"] is not None and b["number"] > a["number"]:
            issues["O5b greater than O5a (both ignored)"] += 1
            for m in (a, b):
                m["invalid"], m["number"] = True, None
        m2 = row["M2"]["codes"]
        if "allow_all" in m2 and len(m2) > 1:
            issues["M2: 'allow all' together with refusals (kept, contradictory)"] += 1
        if row["W2"]["codes"] and row["_price"] is None:
            issues["W2 answered but the price cell is unknown (excluded from price comparison)"] += 1


def _per_question(rows: list[dict], qmap: dict, audit: dict) -> None:
    for qid, q in qmap.items():
        if q["type"] == "hidden":
            continue
        s = {"expected": 0, "answered": 0, "unexpected_answers": 0,
             "unmapped": Counter(), "other": Counter(), "near": Counter()}
        for row in rows:
            m = row[qid]
            exp = is_expected(qid, row, qmap)
            ans = answered(m)
            s["expected"] += exp
            s["answered"] += exp and ans
            s["unexpected_answers"] += (not exp) and ans
            s["unmapped"].update(m["unmapped"])
            if m["other"] and q["type"] not in ("text",):
                s["other"][m["other"]] += 1
            s["near"].update(f"{t!r} looks like {c!r}" for t, c in m["near"])
        s["nonresponse"] = s["expected"] - s["answered"]
        audit["questions"][qid] = s
