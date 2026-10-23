"""survey_synth: synthetic survey responses with KNOWN ground truth.

These rows describe nobody. They exist so that tests can prove the pipeline
recovers answers that were planted, through three languages and messy formatting.
truth() derives every headline estimate analytically from the generating model.
"""
from __future__ import annotations

import csv
import math
import random
import unicodedata

import survey_data as sd

SELLERS = ("regular", "occasional")
ASKED_CONCEPT = ("regular", "occasional", "planning")

P = {
    "consent": 0.97, "adult": 0.985, "missing": 0.03,
    "lang": {"en": 0.30, "fr": 0.40, "ar": 0.30},
    "S3": {"regular": 0.45, "occasional": 0.30, "planning": 0.15, "no": 0.10},
    "P1": {"a18_24": 0.20, "a25_34": 0.40, "a35_44": 0.25, "a45_plus": 0.10, "pnts": 0.05},
    "P2": {"big_city": 0.45, "town": 0.35, "rural": 0.15, "pnts": 0.05},
    "P3": {"training": 0.25, "social_group": 0.30, "chat_group": 0.20, "friend": 0.20, "other": 0.05},
    "D1": {"android": 0.82, "iphone": 0.08, "basic": 0.07, "shared": 0.03},
    "D2": {"several_daily": 0.70, "daily": 0.18, "weekly": 0.08, "rarely": 0.04},
    "D3": {"never": 0.55, "sometimes": 0.30, "often": 0.10, "pnts": 0.05},
    "D4": {"none": 0.50, "days_1_2": 0.20, "days_3plus": 0.20, "unknown": 0.10},
    "C2": {"whatsapp": 0.62, "facebook": 0.15, "instagram": 0.15, "tiktok": 0.02,
           "viber": 0.02, "phone": 0.03, "other": 0.01},
    "C1_extra": {"whatsapp": 0.50, "facebook": 0.45, "instagram": 0.30, "tiktok": 0.08,
                 "viber": 0.10, "phone": 0.40, "other": 0.03},
    "C3": {"darija_arabic": 0.50, "darija_latin": 0.55, "french": 0.60, "msa": 0.25,
           "english": 0.10, "tamazight": 0.08, "other": 0.02},
    "C4": {"paper": 0.35, "phone_notes": 0.40, "spreadsheet": 0.15, "app": 0.05,
           "chat": 0.30, "nothing": 0.10},
    "O1": {"w0_5": 0.30, "w6_20": 0.40, "w21_50": 0.20, "w51_plus": 0.10},
    "O2": {"hand": 0.50, "courier": 0.60, "post": 0.10, "driver": 0.15, "other": 0.03},
    "O3": {"yalidine": 0.45, "maystro": 0.30, "other": 0.35},
    "O4": {"cod_mostly": 0.55, "mixed": 0.25, "prepaid_mostly": 0.15, "other": 0.05},
    "O5_propensity": (1.5, 8.5),
    "O6_k": {1: 0.4, 2: 0.6},
    "O6_w": {"replying": 3.0, "confirming": 2.0, "packing": 1.0, "parcels": 2.5,
             "tracking": 2.0, "records": 1.5, "marketing": 1.5, "other": 0.5},
    "M1": {"1": 0.10, "2": 0.12, "3": 0.25, "4": 0.28, "5": 0.25},
    "M2_allow_all": 0.15,
    "M2": {"send_messages": 0.25, "create_parcels": 0.15, "see_numbers": 0.35,
           "handle_money": 0.45, "post_social": 0.30, "read_contacts": 0.40},
    "M3": {"yes": 0.25, "depends": 0.35, "no": 0.30, "unknown": 0.10},
    "M4_nobody": 0.08,
    "M4": {"dz_company": 0.55, "foreign_company": 0.20, "state": 0.35, "association": 0.30},
    "W3": {"per_job": 0.45, "monthly": 0.35, "unsure": 0.20},
    "W2": {500: {"yes": 0.45, "maybe": 0.25, "no": 0.30},
           1000: {"yes": 0.25, "maybe": 0.25, "no": 0.50}},
}
FREE_TEXT = {"C1": "Telegram", "C2": "Telegram", "C3": "Italiano", "O2": "Aramex",
             "O3": "Aramex", "O4": "Baridi", "P3": "Radio"}


# --------------------------------------------------------------------------
# Ground truth, derived analytically from P
# --------------------------------------------------------------------------

def _nonempty(p: dict) -> dict:
    """Marginals of independent Bernoulli choices conditioned on at least one choice."""
    none = math.prod(1 - v for v in p.values())
    return {k: v / (1 - none) for k, v in p.items()}


def _top2_any(tasks: list[str]) -> float:
    """P(the chosen set contains at least one of `tasks`), pick-1 or pick-2 without
    replacement with weights O6_w."""
    w = P["O6_w"]
    total = sum(w.values())
    hit_first = sum(w[t] for t in tasks) / total
    miss_both = sum(w[u] / total * sum(w[v] for v in w if v not in tasks and v != u) / (total - w[u])
                    for u in w if u not in tasks)
    return P["O6_k"][1] * hit_first + P["O6_k"][2] * (1 - miss_both)


def _top2_share(task: str) -> float:
    return _top2_any([task])


def truth() -> dict:
    c3, o2 = _nonempty(P["C3"]), _nonempty(P["O2"])
    m2 = _nonempty(P["M2"])
    m4 = _nonempty(P["M4"])
    a = 1 - P["M2_allow_all"]
    ch = lambda c: P["C2"][c] + (1 - P["C2"][c]) * P["C1_extra"][c]  # noqa: E731
    t = {
        "android": P["D1"]["android"],
        "smartphone": P["D1"]["android"] + P["D1"]["iphone"],
        "daily_internet": P["D2"]["several_daily"] + P["D2"]["daily"],
        "shared_phone": (P["D3"]["sometimes"] + P["D3"]["often"]) / (1 - P["D3"]["pnts"]),
        "outage_3plus": P["D4"]["days_3plus"] / (1 - P["D4"]["unknown"]),
        "whatsapp_any": ch("whatsapp"), "facebook_any": ch("facebook"), "instagram_any": ch("instagram"),
        "whatsapp_main": P["C2"]["whatsapp"],
        "darija_arabic": c3["darija_arabic"], "darija_latin": c3["darija_latin"],
        "french": c3["french"], "msa": c3["msa"], "tamazight": c3["tamazight"],
        "high_volume": P["O1"]["w21_50"] + P["O1"]["w51_plus"],
        "courier_use": o2["courier"],
        "cod_mostly": P["O4"]["cod_mostly"],
        "interest_high": P["M1"]["4"] + P["M1"]["5"],
        "refuse_money": a * m2["handle_money"], "refuse_numbers": a * m2["see_numbers"],
        "refuse_send": a * m2["send_messages"],
        "privacy_yes": P["M3"]["yes"], "privacy_no": P["M3"]["no"],
        "trust_dz_company": (1 - P["M4_nobody"]) * m4["dz_company"],
        "trust_foreign": (1 - P["M4_nobody"]) * m4["foreign_company"],
        "trust_state": (1 - P["M4_nobody"]) * m4["state"],
        "trust_association": (1 - P["M4_nobody"]) * m4["association"],
        "trust_nobody": P["M4_nobody"],
        "per_job": P["W3"]["per_job"],
    }
    for task in ("replying", "confirming", "packing", "parcels", "tracking", "records", "marketing"):
        t[f"pain_{task}"] = _top2_share(task)
    t["pain_orderflow"] = _top2_any(["confirming", "parcels", "tracking"])
    return {"estimates": t, "wtp_yes": {str(k): v["yes"] for k, v in P["W2"].items()},
            "refusal_ratio": P["O5_propensity"][0] / sum(P["O5_propensity"])}


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------

def _pick(rng: random.Random, dist: dict):
    r, acc = rng.random(), 0.0
    for k, v in dist.items():
        acc += v
        if r < acc:
            return k
    return k


def _multi(rng: random.Random, p: dict) -> list[str]:
    while True:
        chosen = [k for k, v in p.items() if rng.random() < v]
        if chosen:
            return chosen


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _noisy(rng: random.Random, text: str, lang: str) -> str:
    r = rng.random()
    if r < 0.15:
        text = text.upper()
    elif r < 0.30:
        text = text.lower()
    if lang == "fr" and rng.random() < 0.25:
        text = _strip_accents(text)
    if lang == "ar" and rng.random() < 0.25:
        text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    return f"  {text} " if rng.random() < 0.10 else text


def _digits(rng: random.Random, n: int, lang: str) -> str:
    s = str(n)
    return s.translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")) if lang == "ar" and rng.random() < 0.5 else s


def _money(rng: random.Random, amount: int, lang: str) -> str:
    if amount < 1000:
        return rng.choice([str(amount), f"{amount} DA"])
    forms = [str(amount), f"{amount:,}".replace(",", " "), f"{amount:,}".replace(",", "."),
             f"{amount} DA", f"{amount} DZD"]
    if lang == "ar":
        forms += [f"{amount} دج", _digits(rng, amount, "ar")]
    return rng.choice(forms)


def generate(n: int, seed: int = 1, headers: str = "text", price_layout: str = "column",
             include_price_cell: bool = True, path: str | None = None,
             content_dir: str = sd.CONTENT_DIR):
    """Return (table, planted). `table` is header + rows (also written as UTF-8-with-BOM
    CSV when `path` is given). `planted[i]` records, for data row i, what was planted in
    each answered question: {'codes': [...]} or {'number': x} or {'missing': True}.
    headers: 'text' (English question text), 'id', or 'mixed' (each column in a random
    language). price_layout: 'column' (one W2 column + price_cell) or 'headers' (one W2
    column per price, filled only for the price that respondent saw)."""
    rng = random.Random(seed)
    _, questions = sd.load_content(content_dir)
    qmap = {q["id"]: q for q in questions}
    prices = sorted(P["W2"])
    clusters = [f"G{i:02d}" for i in range(1, 11)]

    def label(qid: str, code: str, lang: str) -> str:
        if code == "other" and qid in FREE_TEXT and rng.random() < 0.5:
            return FREE_TEXT[qid]
        for o in qmap[qid]["options"]:
            if o["code"] == code:
                return _noisy(rng, o[lang], lang)
        raise KeyError((qid, code))

    table, planted = [], []
    for _ in range(n):
        lang = _pick(rng, P["lang"])
        sep = rng.choice([", ", "; ", " | ", "،" if lang == "ar" else ", "])
        a: dict[str, str] = {}
        plant: dict[str, dict] = {}
        w2 = None

        def cell(qid, text, **info):
            """Record one answer, which item non-response may blank (optional questions only)."""
            if not qmap[qid]["required"] and rng.random() < P["missing"]:
                a[qid], plant[qid] = "", {"missing": True}
            else:
                a[qid], plant[qid] = text, info

        def one(qid, code):
            cell(qid, label(qid, code, lang), codes=[code])

        def many(qid, codes):
            cell(qid, sep.join(label(qid, c, lang) for c in codes), codes=sorted(codes))

        def finish():
            table.append((a, w2))
            planted.append(plant)

        consent = rng.random() < P["consent"]
        a["S1"], plant["S1"] = label("S1", "yes" if consent else "no", lang), {"codes": ["yes" if consent else "no"]}
        if not consent:
            finish()
            continue
        adult = rng.random() < P["adult"]
        a["S2"], plant["S2"] = label("S2", "yes" if adult else "no", lang), {"codes": ["yes" if adult else "no"]}
        if not adult:
            finish()
            continue
        s3 = _pick(rng, P["S3"])
        one("S3", s3)
        for qid in ("P1", "P2", "P3", "D1", "D2", "D3", "D4"):
            one(qid, _pick(rng, P[qid]))
        if s3 in SELLERS:
            main = _pick(rng, P["C2"])
            many("C1", sorted({main} | {k for k, v in P["C1_extra"].items() if rng.random() < v}))
            one("C2", main)
            many("C3", _multi(rng, P["C3"]))
            many("C4", _multi(rng, P["C4"]))
            one("O1", _pick(rng, P["O1"]))
            o2 = _multi(rng, P["O2"])
            many("O2", o2)
            if "courier" in o2:
                many("O3", _multi(rng, P["O3"]))
                count = rng.randint(5, 20)
                prop = rng.betavariate(*P["O5_propensity"])
                refused = sum(rng.random() < prop for _i in range(count))
                cell("O5a", _digits(rng, count, lang), number=float(count))
                cell("O5b", _digits(rng, refused, lang), number=float(refused))
            one("O4", _pick(rng, P["O4"]))
            pool, tasks = dict(P["O6_w"]), []
            for _i in range(_pick(rng, P["O6_k"])):
                t = _pick(rng, {x: w / sum(pool.values()) for x, w in pool.items()})
                tasks.append(t)
                del pool[t]
            many("O6", tasks)
        if s3 in ASKED_CONCEPT:
            one("M1", _pick(rng, P["M1"]))
            many("M2", ["allow_all"] if rng.random() < P["M2_allow_all"] else _multi(rng, P["M2"]))
            one("M3", _pick(rng, P["M3"]))
            many("M4", ["nobody"] if rng.random() < P["M4_nobody"] else _multi(rng, P["M4"]))
        if s3 in SELLERS:
            amount = int(round(math.exp(rng.gauss(math.log(1500), 0.6)) / 50) * 50)
            cell("W1", _money(rng, amount, lang), number=float(amount))
            one("W3", _pick(rng, P["W3"]))
            price = rng.choice(prices)
            answer = _pick(rng, P["W2"][price])
            if rng.random() < P["missing"]:
                plant["W2"] = {"missing": True, "price": price}
            else:
                w2 = (price, label("W2", answer, lang))
                plant["W2"] = {"codes": [answer], "price": price}
            if include_price_cell:
                a["price_cell"], plant["price_cell"] = str(price), {"number": float(price)}
        a["ref"] = rng.choice(clusters)
        finish()

    cols = [q["id"] for q in questions if q["id"] not in ("W2",)]
    col_lang = {c: rng.choice(["en", "fr", "ar"]) for c in cols}

    def head(qid: str) -> str:
        if headers == "id" or qid in ("ref", "price_cell"):
            return qid
        return qmap[qid]["text"][col_lang[qid] if headers == "mixed" else "en"]

    w2_text = qmap["W2"]["text"]["en"]
    out = [["Timestamp"] + [head(c) for c in cols]
           + ([w2_text.replace("{PRICE}", str(p)) for p in prices] if price_layout == "headers" else [w2_text])]
    for i, (a, w2) in enumerate(table):
        row = [f"2026-10-0{1 + i % 9} 10:{i % 60:02d}"] + [a.get(c, "") for c in cols]
        if price_layout == "headers":
            row += [w2[1] if w2 and w2[0] == p else "" for p in prices]
        else:
            row += [w2[1] if w2 else ""]
        out.append(row)
    if path:
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            csv.writer(fh).writerows(out)
    return out, planted
