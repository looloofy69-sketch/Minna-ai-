"""Tests for minna_text: normalisation, number parsing, header and value mapping."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import minna_text as mt  # noqa: E402


def opt(code, en, fr, ar, **kw):
    return {"code": code, "en": en, "fr": fr, "ar": ar, **kw}


QUESTIONS = [
    {"id": "C1", "type": "multi",
     "text": {"en": "Which apps do you use with customers?",
              "fr": "Quelles applications utilisez-vous avec vos clientes ?",
              "ar": "ما التطبيقات التي تستخدمينها مع الزبائن؟"},
     "options": [opt("whatsapp", "WhatsApp", "WhatsApp", "واتساب"),
                 opt("facebook", "Facebook", "Facebook", "فيسبوك"),
                 opt("instagram", "Instagram", "Instagram", "إنستغرام"),
                 opt("other", "Other", "Autre", "أخرى")]},
    {"id": "D1", "type": "single",
     "text": {"en": "Which phone do you use?", "fr": "Quel téléphone utilisez-vous ?",
              "ar": "أي هاتف تستخدمين؟"},
     "options": [opt("android", "Android smartphone", "Smartphone Android", "هاتف أندرويد"),
                 opt("iphone", "iPhone", "iPhone", "آيفون"),
                 opt("none", "None of these", "Aucun de ceux-ci", "لا شيء مما سبق")]},
    {"id": "S2", "type": "single",
     "text": {"en": "Are you 18 or older?", "fr": "Avez-vous 18 ans ou plus ?",
              "ar": "هل عمرك 18 سنة أو أكثر؟"},
     "options": [opt("yes", "Yes", "Oui", "نعم", syn=["iyeh", "wah"]),
                 opt("no", "No", "Non", "لا", syn=["la"])]},
    {"id": "M1", "type": "single",
     "text": {"en": "How interested are you in such an assistant?",
              "fr": "Cet assistant vous intéresse-t-il ?", "ar": "ما مدى اهتمامك بهذا المساعد؟"},
     "options": [opt(str(i), f"{i} out of 5", f"{i} sur 5", f"{i} من 5") for i in range(1, 6)]},
    {"id": "W1", "type": "money",
     "text": {"en": "How much do you spend per month on phone and internet (DZD)?",
              "fr": "Combien dépensez-vous par mois en téléphone et internet (DZD) ?",
              "ar": "كم تنفقين شهريا على الهاتف والانترنت (دج)؟"}},
    {"id": "O5", "type": "number",
     "text": {"en": "How many of your last 20 parcels were refused?",
              "fr": "Combien de vos 20 derniers colis ont été refusés ?",
              "ar": "كم من آخر 20 طردا تم رفضه؟"}},
]
CB = mt.Codebook(QUESTIONS)


class Normalisation(unittest.TestCase):
    def test_equivalent_spellings_collapse(self):
        same = [("Été", "ete"), ("أندرويد", "اندرويد"), ("إنستغرام", "انستغرام"), ("آيفون", "ايفون"),
                ("مدينة", "مدينه"), ("نَعَمْ", "نعم"), ("نعـــم", "نعم"), ("٣٠", "30"), ("۳۰", "30"),
                ("１２", "12"), ("‏نعم‏", "نعم"), ("ن‌عم", "نعم"),
                ("aujourd’hui", "aujourd'hui"), ("WhatsApp", "whatsapp"), ("a b", "a b"),
                ("cœur", "coeur"), ("ﻻ", "لا"), ("  Quel   téléphone ?  ", "quel telephone"),
                ("ﺑﻌﺪ", "بعد"), ("مؤسسة", "موسسه"),
                # letters whose variants must fold (alef maksura, Persian yeh, kaf, heh forms)
                ("على", "علي"), ("علی", "علي"), ("کتاب", "كتاب"), ("ھذا", "هذا"), ("ۀ", "ه"),
                # punctuation separates words instead of deleting them
                ("a/b", "a b"), ("l'adresse", "l adresse"), ("tracking / suivi", "tracking suivi")]
        for a, b in same:
            self.assertEqual(mt.norm(a), mt.norm(b), (a, b))

    def test_different_words_stay_different(self):
        for a, b in [("نعم", "لا"), ("oui", "non"), ("yes", "no"), ("1 sur 5", "2 sur 5"), ("ab", "a b")]:
            self.assertNotEqual(mt.norm(a), mt.norm(b), (a, b))

    def test_none_and_empty(self):
        self.assertEqual(mt.norm(None), "")
        self.assertEqual(mt.norm("   "), "")

    def test_missing_detection_does_not_swallow_a_real_answer_called_none(self):
        for raw in (None, "", "  ", "NaN", "null", "N/A"):
            self.assertTrue(mt.is_missing(raw), raw)
        self.assertFalse(mt.is_missing("None"))
        self.assertFalse(mt.is_missing("0"))


class Numbers(unittest.TestCase):
    def test_plain_and_arabic_digits(self):
        for raw, want in [("12", 12.0), ("١٥", 15.0), ("۳۰", 30.0), (" 7 ", 7.0), ("0", 0.0)]:
            self.assertEqual(mt.parse_number(raw), want, raw)

    def test_decimals(self):
        self.assertEqual(mt.parse_number("1,5"), 1.5)
        self.assertEqual(mt.parse_number("2.25"), 2.25)
        self.assertEqual(mt.parse_number("1.500"), 1.5)          # not money: a decimal
        self.assertEqual(mt.parse_number("٢٫٥"), 2.5)             # Arabic decimal separator

    def test_money_thousands_groups(self):
        for raw in ("1 500 DA", "1.500", "1,500", "1 500", "١٥٠٠ دج", "1500 dzd", "1 500"):
            self.assertEqual(mt.parse_number(raw, money=True), 1500.0, raw)
        self.assertEqual(mt.parse_number("2.5", money=True), 2.5)   # one digit after the point
        self.assertEqual(mt.parse_number("12 345 678", money=True), 12345678.0)
        self.assertEqual(mt.parse_number("٣٠٠٠ دينار", money=True), 3000.0)
        # two digits after a separator is a decimal, not a thousands group
        self.assertEqual(mt.parse_number("1,50", money=True), 1.5)
        self.assertEqual(mt.parse_number("12,34", money=True), 12.34)
        self.assertIsNone(mt.parse_number("1 50", money=True))

    def test_rejects_what_it_cannot_read(self):
        for raw in ("abc", "1k", "ألف", "12 x", "1,2,3", "", None, "--"):
            self.assertIsNone(mt.parse_number(raw), raw)


class Headers(unittest.TestCase):
    def test_id_text_prefix_and_none(self):
        self.assertEqual(CB.map_header("C1"), ("C1", "id"))
        self.assertEqual(CB.map_header(" c1 "), ("C1", "id"))
        self.assertEqual(CB.map_header("Quelles applications utilisez-vous avec vos clientes ?"), ("C1", "text"))
        self.assertEqual(CB.map_header("ما التطبيقات التي تستخدمينها مع الزبائن"), ("C1", "text"))
        self.assertEqual(CB.map_header("Which apps do you use with customers? (select all)"), ("C1", "prefix"))
        self.assertEqual(CB.map_header("Timestamp"), (None, "none"))
        self.assertEqual(CB.map_header("Which"), (None, "none"))      # too short to prefix-match
        self.assertEqual(CB.map_header("Are you 18"), (None, "none"))  # a real prefix, but under 12 characters

    def test_ambiguous_prefix_is_refused(self):
        qs = [{"id": "X1", "type": "text", "text": {"en": "Tell us about your business please"}},
              {"id": "X2", "type": "text", "text": {"en": "Tell us about your business hours"}}]
        cb = mt.Codebook(qs)
        self.assertEqual(cb.map_header("Tell us about your business"), (None, "none"))

    def test_a_price_header_must_match_both_ends_of_the_question_text(self):
        cb = mt.Codebook([{"id": "W2", "type": "single",
                           "text": {"en": "Would you pay {PRICE} DZD per month for the assistant?"},
                           "options": [opt("yes", "Yes", "Oui", "نعم")]}])
        self.assertEqual(cb.price_in_header("Would you pay 500 DZD per month for the assistant?"), ("W2", 500.0))
        self.assertEqual(cb.price_in_header("Would you pay 1 500 DZD per month for the assistant?"), ("W2", 1500.0))
        self.assertIsNone(cb.price_in_header("Would you pay 500 DZD per week for the assistant?"))      # other ending
        self.assertIsNone(cb.price_in_header("How would you pay 500 DZD per month for the assistant?"))  # other start
        self.assertIsNone(cb.price_in_header("Would you pay DZD per month for the assistant?"))          # no number
        self.assertIsNone(cb.price_in_header("Would you pay 5x0 DZD per month for the assistant?"))

    def test_collisions_are_caught_at_construction(self):
        with self.assertRaises(ValueError):
            mt.Codebook([{"id": "A", "type": "single", "text": {"en": "q"},
                          "options": [opt("a", "Same", "x", "y"), opt("b", "same", "z", "w")]}])
        with self.assertRaises(ValueError):
            mt.Codebook([{"id": "A", "type": "text", "text": {"en": "Same question"}},
                         {"id": "B", "type": "text", "text": {"en": "same   question?"}}])


class Values(unittest.TestCase):
    def test_single_choice_in_each_language_gives_one_code(self):
        for raw in ("Android smartphone", "Smartphone Android", "هاتف أندرويد", "هاتف اندرويد", "android",
                    "  ANDROID SMARTPHONE "):
            self.assertEqual(CB.map_value("D1", raw)["codes"], ["android"], raw)

    def test_synonyms_and_a_real_answer_called_none(self):
        self.assertEqual(CB.map_value("S2", "wah")["codes"], ["yes"])
        self.assertEqual(CB.map_value("S2", "la")["codes"], ["no"])
        r = CB.map_value("D1", "None of these")
        self.assertEqual((r["codes"], r["missing"]), (["none"], False))

    def test_multi_select_separators_and_duplicates(self):
        for raw in ("WhatsApp, فيسبوك", "واتساب؛ Facebook", "whatsapp|facebook", "WhatsApp\nFacebook",
                    "واتساب،فيسبوك", "WhatsApp, واتساب, Facebook"):
            self.assertEqual(CB.map_value("C1", raw)["codes"], ["whatsapp", "facebook"], raw)

    def test_free_text_goes_to_other_and_misspellings_are_flagged(self):
        r = CB.map_value("C1", "WhatsApp, Telegram")
        self.assertEqual(r["codes"], ["whatsapp", "other"])
        self.assertEqual(r["other"], "Telegram")
        self.assertEqual(r["near"], [])
        r = CB.map_value("C1", "Whatsap")
        self.assertEqual(r["codes"], ["other"])
        self.assertEqual(r["near"], [("Whatsap", "whatsapp")])

    def test_empty_pieces_between_separators_are_ignored(self):
        r = CB.map_value("C1", "WhatsApp,, Facebook, ; ")
        self.assertEqual((r["codes"], r["other"], r["unmapped"]), (["whatsapp", "facebook"], None, []))

    def test_every_unmatched_answer_is_kept_in_other_in_order(self):
        r = CB.map_value("C1", "WhatsApp, Telegram, Signal")
        self.assertEqual(r["codes"], ["whatsapp", "other"])
        self.assertEqual(r["other"], "Telegram | Signal")

    def test_unmatched_answer_without_an_other_option_is_reported_not_dropped(self):
        r = CB.map_value("D1", "Nokia 3310")
        self.assertEqual((r["codes"], r["unmapped"]), ([], ["Nokia 3310"]))

    def test_scale_answers(self):
        for raw in ("4", "٤", "4 out of 5", "4 sur 5", "4 من 5"):
            self.assertEqual(CB.map_value("M1", raw)["codes"], ["4"], raw)

    def test_numbers_and_money(self):
        self.assertEqual(CB.map_value("W1", "1 500 DA")["number"], 1500.0)
        self.assertEqual(CB.map_value("O5", "٣")["number"], 3.0)
        r = CB.map_value("O5", "a few")
        self.assertEqual((r["number"], r["unmapped"]), (None, ["a few"]))

    def test_missing_cells(self):
        for raw in (None, "", "NaN"):
            r = CB.map_value("C1", raw)
            self.assertTrue(r["missing"])
            self.assertEqual((r["codes"], r["unmapped"]), ([], []))


if __name__ == "__main__":
    unittest.main(verbosity=2)
