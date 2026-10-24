"""survey_forms: print the survey from the same JSON the analysis reads, plus a codebook.

Because both come from content/*.json, the questions people answer and the
questions the code analyses cannot drift apart.
"""
from __future__ import annotations

import csv
import re

TYPES = {"single": "Choose one", "multi": "Choose all that apply", "number": "Number",
         "money": "Amount in DZD", "text": "Free text", "hidden": "Hidden field (set by the link, not asked)"}
LANG_NAMES = {"en": "English", "fr": "Français", "ar": "العربية"}
PLACEHOLDER = re.compile(r"\[[^\]]+\]")


def placeholders(meta: dict) -> list[str]:
    """Every [BRACKETED] token left in the consent and closing texts."""
    found = []
    for key in ("consent", "closing"):
        for lang in meta["languages"]:
            found += PLACEHOLDER.findall(meta[key][lang])
    return sorted(set(found))


def _skip_note(q: dict, qmap: dict) -> str:
    cond = q.get("show_if")
    if not cond:
        return ""
    parent = qmap[cond["q"]]
    names = {o["code"]: o["en"] for o in parent["options"]}
    return f"Ask only if {cond['q']} is: " + " / ".join(names[c] for c in cond["in"]) + "."


def render_survey(meta: dict, questions: list[dict], lang: str) -> str:
    qmap = {q["id"]: q for q in questions}
    fill = ", ".join(placeholders(meta))
    L = [f"# {meta['title'][lang]}", "",
         f"> **DRAFT, do not field yet.** Fill in: {fill}. Price cells are placeholders "
         f"({', '.join(str(p) for p in meta['design']['price_cells_dzd'])} DZD). "
         + ("" if lang == "en" else "This translation needs native-speaker review and a pretest. ")
         + f"Version {meta['version']}, language: {LANG_NAMES[lang]}.", "",
         "## Consent", "", meta["consent"][lang], ""]
    section = None
    for q in questions:
        if q["section"] != section:
            section = q["section"]
            # Behavioural questions (including the task-pain ranking) must come
            # before the concept card to reduce solution-priming effects.
            if section == "M":
                L += ["## The idea", "", meta["concept_card"][lang], ""]
            L += [f"## {meta['sections'][section][lang]}", ""]
        L += [f"**{q['id']}.** {q['text'][lang]}", ""]
        L += [f"*{TYPES[q['type']]}" + (f", at most {q['max_select']}" if q.get("max_select") else "")
              + (f", between {q['range'][0]} and {q['range'][1]}" if q.get("range") else "")
              + ("" if q["required"] or q["type"] == "hidden" else ", optional") + "*", ""]
        marker = "( )" if q["type"] == "single" else "[ ]"
        L += [f"- {marker} {o[lang]}" for o in q.get("options", [])]
        if q.get("options"):
            L += [""]
        note = _skip_note(q, qmap)
        if note:
            L += [f"<!-- {note} -->", ""]
    L += ["## End", "", meta["closing"][lang], ""]
    text = "\n".join(L)
    if lang == "ar":
        text = '<div dir="rtl">\n\n' + text + "\n</div>\n"
    return text


def write_codebook(meta: dict, questions: list[dict], path: str) -> int:
    """One row per option (or per question without options). Returns the row count."""
    qmap = {q["id"]: q for q in questions}
    n = 0
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, lineterminator="\\n")
        w.writerow(["question_id", "section", "type", "required", "max_select", "ask_only_if",
                    "assumptions", "option_code", "label_en", "label_fr", "label_ar", "purpose"])
        for q in questions:
            base = [q["id"], q["section"], q["type"], q["required"], q.get("max_select", ""),
                    _skip_note(q, qmap), " ".join(q["assumption"])]
            if q.get("options"):
                for o in q["options"]:
                    w.writerow(base + [o["code"], o["en"], o["fr"], o["ar"], q["purpose"]])
                    n += 1
            else:
                w.writerow(base + ["", q["text"]["en"], q["text"]["fr"], q["text"]["ar"], q["purpose"]])
                n += 1
    return n
