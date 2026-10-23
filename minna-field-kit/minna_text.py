"""minna_text: match survey answers written in English, French or Arabic to codes.

Standard library only. Nothing is guessed: a header or value that cannot be
matched is returned as unmatched so the report can show it. A silent drop would
bias the estimates without anyone noticing.
"""
from __future__ import annotations

import difflib
import re
import unicodedata

LANGS = ("en", "fr", "ar")

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
# Folds applied after NFKD. ۀ decomposes under NFKD into ە plus a mark that is then stripped,
# so the key that has to be mapped is ە (an entry for ۀ itself would never be reached).
_ARABIC_SPELLING = str.maketrans({"ى": "ي", "ة": "ه", "ی": "ي", "ک": "ك", "ھ": "ه", "ە": "ه"})
_NOT_WORD = re.compile(r"[^\w\s]", re.UNICODE)
_SEPARATORS = re.compile(r"[,;|\n،؛]+")
_MISSING = {"", "nan", "null", "n/a", "na"}
_CURRENCY = re.compile(r"\s*(?:da|dzd|dinars?|دج|د\.ج|دينار|دنانير)\s*$", re.IGNORECASE)


def norm(text) -> str:
    """Canonical matching form. Lower-cases, strips Latin accents and Arabic vowel
    and hamza marks (so أ إ آ become ا), removes tatweel and invisible format
    characters, folds ى to ي and ة to ه, turns Arabic-Indic digits into ASCII
    digits, replaces punctuation (including apostrophes) with spaces and
    collapses whitespace. For matching only, never for display."""
    if text is None:
        return ""
    s = unicodedata.normalize("NFKD", str(text)).translate(_DIGITS)
    s = "".join(ch for ch in s if unicodedata.category(ch) not in ("Mn", "Cf"))
    s = s.replace("ـ", "").translate(_ARABIC_SPELLING).casefold()
    s = s.replace("œ", "oe").replace("æ", "ae")
    return " ".join(_NOT_WORD.sub(" ", s).split())


def is_missing(raw) -> bool:
    return raw is None or str(raw).strip().lower() in _MISSING


def parse_number(text, money: bool = False):
    """float or None. Accepts Arabic-Indic digits, a trailing currency word (DA, DZD,
    دج, دينار) and a decimal comma. With money=True, '1 500', '1.500' and '1,500'
    are thousands groups (every group after the first has exactly three digits);
    otherwise '1.500' means 1.5."""
    if is_missing(text):
        return None
    s = unicodedata.normalize("NFKC", str(text)).translate(_DIGITS)
    s = s.translate({0x066B: ".", 0x066C: ",", 0x00A0: " ", 0x202F: " "}).strip()
    s = _CURRENCY.sub("", s).strip()
    if money and re.fullmatch(r"\d{1,3}(?:[ .,]\d{3})+", s):
        return float(re.sub(r"[ .,]", "", s))
    if re.fullmatch(r"\d+", s):
        return float(s)
    if re.fullmatch(r"\d+[.,]\d+", s):
        return float(s.replace(",", "."))
    return None


class Codebook:
    """Lookup tables built from the survey content (a list of question dicts)."""

    def __init__(self, questions: list[dict]):
        self.questions = {q["id"]: q for q in questions}
        self._header_ids = {norm(qid): qid for qid in self.questions}
        self._header_text: dict[str, str] = {}
        self._price_templates: list[tuple[str, str, str]] = []
        self._options: dict[str, dict[str, str]] = {}
        for q in questions:
            for lang in LANGS:
                raw_text = q["text"].get(lang, "")
                if "{PRICE}" in raw_text:
                    left, right = raw_text.split("{PRICE}", 1)
                    self._price_templates.append((q["id"], norm(left), norm(right)))
                t = norm(raw_text)
                if t:
                    if self._header_text.setdefault(t, q["id"]) != q["id"]:
                        raise ValueError(f"two questions share the text {t!r}")
            table: dict[str, str] = {}
            for opt in q.get("options", []):
                keys = [opt["code"]] + [opt.get(lang, "") for lang in LANGS] + opt.get("syn", [])
                for key in filter(None, map(norm, keys)):
                    if table.setdefault(key, opt["code"]) != opt["code"]:
                        raise ValueError(
                            f"{q['id']}: {key!r} matches both {table[key]!r} and {opt['code']!r}")
            self._options[q["id"]] = table

    # ---- headers -------------------------------------------------------
    def price_in_header(self, header) -> tuple[str, float] | None:
        """For a question whose text holds {PRICE}: (question id, price) when the
        header is that text with a number in place of the placeholder."""
        h = norm(header)
        for qid, left, right in self._price_templates:
            if len(h) > len(left) + len(right) and h.startswith(left) and h.endswith(right):
                middle = h[len(left): len(h) - len(right)].replace(" ", "")
                if middle.isdigit():
                    return qid, float(middle)
        return None

    def map_header(self, header) -> tuple[str | None, str]:
        """(question id or None, how it matched: id, text, price-template, prefix, none)."""
        h = norm(header)
        if h in self._header_ids:
            return self._header_ids[h], "id"
        if h in self._header_text:
            return self._header_text[h], "text"
        hit = self.price_in_header(header)
        if hit:
            return hit[0], "price-template"
        hits = {qid for t, qid in self._header_text.items()
                if len(t) >= 12 and len(h) >= 12 and (h.startswith(t) or t.startswith(h))}
        if len(hits) == 1:
            return hits.pop(), "prefix"
        return None, "none"

    # ---- values --------------------------------------------------------
    def map_value(self, qid: str, raw) -> dict:
        """{'missing', 'codes', 'other', 'unmapped', 'number', 'near'} for one cell.
        'near' lists (text, code) pairs where free text that went to 'other' is
        suspiciously close to a real option, i.e. probably a misspelled label."""
        q = self.questions[qid]
        out = {"missing": False, "codes": [], "other": None, "unmapped": [], "number": None,
               "near": []}
        if is_missing(raw):
            out["missing"] = True
            return out
        kind = q["type"]
        if kind in ("number", "money") or q.get("numeric"):
            val = parse_number(raw, money=(kind != "number"))
            if val is None:
                out["unmapped"].append(str(raw))
            out["number"] = val
            return out
        if kind in ("text", "hidden"):
            out["other"] = str(raw).strip()
            return out
        table = self._options[qid]
        tokens = _SEPARATORS.split(str(raw)) if kind == "multi" else [str(raw)]
        has_other = any(o["code"] == "other" for o in q.get("options", []))
        for tok in (t.strip() for t in tokens):
            if not tok:
                continue
            code = table.get(norm(tok))
            if code is not None:
                if code not in out["codes"]:
                    out["codes"].append(code)
            elif has_other:
                if "other" not in out["codes"]:
                    out["codes"].append("other")
                out["other"] = tok if out["other"] is None else f"{out['other']} | {tok}"
                close = difflib.get_close_matches(norm(tok), list(table), n=1, cutoff=0.8)
                if close:
                    out["near"].append((tok, table[close[0]]))
            else:
                out["unmapped"].append(tok)
        return out
