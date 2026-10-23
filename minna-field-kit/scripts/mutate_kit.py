#!/usr/bin/env python3
"""Mutation check for the field kit: do the tests notice when the code is wrong?

Each mutant is ONE exact-once textual change to one file of the kit, applied to a
throw-away copy. Outcome per mutant:

  KILLED    at least one test fails (or the run hangs)   -> the tests protect this line
  SURVIVED  every test still passes                       -> a gap: add a test, or justify below
  INVALID   the mutated file no longer parses or imports  -> not scored
  ERROR     the pattern was not found exactly once        -> fix the mutant list

Mutants judged EQUIVALENT (the change cannot alter any output) are not hidden: they
are listed in EQUIVALENT with the reason and are never counted in the score.

usage: python3 scripts/mutate_kit.py [--jobs N] [--only NAME,NAME] [--check-patterns]
                                     [--json PATH] [--list]
Exit status 1 if the baseline is not green, or any mutant survived or errored.
"""
import argparse
import concurrent.futures as cf
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0")
ALL_TESTS = ["test_content", "test_guides", "test_text", "test_hand_built", "test_stats", "test_pipeline"]
FIRST = {"minna_stats.py": "test_stats", "minna_text.py": "test_text",
         "content": "test_content", "guide": "test_guides"}
DEFAULT_FIRST = "test_hand_built"          # data, estimates, report, forms, cli: fast hand-built cases first

S, T = "minna_stats.py", "minna_text.py"
D, E, R = "survey_data.py", "survey_estimates.py", "survey_report.py"
F, C = "survey_forms.py", "survey_cli.py"
SY = "survey_synth.py"
P1 = "content/part1_screen_profile_devices.json"
P2 = "content/part2_channels_orders.json"
META = "content/meta.json"
GEN, GFR = "interview_guide_en.md", "interview_guide_fr.md"

# (name, file, exact old text, new text)
MUTANTS = [
    # ---- minna_stats.py: exact intervals ---------------------------------
    ("cp_two_sided_uses_one_sided_tail", S,
     "tail = round((1 - conf) / 2, 12)", "tail = round(1 - conf, 12)"),
    ("cp_lower_one_sided_tail_halved", S,
     "return cp_lower(k, n, round(1 - conf, 12))", "return cp_lower(k, n, round((1 - conf) / 2, 12))"),
    ("cp_upper_one_sided_tail_halved", S,
     "return cp_upper(k, n, round(1 - conf, 12))", "return cp_upper(k, n, round((1 - conf) / 2, 12))"),
    ("solver_too_few_iterations", S,
     "increasing: bool, iters: int = 60)", "increasing: bool, iters: int = 12)"),
    ("wilson_z_one_sided", S,
     "    z = NormalDist().inv_cdf(1 - (1 - conf) / 2)\n    ph = k / n\n",
     "    z = NormalDist().inv_cdf(1 - (1 - conf))\n    ph = k / n\n"),
    ("wilson_half_width_formula", S,
     "z * z / (4 * n * n)", "z * z / (4 * n)"),
    ("wilson_no_centre_shift", S,
     "centre = (ph + z * z / (2 * n)) / denom", "centre = ph"),
    # ---- sample sizes ------------------------------------------------------
    ("required_n_alpha_doubled", S,
     "while binom_cdf(k, n, p_max) > alpha:", "while binom_cdf(k, n, p_max) > 2 * alpha:"),
    ("margin_at_uses_shorter_arm", S,
     "return max(hi - ph, ph - lo)", "return min(hi - ph, ph - lo)"),
    ("proportion_margin_uses_shorter_arm", S,
     "margin = max(hi - ph, ph - lo)", "margin = min(hi - ph, ph - lo)"),
    ("worst_case_scans_a_window_only", S,
     "return max(margin_at(n, k, conf) for k in range(0, n // 2 + 1))",
     "return max(margin_at(n, k, conf) for k in range(max(0, n // 2 - 3), n // 2 + 1))"),
    ("worst_case_k_returns_the_minimum", S,
     "return max(range(0, n // 2 + 1), key=lambda k: margin_at(n, k, conf))",
     "return min(range(0, n // 2 + 1), key=lambda k: margin_at(n, k, conf))"),
    ("n_for_margin_no_lookahead_guard", S,
     '    if any(worst_case_margin(m, conf) > margin for m in range(lo, lo + lookahead + 1)):\n'
     '        raise ValueError("margin rises again just above the answer; scan linearly")\n',
     "    pass\n"),
    ("n_for_margin_upper_bound_unchecked", S,
     '    if worst_case_margin(hi, conf) > margin:\n'
     '        raise ValueError("upper search bound too small; margin unusually tight")\n',
     "    pass\n"),
    ("normal_n_z_one_sided", S,
     "    z = NormalDist().inv_cdf(1 - (1 - conf) / 2)\n    return math.ceil(z * z * 0.25 / (margin * margin))\n",
     "    z = NormalDist().inv_cdf(1 - (1 - conf))\n    return math.ceil(z * z * 0.25 / (margin * margin))\n"),
    # ---- interviews ---------------------------------------------------------
    ("prob_detect_off_by_one", S,
     "return 1 - (1 - prevalence) ** n", "return 1 - (1 - prevalence) ** (n - 1)"),
    ("n_to_detect_alpha_halved", S,
     "    alpha = round(1 - conf, 12)\n    n = 1\n", "    alpha = round((1 - conf) / 2, 12)\n    n = 1\n"),
    ("min_detectable_off_by_one", S,
     "return 1 - round(1 - conf, 12) ** (1.0 / n)", "return 1 - round(1 - conf, 12) ** (1.0 / (n + 1))"),
    # ---- clustering ---------------------------------------------------------
    ("design_effect_no_minus_one", S,
     "return 1 + (mean_cluster_size - 1) * icc", "return 1 + mean_cluster_size * icc"),
    ("wilson_deff_keeps_raw_k", S,
     "return wilson(k / deff, n / deff, conf)", "return wilson(k, n / deff, conf)"),
    ("cluster_sim_ignores_rho", S,
     "theta = rng.betavariate(a, b) if rho > 0 else mu", "theta = mu"),
    ("cluster_sim_wrong_beta_scale", S,
     "s = (1 - rho) / rho", "s = (1 - rho) * rho"),
    # ---- two groups -----------------------------------------------------------
    ("fisher_ties_excluded", S,
     "if p <= p_obs * (1 + 1e-7)))", "if p < p_obs * (1 - 1e-7)))"),
    ("fisher_tolerance_removed", S,
     "if p <= p_obs * (1 + 1e-7)))", "if p <= p_obs))"),
    ("fisher_support_lower_bound_zero", S,
     "lo, hi = max(0, k - n2), min(k, n1)", "lo, hi = 0, min(k, n1)"),
    ("mcnemar_one_sided", S,
     "min(1.0, 2 * binom_cdf(min(b, c), n, 0.5))", "min(1.0, binom_cdf(min(b, c), n, 0.5))"),
    ("mcnemar_empty_is_zero", S,
     "return 1.0 if n == 0 else", "return 0.0 if n == 0 else"),
    ("rejection_set_tolerance_removed", S,
     "pos = bisect.bisect_right(sorted_p, v * (1 + 1e-7))", "pos = bisect.bisect_right(sorted_p, v)"),
    ("rejection_set_level_halved", S,
     "if min(1.0, cum[pos - 1]) <= alpha:", "if min(1.0, cum[pos - 1]) <= alpha / 2:"),
    ("fisher_power_second_arm_size_ignored", S,
     "n2 = n1 if n2 is None else n2", "n2 = n1"),
    ("fisher_power_same_rate_both_arms", S,
     "pm1 = [binom_pmf(x, n1, p1) for x in range(n1 + 1)]", "pm1 = [binom_pmf(x, n1, p2) for x in range(n1 + 1)]"),
    ("normal_n_per_arm_one_sided_alpha", S,
     "n = (z(1 - alpha / 2) + z(power)) ** 2", "n = (z(1 - alpha) + z(power)) ** 2"),
    ("check_allows_k_above_n", S,
     "n < 1 or not 0 <= k <= n:", "n < 1 or not 0 <= k:"),
    ("fisher_accepts_negative_counts", S,
     "if min(a, b, c, d) < 0 or total == 0:", "if total == 0:"),
    # ---- bootstrap, proportion -------------------------------------------------
    ("bootstrap_keeps_zero_denominators", S,
     "pairs = [(a, b) for a, b in zip(nums, dens) if b > 0]", "pairs = [(a, b) for a, b in zip(nums, dens) if b >= 0]"),
    ("bootstrap_interval_is_90_percent", S,
     "    tail = (1 - conf) / 2\n    return est,", "    tail = (1 - conf)\n    return est,"),
    ("proportion_wide_threshold_ignored", S,
     '"wide": margin > wide_margin}', '"wide": margin > 0.5}'),
    # ---- minna_text.py -----------------------------------------------------------
    ("norm_keeps_combining_marks", T,
     'not in ("Mn", "Cf"))', 'not in ("Cf",))'),
    ("norm_keeps_format_characters", T,
     'not in ("Mn", "Cf"))', 'not in ("Mn",))'),
    ("norm_keeps_tatweel", T,
     's = s.replace("ـ", "").translate(_ARABIC_SPELLING).casefold()',
     "s = s.translate(_ARABIC_SPELLING).casefold()"),
    ("norm_no_alef_maksura_fold", T,
     '{"ى": "ي", "ة": "ه", ', '{"ة": "ه", '),
    ("norm_no_teh_marbuta_fold", T,
     '"ة": "ه", "ی": "ي"', '"ی": "ي"'),
    ("norm_persian_digits_dropped", T,
     '_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")',
     '_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")'),
    ("norm_deletes_punctuation_instead_of_spacing", T,
     'return " ".join(_NOT_WORD.sub(" ", s).split())', 'return " ".join(_NOT_WORD.sub("", s).split())'),
    ("none_treated_as_missing", T,
     '_MISSING = {"", "nan", "null", "n/a", "na"}', '_MISSING = {"", "nan", "null", "n/a", "na", "none"}'),
    ("money_group_pattern_loose", T,
     r'if money and re.fullmatch(r"\d{1,3}(?:[ .,]\d{3})+", s):',
     r'if money and re.fullmatch(r"\d{1,3}(?:[ .,]\d{2,3})+", s):'),
    ("thousands_rule_applied_to_plain_numbers", T,
     "if money and re.fullmatch(", "if re.fullmatch("),
    ("decimal_comma_becomes_thousands", T,
     'return float(s.replace(",", "."))', 'return float(s.replace(",", ""))'),
    ("currency_suffix_not_stripped", T,
     's = _CURRENCY.sub("", s).strip()', "s = s.strip()"),
    ("header_prefix_match_too_short", T,
     "if len(t) >= 12 and len(h) >= 12 and", "if len(t) >= 3 and len(h) >= 3 and"),
    ("header_prefix_ambiguity_accepted", T,
     "if len(hits) == 1:", "if len(hits) >= 1:"),
    ("near_miss_cutoff_too_strict", T,
     "n=1, cutoff=0.8)", "n=1, cutoff=0.99)"),
    ("near_miss_cutoff_too_loose", T,
     "n=1, cutoff=0.8)", "n=1, cutoff=0.3)"),
    ("multi_select_duplicates_kept", T,
     'if code not in out["codes"]:', "if True:"),
    ("empty_pieces_become_answers", T,
     "            if not tok:\n                continue\n", "            if False:\n                continue\n"),
    ("money_flag_dropped", T,
     'val = parse_number(raw, money=(kind != "number"))', "val = parse_number(raw, money=False)"),
    ("arabic_comma_not_a_separator", T,
     'r"[,;|\\n،؛]+"', 'r"[,;|\\n]+"'),
    ("other_text_keeps_last_only", T,
     "out[\"other\"] = tok if out[\"other\"] is None else f\"{out['other']} | {tok}\"", 'out["other"] = tok'),
    ("norm_no_ae_fold", T,
     '"ھ": "ه", "ە": "ه"})', '"ھ": "ه"})'),
    ("norm_no_casefold", T,
     ".translate(_ARABIC_SPELLING).casefold()", ".translate(_ARABIC_SPELLING)"),
    ("norm_uses_nfc_not_nfkd", T,
     'unicodedata.normalize("NFKD", str(text))', 'unicodedata.normalize("NFC", str(text))'),
    ("missing_check_keeps_whitespace", T,
     "str(raw).strip().lower() in _MISSING", "str(raw).lower() in _MISSING"),
    ("missing_check_case_sensitive", T,
     "str(raw).strip().lower() in _MISSING", "str(raw).strip() in _MISSING"),
    ("question_text_collision_not_detected", T,
     'if self._header_text.setdefault(t, q["id"]) != q["id"]:', "if False:"),
    ("option_collision_not_detected", T,
     'if table.setdefault(key, opt["code"]) != opt["code"]:', "if False:"),
    ("price_header_needs_only_one_end", T,
     "and h.startswith(left) and h.endswith(right):", "and (h.startswith(left) or h.endswith(right)):"),
    # ---- survey_data.py ------------------------------------------------------------
    ("consent_not_enforced", D,
     'if row["S1"]["codes"] != ["yes"]:', "if False:"),
    ("adult_screen_not_enforced", D,
     'if row["S2"]["codes"] != ["yes"]:', "if False:"),
    ("one_missing_screen_column_accepted", D,
     'if not {"S1", "S2"} <= present and not assume_screened:',
     'if not {"S1", "S2"} & present and not assume_screened:'),
    ("missing_screen_columns_never_refused", D,
     'if not {"S1", "S2"} <= present and not assume_screened:',
     'if not {"S1", "S2"} <= present and False:'),
    ("range_upper_bound_exclusive", D,
     'if not lo <= m["number"] <= hi:', 'if not lo <= m["number"] < hi:'),
    ("range_lower_bound_exclusive", D,
     'if not lo <= m["number"] <= hi:', 'if not lo < m["number"] <= hi:'),
    ("max_select_off_by_one", D,
     'if limit and len(m["codes"]) > limit:', 'if limit and len(m["codes"]) >= limit:'),
    ("max_select_allows_one_extra", D,
     'if limit and len(m["codes"]) > limit:', 'if limit and len(m["codes"]) > limit + 1:'),
    ("refused_equal_to_recalled_is_invalid", D,
     'and b["number"] > a["number"]:', 'and b["number"] >= a["number"]:'),
    ("refused_above_recalled_unchecked", D,
     'if a["number"] is not None and b["number"] is not None and b["number"] > a["number"]:', "if False:"),
    ("allow_all_contradiction_threshold", D,
     'if "allow_all" in m2 and len(m2) > 1:', 'if "allow_all" in m2 and len(m2) > 2:'),
    ("w2_without_price_unflagged", D,
     'if row["W2"]["codes"] and row["_price"] is None:', "if False:"),
    ("answered_ignores_invalid_flag", D,
     'return not m["missing"] and not m.get("invalid") and bool(', 'return not m["missing"] and bool('),
    ("skip_chain_not_followed", D,
     '    if not is_expected(cond["q"], row, qmap):\n        return False\n', ""),
    ("skip_logic_needs_all_codes", D,
     'any(c in cond["in"] for c in parent["codes"])', 'all(c in cond["in"] for c in parent["codes"])'),
    ("nonresponse_counts_unexpected_answers", D,
     's["answered"] += exp and ans', 's["answered"] += ans'),
    ("unexpected_answers_not_counted", D,
     's["unexpected_answers"] += (not exp) and ans', 's["unexpected_answers"] += 0'),
    ("last_duplicate_column_wins", D,
     'if row[qid]["missing"] and not m["missing"]:', 'if not m["missing"]:'),
    ("blank_rows_not_skipped", D,
     "if not any(c.strip() for c in raw):", "if False:"),
    ("price_in_header_ignored", D,
     "price_from_header = price", "price_from_header = None"),
    ("price_prefers_header_over_price_cell", D,
     'row["_price"] = row["price_cell"]["number"] if row["price_cell"]["number"] is not None \\\n            else price_from_header',
     'row["_price"] = price_from_header if price_from_header is not None \\\n            else row["price_cell"]["number"]'),
    ("unmatched_headers_not_recorded", D,
     "unmatched.append(h)", "pass"),
    ("w2_duplicates_reported_as_a_problem", D,
     'if c > 1 and qid != "W2")', "if c > 1)"),
    ("empty_file_not_refused", D,
     'if len(table) < 1:\n        raise DataError("the file is empty")', "if False:\n        pass"),
    ("short_rows_crash", D,
     "m = cb.map_value(qid, raw[i] if i < len(raw) else None)", "m = cb.map_value(qid, raw[i])"),
    # ---- survey_estimates.py ------------------------------------------------------------
    ("invalid_answers_counted", E,
     'if m["missing"] or m.get("invalid") or not m["codes"]:', 'if m["missing"] or not m["codes"]:'),
    ("excluded_codes_counted", E,
     'codes = [c for c in m["codes"] if c not in exclude]', 'codes = list(m["codes"])'),
    ("tally_needs_all_codes", E,
     'k += any(c in est["codes"] for c in codes)', 'k += all(c in est["codes"] for c in codes)'),
    ("cluster_code_coverage_too_low", E,
     'len(refs) >= 0.8 * item["n"]', 'len(refs) >= 0.1 * item["n"]'),
    ("single_cluster_accepted", E,
     "and len(sizes) >= 2:", "and len(sizes) >= 1:"),
    ("price_test_uses_second_cell", E,
     'lo, hi = table[0], table[-1]', 'lo, hi = table[0], table[1]'),
    ("price_test_drops_maybe", E,
     'ms.fisher_exact(lo["yes"], lo["n"] - lo["yes"], hi["yes"], hi["n"] - hi["yes"])',
     'ms.fisher_exact(lo["yes"], lo["no"], hi["yes"], hi["no"])'),
    ("refusal_keeps_zero_recall", E,
     "pairs = [(b, a) for b, a in pairs if a > 0]", "pairs = [(b, a) for b, a in pairs if a >= 0]"),
    ("pick2_both_counted_as_only_first", E,
     "only_a += in_a and not in_b", "only_a += in_a"),
    ("top_pains_includes_orderflow", E,
     ' and i["id"] != "pain_orderflow"', ""),
    ("top_pains_ascending", E,
     'key=lambda i: (-i["p"], i["id"])', 'key=lambda i: (i["p"], i["id"])'),
    ("android_pass_on_upper_bound", E,
     '"PASS: Android share is at least the threshold" if lower >= thr else',
     '"PASS: Android share is at least the threshold" if upper >= thr else'),
    ("android_fail_on_lower_bound", E,
     '"FAIL: Android share is below the threshold" if upper < thr else',
     '"FAIL: Android share is below the threshold" if lower < thr else'),
    ("android_clustered_level_95", E,
     "ms.wilson_deff(k, n, m, rho, conf=0.90)", "ms.wilson_deff(k, n, m, rho, conf=0.95)"),
    ("headline_uses_90_percent", E,
     "ms.proportion(k, n, conf, wide) if n else", "ms.proportion(k, n, 0.90, wide) if n else"),
    ("headline_ignores_wide_margin_setting", E,
     "ms.proportion(k, n, conf, wide) if n else", "ms.proportion(k, n, conf) if n else"),
    ("segments_ignore_wide_margin_setting", E,
     'ms.proportion(k, n, meta["design"]["conf"], meta["design"]["wide_margin"]) if n',
     'ms.proportion(k, n, meta["design"]["conf"]) if n'),
    ("cluster_view_assumed_sizes_changed", E,
     "assumed_sizes=(5, 10, 20)", "assumed_sizes=(5, 10, 40)"),
    ("cluster_view_margin_uses_shorter_arm", E,
     '"margin": max(hi - k / n, k / n - lo)}', '"margin": min(hi - k / n, k / n - lo)}'),
    ("cluster_view_share_counts_uncoded_respondents", E,
     '(max(sizes.values()) / len(refs)) if observed', '(max(sizes.values()) / item["n"]) if observed'),
    ("sample_check_slack", E,
     'out[key]["margin"] <= target)', 'out[key]["margin"] <= target * 1.2)'),
    ("sellers_exclude_occasional", E,
     'SELLERS = ("regular", "occasional")', 'SELLERS = ("regular",)'),
    ("planning_group_wrong", E,
     '"planning": lambda r: r["S3"]["codes"] == ["planning"]}', '"planning": lambda r: r["S3"]["codes"] == ["occasional"]}'),
    # ---- survey_report.py ---------------------------------------------------------------
    ("report_hides_unmatched_headers", R,
     'if audit["unmatched_headers"]:', "if False:"),
    ("report_hides_issues", R,
     'for msg, c in audit["issues"].items():', "for msg, c in []:"),
    ("report_hides_unmapped_answers", R,
     'if s["unmapped"]:', "if False:"),
    ("report_nonresponse_threshold_raised", R,
     'if s["expected"] and s["nonresponse"] / s["expected"] > 0.10:',
     'if s["expected"] and s["nonresponse"] / s["expected"] > 0.90:'),
    ("report_cluster_dominance_threshold_raised", R,
     "if top / len(refs) > 0.25", "if top / len(refs) > 0.99"),
    ("report_target_always_met", R,
     '"yes" if chk[g]["meets_target"] else "**no**"', '"yes"'),
    ("report_hides_clustered_verdict", R,
     'if "clustered_status" in a:', "if False:"),
    ("report_price_note_inverted", R,
     'if w["test"]["p_value"] >= 0.05', 'if w["test"]["p_value"] < 0.05'),
    ("report_mcnemar_wording_threshold", R,
     'if t["p_value"] >= 0.05', 'if t["p_value"] >= 0.5'),
    ("report_drops_stated_is_not_done_caveat", R,
     '    "**Stated is not done.** Interest, willingness to pay and the recalled refusal rate overstate or distort behaviour. Treat them as screens. The pilot\'s payments and logs are the evidence.",\n',
     ""),
    ("report_planning_number_not_enough_note_dropped", R,
     " is the normal-approximation figure and is not enough)", " is the normal-approximation figure)"),
    ("report_hides_duplicate_columns", R,
     'if audit["duplicate_columns"]:', "if False:"),
    ("report_hides_misspelled_labels", R,
     'if s["near"]:', "if False:"),
    ("report_hides_unexpected_answers", R,
     'if s["unexpected_answers"]:', "if False:"),
    ("report_hides_unpriced_answers", R,
     'if w["unpriced"]:', "if False:"),
    ("report_pain_id_prefix_slice", R,
     'pains[0]["id"][5:]', 'pains[0]["id"][6:]'),
    ("report_wide_legend_uses_the_target", R,
     "WIDE = margin above {100 * d['wide_margin']:.0f} pp", "WIDE = margin above {100 * d['margin_target']:.0f} pp"),
    ("report_never_flags_wide", R,
     '"WIDE" if i["wide"] else ""', '""'),
    # ---- survey_forms.py ----------------------------------------------------------------
    ("form_optional_marker_dropped", F,
     '("" if q["required"] or q["type"] == "hidden" else ", optional")', '""'),
    ("form_draft_banner_dropped", F,
     'f"> **DRAFT, do not field yet.** Fill in: {fill}. Price cells are placeholders "',
     'f"> Fill in: {fill}. Price cells are placeholders "'),
    ("form_translation_warning_dropped", F,
     '+ ("" if lang == "en" else "This translation needs native-speaker review and a pretest. ")', '+ ""'),
    ("form_arabic_not_right_to_left", F,
     'if lang == "ar":', "if False:"),
    ("placeholders_ignore_closing_text", F,
     'for key in ("consent", "closing"):', 'for key in ("consent",):'),
    # ---- survey_synth.py (the generator behind every planted-truth test) -----------------
    ("generator_writes_a_set_in_hash_order", SY,
     'many("C1", sorted({main} | {k for k, v in P["C1_extra"].items() if rng.random() < v}))',
     'many("C1", {main} | {k for k, v in P["C1_extra"].items() if rng.random() < v})'),
    # The planted truth itself: a slip here makes the pipeline look biased (or hides a real bias).
    ("truth_second_draw_not_renormalised", SY,
     "/ (total - w[u])", "/ total"),
    ("truth_pick_two_ignores_the_second_draw", SY,
     'P["O6_k"][2] * (1 - miss_both)', 'P["O6_k"][2] * hit_first'),
    ("truth_at_least_one_choice_not_conditioned_on", SY,
     "return {k: v / (1 - none) for k, v in p.items()}", "return dict(p)"),
    ("truth_shared_phone_denominator_dropped", SY,
     '(P["D3"]["sometimes"] + P["D3"]["often"]) / (1 - P["D3"]["pnts"]),',
     '(P["D3"]["sometimes"] + P["D3"]["often"]),'),
    ("truth_outage_denominator_dropped", SY,
     'P["D4"]["days_3plus"] / (1 - P["D4"]["unknown"]),', 'P["D4"]["days_3plus"],'),
    ("truth_nobody_share_dropped_from_trust", SY,
     '"trust_state": (1 - P["M4_nobody"]) * m4["state"],', '"trust_state": m4["state"],'),
    ("truth_allow_all_share_ignored", SY,
     'a = 1 - P["M2_allow_all"]', "a = 1"),
    ("truth_main_app_counted_twice", SY,
     'ch = lambda c: P["C2"][c] + (1 - P["C2"][c]) * P["C1_extra"][c]',
     'ch = lambda c: P["C2"][c] + P["C1_extra"][c]'),
    # ---- survey_cli.py -------------------------------------------------------------------
    ("refused_analysis_exits_zero", C,
     "        return 2\n", "        return 0\n"),
    ("plan_slow_flag_ignored", C,
     "    if args.slow:\n", "    if False:\n"),
    ("estimates_file_always_written", C,
     "    if args.estimates_csv:\n", "    if True:\n"),
    ("selftest_always_green", C,
     "return 0 if result.wasSuccessful() else 1", "return 0"),
    # ---- content (what is asked and how it is gated) -------------------------------------
    ("age_screen_not_gated_on_consent", P1,
     '      "show_if": {"q": "S1", "in": ["yes"]},\n', ""),
    ("segment_not_gated_on_age_screen", P1,
     "purpose\": \"Segment screen. Sellers (regular, occasional) get the orders section; planners are counted but kept apart. Feeds decision D1.\",\n"
     '      "show_if": {"q": "S2", "in": ["yes"]},\n',
     "purpose\": \"Segment screen. Sellers (regular, occasional) get the orders section; planners are counted but kept apart. Feeds decision D1.\",\n"),
    ("parcels_recalled_may_be_zero", P2,
     '"range": [1, 20],', '"range": [0, 20],'),
    ("pick_two_becomes_pick_three", P2,
     '"max_select": 2', '"max_select": 3'),
    ("meta_sample_size_is_the_textbook_one", META,
     '"n_min_exact": 106,', '"n_min_exact": 97,'),
    ("meta_margin_target_changed", META,
     '"margin_target": 0.10,', '"margin_target": 0.12,'),
    # ---- the interview guides print computed numbers ---------------------------------------
    ("guide_en_table_cell_wrong", GEN,
     "| 7 of 14 | 26.4% | 73.6% |", "| 7 of 14 | 26.5% | 73.6% |"),
    ("guide_fr_table_cell_wrong", GFR,
     "| 7 sur 14 | 26,4 % | 73,6 % |", "| 7 sur 14 | 26,4 % | 73,7 % |"),
]

# Judged equivalent: no input can make the output differ, so no test could kill them.
# Never counted in the score; kept here so the list of what was tried stays honest.
EQUIVALENT = {}

# Mutants that survived because the code they changed could never matter. The code was deleted
# instead of the mutant being excused; the entries stay here as the record of what was found.
REMOVED_CODE = {
    "n_for_margin_no_monotone_guard":
        "minna_stats.n_for_margin re-checked that n - 1 fails after the bisection. The bisection "
        "has itself just evaluated n - 1 (that is how it arrived at n), so the check could never fire "
        "for a deterministic margin function. Deleted; the docstring now says what is really checked.",
    "norm_no_ae_fold (found by reading the survivors, not by a mutant)":
        "minna_text mapped U+06C0 to heh, but NFKD turns U+06C0 into U+06D5 plus a mark before the "
        "mapping runs, so the entry was never reached. The key is now U+06D5.",
}


def first_for(fname):
    if fname.startswith("content/"):
        return FIRST["content"]
    if fname.startswith("interview_guide"):
        return FIRST["guide"]
    return FIRST.get(fname, DEFAULT_FIRST)


def work_copy():
    tmp = tempfile.mkdtemp(prefix="kitmut-")
    shutil.copytree(KIT, os.path.join(tmp, "kit"),
                    ignore=shutil.ignore_patterns("__pycache__", "generated", "scripts", "*.zip", "examples"))
    return tmp, os.path.join(tmp, "kit")


def run_tests(kit, order, timeout):
    for name in order:
        cmd = [PY, "-m", "unittest", "discover", "-s", "tests", "-p", f"{name}.py", "-f"]
        try:
            p = subprocess.run(cmd, cwd=kit, capture_output=True, text=True, timeout=timeout, env=ENV)
        except subprocess.TimeoutExpired:
            return "KILLED", f"{name}: hang (timeout)"
        if p.returncode != 0:
            if "_FailedTest" in p.stderr:
                return "INVALID", f"{name}: module no longer imports"
            m = re.search(r"^(?:FAIL|ERROR): (\S+) \(([^)]+)\)", p.stderr, re.M)
            return "KILLED", f"{name}: {m.group(1)}" if m else f"{name}: exit {p.returncode}"
    return "SURVIVED", ""


def apply(kit, fname, old, new):
    path = os.path.join(kit, fname)
    text = open(path, encoding="utf-8").read()
    count = text.count(old)
    if count != 1:
        return None, f"pattern found {count}x (need exactly 1)"
    mutated = text.replace(old, new)
    if mutated == text:
        return None, "mutation changes nothing"
    if fname.endswith(".py"):
        try:
            compile(mutated, fname, "exec")
        except SyntaxError as exc:
            return None, f"does not compile: {exc.msg}"
    elif fname.endswith(".json"):
        try:
            json.loads(mutated)
        except ValueError as exc:
            return None, f"invalid JSON: {exc}"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(mutated)
    return True, ""


def run_mutant(m, timeout, check_only):
    name, fname, old, new = m
    tmp, kit = work_copy()
    try:
        ok, why = apply(kit, fname, old, new)
        if ok is None:
            return name, ("ERROR" if why.startswith(("pattern", "mutation")) else "INVALID"), why
        if check_only:
            return name, "OK", "pattern found once, file still parses"
        first = first_for(fname)
        order = [first] + [t for t in ALL_TESTS if t != first]
        status, detail = run_tests(kit, order, timeout)
        return name, status, detail
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def baseline(timeout):
    tmp, kit = work_copy()
    try:
        return run_tests(kit, ALL_TESTS, timeout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--only", help="comma-separated mutant names")
    ap.add_argument("--timeout", type=int, default=300, help="seconds per test file")
    ap.add_argument("--check-patterns", action="store_true", help="only verify each pattern; run no tests")
    ap.add_argument("--json", help="write the results to this file")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    names = [m[0] for m in MUTANTS]
    if len(set(names)) != len(names):
        sys.exit("duplicate mutant names")
    if args.list:
        for m in MUTANTS:
            print(f"{m[0]:<48} {m[1]}")
        print(len(MUTANTS), "mutants,", len(EQUIVALENT), "judged equivalent")
        return
    chosen = [m for m in MUTANTS if not args.only or m[0] in set(args.only.split(","))]
    t0 = time.time()
    if not args.check_patterns:
        status, detail = baseline(args.timeout)
        print("BASELINE:", "green" if status == "SURVIVED" else f"NOT GREEN ({status} {detail})")
        if status != "SURVIVED":
            sys.exit("baseline is not green; mutation results would be meaningless")
    results = []
    with cf.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(run_mutant, m, args.timeout, args.check_patterns) for m in chosen]
        for done, fut in enumerate(cf.as_completed(futures), 1):
            res = fut.result()
            results.append(res)
            print(f"[{done:3d}/{len(chosen)}] {res[0]:<46} {res[1]:<8} {res[2]}", flush=True)
    order = {m[0]: i for i, m in enumerate(chosen)}
    results.sort(key=lambda r: order[r[0]])

    print("\n---- summary, in list order ----")
    width = max(len(r[0]) for r in results)
    for name, status, detail in results:
        print(f"{name:<{width}}  {status:<8} {detail}")
    count = {s: sum(r[1] == s for r in results) for s in ("KILLED", "SURVIVED", "INVALID", "ERROR", "OK")}
    if args.check_patterns:
        print(f"patterns ok={count['OK']} invalid={count['INVALID']} error={count['ERROR']}")
        sys.exit(0 if count["OK"] == len(results) else 1)
    scored = count["KILLED"] + count["SURVIVED"]
    score = count["KILLED"] / scored if scored else float("nan")
    print(f"killed={count['KILLED']} survived={count['SURVIVED']} invalid={count['INVALID']} "
          f"error={count['ERROR']} judged_equivalent={len(EQUIVALENT)}  "
          f"mutation_score={score:.1%}  elapsed={time.time() - t0:.0f}s")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump([{"name": n, "status": s, "detail": d} for n, s, d in results], fh, indent=1)
    sys.exit(1 if count["SURVIVED"] or count["ERROR"] or count["INVALID"] else 0)


if __name__ == "__main__":
    main()
