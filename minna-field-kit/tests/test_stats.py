"""Tests for minna_stats. Run: python3 -m unittest discover -s tests -v

Three kinds of evidence are used, in this order of strength:
  1. defining equations and closed forms (no outside reference needed);
  2. numbers published in the build plan (docs/BUILD_PLAN.md, section 5);
  3. scipy, when installed (skipped, loudly, when not).
"""
import math
import os
import random
import sys
import unittest
from fractions import Fraction
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import minna_stats as ms  # noqa: E402

try:
    from scipy import stats as sps
except ImportError:  # pragma: no cover
    sps = None

needs_scipy = unittest.skipUnless(sps is not None, "SKIPPED: scipy not installed, cross-check not run")

# Build plan section 5: samples n so that at most k failures proves failure rate < p_max.
PLAN_TABLE = {
    0.20: [14, 22, 30, 37, 44],
    0.10: [29, 46, 61, 76, 89],
    0.05: [59, 93, 124, 153, 181],
    0.02: [149, 236, 313, 386, 456],
    0.01: [299, 473, 628, 773, 913],
    0.005: [598, 947, 1258, 1549, 1829],
    0.001: [2995, 4742, 6294, 7752, 9151],
}


def cp_scipy(k, n, conf=0.95):
    a = (1 - conf) / 2
    lo = 0.0 if k == 0 else sps.beta.ppf(a, k, n - k + 1)
    hi = 1.0 if k == n else sps.beta.ppf(1 - a, k + 1, n - k)
    return lo, hi


class ExactInterval(unittest.TestCase):
    def test_defining_equations(self):
        for n, k in [(10, 5), (14, 1), (44, 4), (97, 41), (120, 119)]:
            lo, hi = ms.cp_interval(k, n)
            self.assertAlmostEqual(ms.binom_sf(k, n, lo), 0.025, places=9)
            self.assertAlmostEqual(ms.binom_cdf(k, n, hi), 0.025, places=9)

    def test_closed_forms_at_the_edges(self):
        # k = 0: upper end solves (1 - p)^n = tail; k = n: lower end solves p^n = tail.
        for n in (1, 5, 14, 100):
            self.assertAlmostEqual(ms.cp_upper(0, n, 0.025), 1 - 0.025 ** (1 / n), places=12)
            self.assertAlmostEqual(ms.cp_lower(n, n, 0.025), 0.025 ** (1 / n), places=12)
            self.assertEqual(ms.cp_lower(0, n, 0.025), 0.0)
            self.assertEqual(ms.cp_upper(n, n, 0.025), 1.0)

    def test_reflection_symmetry(self):
        for n in (7, 30, 61):
            for k in range(n + 1):
                lo, hi = ms.cp_interval(k, n)
                lo2, hi2 = ms.cp_interval(n - k, n)
                self.assertAlmostEqual(lo, 1 - hi2, places=10)
                self.assertAlmostEqual(hi, 1 - lo2, places=10)

    def test_guaranteed_coverage_is_at_least_nominal(self):
        # Exact coverage = sum over outcomes whose interval contains p. By construction >= 95%.
        for n in (10, 20, 40):
            for p in (0.05, 0.1, 0.3, 0.5, 0.7, 0.93):
                cover = sum(ms.binom_pmf(k, n, p) for k in range(n + 1)
                            if ms.cp_interval(k, n)[0] <= p <= ms.cp_interval(k, n)[1])
                self.assertGreaterEqual(cover, 0.95 - 1e-9, (n, p))

    def test_published_value(self):
        lo, hi = ms.cp_interval(5, 10)
        self.assertAlmostEqual(lo, 0.1871, places=4)
        self.assertAlmostEqual(hi, 0.8129, places=4)

    def test_one_sided_statements_used_by_the_plan(self):
        # 0 of 14 proves < 20%, 0 of 13 does not; 5 of 10 proves >= 22%.
        self.assertLess(ms.cp_upper_one_sided(0, 14), 0.20)
        self.assertGreaterEqual(ms.cp_upper_one_sided(0, 13), 0.20)
        self.assertAlmostEqual(ms.cp_lower_one_sided(5, 10), 0.2224, places=4)
        # 4 failures in 44 proves < 20%, 4 in 43 does not.
        self.assertLess(ms.cp_upper_one_sided(4, 44), 0.20)
        self.assertGreaterEqual(ms.cp_upper_one_sided(4, 43), 0.20)

    def test_bad_input_is_rejected(self):
        for k, n in [(-1, 5), (6, 5), (0, 0), (1.5, 5)]:
            with self.assertRaises(ValueError):
                ms.cp_interval(k, n)

    @needs_scipy
    def test_against_scipy_beta_quantiles(self):
        worst = 0.0
        for n in (1, 2, 5, 10, 14, 29, 44, 97, 120, 300):
            for k in sorted({0, 1, 2, n // 3, n // 2, n - 1, n} & set(range(n + 1))):
                lo, hi = ms.cp_interval(k, n)
                slo, shi = cp_scipy(k, n)
                worst = max(worst, abs(lo - slo), abs(hi - shi))
        self.assertLess(worst, 1e-10)


class GateTable(unittest.TestCase):
    def test_every_cell_of_the_plan_table(self):
        for p_max, row in PLAN_TABLE.items():
            for k, expected in enumerate(row):
                self.assertEqual(ms.required_n(p_max, k), expected, (p_max, k))

    def test_hand_checkable_zero_failure_rows(self):
        # With k = 0 the condition is (1 - p)^n <= 0.05, so n = ceil(ln 0.05 / ln(1 - p)).
        for p_max in PLAN_TABLE:
            n = ms.required_n(p_max, 0)
            self.assertLessEqual((1 - p_max) ** n, 0.05)
            self.assertGreater((1 - p_max) ** (n - 1), 0.05)


class MarginAndSampleSize(unittest.TestCase):
    def test_textbook_97_is_the_normal_approximation(self):
        self.assertEqual(ms.normal_n_for_margin(0.10), 97)

    def test_97_is_not_enough_for_the_exact_interval(self):
        self.assertGreater(ms.worst_case_margin(97), 0.10)
        self.assertAlmostEqual(ms.worst_case_margin(97), 0.1045, places=4)

    def test_105_fails_and_106_passes(self):
        self.assertGreater(ms.worst_case_margin(105), 0.10)
        self.assertLessEqual(ms.worst_case_margin(106), 0.10)

    def test_the_worst_case_is_not_at_the_centre(self):
        # Regression guard: an earlier version scanned only k within 3 of n/2 and
        # under-reported the margin. The true maximum is near 0.42 n.
        n = 97
        centre_best = max(ms.margin_at(n, k) for k in range(n // 2 - 3, n // 2 + 1))
        self.assertEqual(ms.worst_case_k(n), 41)
        self.assertGreater(ms.margin_at(n, 41), centre_best)

    def test_n_for_margin_matches_a_plain_linear_scan(self):
        def linear(margin):
            n = 20
            while not all(ms.worst_case_margin(m) <= margin for m in range(n, n + 31)):
                n += 1
            return n
        self.assertEqual(ms.n_for_margin(0.15), 49)
        self.assertEqual(ms.n_for_margin(0.15), linear(0.15))
        self.assertEqual(ms.n_for_margin(0.10), 106)

    def test_margin_decreases_with_n_over_the_planning_range(self):
        vals = [ms.worst_case_margin(n) for n in range(80, 113)]
        self.assertTrue(all(b < a for a, b in zip(vals, vals[1:])))

    @needs_scipy
    def test_worst_case_margin_against_exhaustive_scipy_scan(self):
        for n in (20, 50, 97, 106):
            ref = max(max(cp_scipy(k, n)[1] - k / n, k / n - cp_scipy(k, n)[0])
                      for k in range(n // 2 + 1))
            self.assertAlmostEqual(ms.worst_case_margin(n), ref, places=10)


class Interviews(unittest.TestCase):
    def test_detection_sample_sizes(self):
        self.assertEqual(ms.n_to_detect(0.20), 14)
        self.assertEqual(ms.n_to_detect(0.05), 59)
        self.assertEqual(ms.n_to_detect(0.10), 29)
        self.assertGreaterEqual(ms.prob_detect(0.20, 14), 0.95)
        self.assertLess(ms.prob_detect(0.20, 13), 0.95)

    def test_ten_interviews_see_a_quarter_prevalence_trait(self):
        self.assertAlmostEqual(ms.min_detectable_prevalence(10), 1 - 0.05 ** 0.1, places=12)
        self.assertAlmostEqual(ms.min_detectable_prevalence(10), 0.2589, places=4)
        self.assertGreaterEqual(ms.prob_detect(ms.min_detectable_prevalence(10), 10), 0.95 - 1e-12)


class DesignEffect(unittest.TestCase):
    def test_formula(self):
        self.assertAlmostEqual(ms.design_effect(10, 0.1), 1.9)
        self.assertEqual(ms.design_effect(1, 0.7), 1.0)
        self.assertEqual(ms.design_effect(25, 0.0), 1.0)

    def test_wilson_published_value_and_degenerate_adjustment(self):
        lo, hi = ms.wilson(5, 10)
        self.assertAlmostEqual(lo, 0.2366, places=4)
        self.assertAlmostEqual(hi, 0.7634, places=4)
        self.assertEqual(ms.wilson_deff(5, 10, 10, 0.0), ms.wilson(5, 10))

    def test_adjustment_widens_the_interval(self):
        lo0, hi0 = ms.wilson_deff(50, 100, 10, 0.0)
        lo1, hi1 = ms.wilson_deff(50, 100, 10, 0.1)
        self.assertLess(lo1, lo0)
        self.assertGreater(hi1, hi0)

    def test_generator_matches_beta_binomial_moments(self):
        ks = ms.sample_cluster_counts(0.5, 10, 10, 0.1, reps=6000, seed=2)
        mean = sum(ks) / len(ks)
        var = sum((k - mean) ** 2 for k in ks) / (len(ks) - 1)
        self.assertAlmostEqual(mean, 50.0, delta=0.5)
        self.assertAlmostEqual(var, 100 * 0.25 * 1.9, delta=47.5 * 0.08)

    def test_clustering_breaks_the_naive_interval_and_the_adjustment_repairs_it(self):
        indep = ms.simulate_cluster_coverage(0.5, 100, 1, 0.0, reps=2000, seed=11)
        self.assertGreaterEqual(indep["naive_exact"], 0.95)
        bad = ms.simulate_cluster_coverage(0.5, 10, 10, 0.20, reps=2000, seed=11)
        self.assertLess(bad["naive_exact"], 0.85)
        self.assertGreater(bad["design_effect_wilson"], 0.92)
        self.assertLess(bad["design_effect_wilson"], 0.98)


class TwoGroups(unittest.TestCase):
    def test_tea_tasting_table(self):
        self.assertAlmostEqual(ms.fisher_exact(3, 1, 1, 3), 34 / 70, places=12)

    def test_identical_groups_and_symmetries(self):
        self.assertAlmostEqual(ms.fisher_exact(10, 10, 10, 10), 1.0, places=12)
        self.assertAlmostEqual(ms.fisher_exact(8, 2, 3, 7), ms.fisher_exact(3, 7, 8, 2), places=12)
        self.assertAlmostEqual(ms.fisher_exact(8, 2, 3, 7), ms.fisher_exact(8, 3, 2, 7), places=12)

    @needs_scipy
    def test_against_scipy_on_random_tables(self):
        rng = random.Random(3)
        worst = 0.0
        for _ in range(300):
            a, b, c, d = (rng.randint(0, 40) for _ in range(4))
            if a + b == 0 or c + d == 0:
                continue
            worst = max(worst, abs(ms.fisher_exact(a, b, c, d) - sps.fisher_exact([[a, b], [c, d]])[1]))
        self.assertLess(worst, 1e-9)

    def test_type_one_error_never_exceeds_alpha(self):
        for n in (20, 30):
            for p in (0.2, 0.5):
                self.assertLessEqual(ms.fisher_power(p, p, n), 0.05 + 1e-12)

    def test_exact_power_matches_a_simulation_of_the_same_test(self):
        n, p1, p2 = 60, 0.5, 0.3
        rng = random.Random(5)
        reps, rejects = 3000, 0
        for _ in range(reps):
            x1 = sum(rng.random() < p1 for _ in range(n))
            x2 = sum(rng.random() < p2 for _ in range(n))
            rejects += ms.fisher_exact(x1, n - x1, x2, n - x2) <= 0.05
        self.assertAlmostEqual(ms.fisher_power(p1, p2, n), rejects / reps, delta=0.03)

    def test_fast_exact_power_equals_the_brute_force_definition(self):
        # Reference: enumerate every outcome pair and call fisher_exact on it (O(n^3)).
        def brute(p1, p2, n1, n2):
            pm1 = [ms.binom_pmf(x, n1, p1) for x in range(n1 + 1)]
            pm2 = [ms.binom_pmf(x, n2, p2) for x in range(n2 + 1)]
            return math.fsum(w1 * w2 for x1, w1 in enumerate(pm1) for x2, w2 in enumerate(pm2)
                             if ms.fisher_exact(x1, n1 - x1, x2, n2 - x2) <= 0.05)
        for p1, p2, n1, n2 in [(0.5, 0.3, 20, 20), (0.5, 0.3, 45, 45), (0.6, 0.2, 15, 15),
                               (0.5, 0.3, 30, 50), (0.1, 0.1, 25, 25), (0.9, 0.5, 12, 18), (0.5, 0.3, 60, 60)]:
            self.assertAlmostEqual(ms.fisher_power(p1, p2, n1, n2), brute(p1, p2, n1, n2), places=12,
                                   msg=(p1, p2, n1, n2))

    def test_the_normal_approximation_is_the_textbook_formula_and_is_not_enough(self):
        self.assertEqual(ms.normal_n_per_arm(0.5, 0.3), 91)
        self.assertEqual(ms.normal_n_per_arm(0.5, 0.4), 385)
        z = 1.959963984540054 + 0.8416212335729143
        self.assertEqual(ms.normal_n_per_arm(0.5, 0.3), math.ceil(z * z * (0.25 + 0.21) / 0.04))
        self.assertLess(ms.fisher_power(0.5, 0.3, 91), 0.80)        # 91 per arm is short for the exact test

    def test_a_ten_point_drop_needs_hundreds_per_price(self):
        self.assertLess(ms.fisher_power(0.5, 0.4, 403), 0.80)
        self.assertGreaterEqual(ms.fisher_power(0.5, 0.4, 404), 0.80)
        self.assertEqual(ms.n_per_arm_for_power(0.5, 0.4, start=270, stop=900), 404)

    def test_sample_size_for_half_vs_thirty_percent(self):
        # Textbook normal approximation gives about 91 per arm; the exact test needs more.
        self.assertLess(ms.fisher_power(0.5, 0.3, 101), 0.80)
        self.assertGreaterEqual(ms.fisher_power(0.5, 0.3, 102), 0.80)
        self.assertEqual(ms.n_per_arm_for_power(0.5, 0.3), 102)
        self.assertAlmostEqual(ms.fisher_power(0.5, 0.3, 93), 0.7511, places=3)


class PairedAnswers(unittest.TestCase):
    def test_closed_forms(self):
        self.assertEqual(ms.mcnemar_exact(0, 0), 1.0)
        self.assertEqual(ms.mcnemar_exact(5, 5), 1.0)
        self.assertAlmostEqual(ms.mcnemar_exact(10, 0), 2 * 0.5 ** 10, places=15)
        self.assertEqual(ms.mcnemar_exact(3, 12), ms.mcnemar_exact(12, 3))
        with self.assertRaises(ValueError):
            ms.mcnemar_exact(-1, 2)

    @needs_scipy
    def test_against_scipy_binomial_test(self):
        for b, c in [(3, 12), (20, 31), (1, 9), (40, 41), (0, 7)]:
            ref = sps.binomtest(min(b, c), b + c, 0.5).pvalue
            self.assertAlmostEqual(ms.mcnemar_exact(b, c), ref, places=12)


class Ratio(unittest.TestCase):
    def test_point_estimate_and_determinism(self):
        nums, dens = [1, 0, 2, 0, 3], [10, 10, 10, 10, 10]
        a = ms.bootstrap_ratio(nums, dens, reps=500, seed=4)
        self.assertAlmostEqual(a[0], 6 / 50)
        self.assertLessEqual(a[1], a[0])
        self.assertGreaterEqual(a[2], a[0])
        self.assertEqual(a, ms.bootstrap_ratio(nums, dens, reps=500, seed=4))

    def test_identical_respondents_give_a_degenerate_interval(self):
        est, lo, hi = ms.bootstrap_ratio([2] * 8, [10] * 8, reps=200)
        self.assertEqual((est, lo, hi), (0.2, 0.2, 0.2))

    def test_respondents_without_a_denominator_are_dropped(self):
        self.assertAlmostEqual(ms.bootstrap_ratio([1, 5], [10, 0], reps=100)[0], 0.1)
        with self.assertRaises(ValueError):
            ms.bootstrap_ratio([1], [0])


class Proportion(unittest.TestCase):
    def test_width_flag(self):
        self.assertTrue(ms.proportion(10, 20)["wide"])
        self.assertFalse(ms.proportion(55, 110)["wide"])
        r = ms.proportion(41, 97)
        self.assertAlmostEqual(r["margin"], 0.1045, places=3)

    def test_the_width_threshold_is_a_parameter(self):
        self.assertTrue(ms.proportion(10, 20, wide_margin=0.15)["wide"])      # margin about 0.23
        self.assertFalse(ms.proportion(10, 20, wide_margin=0.30)["wide"])
        self.assertTrue(ms.proportion(55, 110, wide_margin=0.05)["wide"])     # margin about 0.095


class WilsonInterval(unittest.TestCase):
    # Reference values from scipy.stats.binomtest(k, n).proportion_ci(method="wilson"), 4 decimals.
    # Most are far from one half on purpose: at k = n/2 the interval is symmetric and a missing
    # centre shift goes unnoticed (found by the mutation check).
    REFERENCE = {(0, 10): (0.0, 0.2775), (1, 10): (0.0179, 0.4042), (1, 20): (0.0089, 0.2361),
                 (3, 25): (0.0417, 0.2996), (9, 10): (0.5958, 0.9821), (17, 60): (0.1851, 0.4077),
                 (2, 97): (0.0057, 0.0721), (41, 97): (0.3292, 0.5221)}

    def test_published_reference_values(self):
        for (k, n), (lo, hi) in self.REFERENCE.items():
            got = ms.wilson(k, n)
            self.assertAlmostEqual(got[0], lo, places=4, msg=(k, n))
            self.assertAlmostEqual(got[1], hi, places=4, msg=(k, n))

    def test_mirror_symmetry_and_ordering(self):
        for k, n in [(1, 10), (3, 25), (17, 60)]:
            lo, hi = ms.wilson(k, n)
            lo2, hi2 = ms.wilson(n - k, n)
            self.assertAlmostEqual(lo, 1 - hi2, places=12)
            self.assertAlmostEqual(hi, 1 - lo2, places=12)
            self.assertLess(lo, k / n)
            self.assertGreater(hi, k / n)

    def test_the_level_changes_the_width(self):
        w95 = ms.wilson(17, 60, 0.95)
        w90 = ms.wilson(17, 60, 0.90)
        self.assertLess(w95[0], w90[0])
        self.assertGreater(w95[1], w90[1])
        self.assertAlmostEqual(ms.wilson(17, 60, 0.90)[1], 0.3869, places=3)

    @needs_scipy
    def test_against_scipy_on_a_grid(self):
        worst = 0.0
        for n in (5, 12, 30, 80, 200):
            for k in range(n + 1):
                ref = sps.binomtest(k, n).proportion_ci(confidence_level=0.95, method="wilson")
                lo, hi = ms.wilson(k, n)
                worst = max(worst, abs(lo - ref.low), abs(hi - ref.high))
        self.assertLess(worst, 1e-9)


class SearchGuards(unittest.TestCase):
    """n_for_margin refuses instead of returning a number it has not earned."""

    def test_a_search_range_that_is_too_small_is_refused_with_its_own_message(self):
        with mock.patch.object(ms, "normal_n_for_margin", return_value=10):
            with self.assertRaisesRegex(ValueError, "upper search bound"):
                ms.n_for_margin(0.10)

    def test_a_margin_that_rises_again_above_the_answer_is_refused(self):
        def blip(n, conf=0.95):
            return 0.20 if n < 60 or n == 65 else 0.05
        with mock.patch.object(ms, "worst_case_margin", blip), \
                mock.patch.object(ms, "normal_n_for_margin", return_value=72):
            with self.assertRaisesRegex(ValueError, "rises again"):
                ms.n_for_margin(0.10)

    def test_the_same_margins_without_the_blip_give_the_first_passing_n(self):
        def clean(n, conf=0.95):
            return 0.20 if n < 60 else 0.05
        with mock.patch.object(ms, "worst_case_margin", clean), \
                mock.patch.object(ms, "normal_n_for_margin", return_value=72):
            self.assertEqual(ms.n_for_margin(0.10), 60)

    def test_the_lookahead_window_is_the_one_asked_for(self):
        def late_blip(n, conf=0.95):
            return 0.20 if n < 60 or n == 95 else 0.05
        with mock.patch.object(ms, "worst_case_margin", late_blip), \
                mock.patch.object(ms, "normal_n_for_margin", return_value=72):
            self.assertEqual(ms.n_for_margin(0.10, lookahead=30), 60)          # 95 is beyond 60 + 30
            with self.assertRaisesRegex(ValueError, "rises again"):
                ms.n_for_margin(0.10, lookahead=40)


class BootstrapPercentiles(unittest.TestCase):
    def test_the_interval_is_the_2_5_and_97_5_percentiles_of_a_known_distribution(self):
        # 20 respondents with 1 of 1 and 20 with 0 of 1. The pooled ratio of a resample of 40
        # respondents is Binomial(40, 1/2) / 40, whose exact quantiles are known:
        #   P(X <= 13) = 0.0192 < 0.025 <= P(X <= 14) = 0.0403   -> lower end 14 / 40
        #   P(X <= 14) = 0.0403 < 0.05  <= P(X <= 15) = 0.0769   -> a 90% interval would give 15 / 40
        est, lo, hi = ms.bootstrap_ratio([1] * 20 + [0] * 20, [1] * 40, reps=20000, seed=1)
        self.assertEqual(est, 0.5)
        self.assertEqual((lo, hi), (0.35, 0.65))

    def test_the_stated_level_moves_the_interval(self):
        args = ([1] * 20 + [0] * 20, [1] * 40)
        _, lo95, hi95 = ms.bootstrap_ratio(*args, reps=20000, seed=1, conf=0.95)
        _, lo90, hi90 = ms.bootstrap_ratio(*args, reps=20000, seed=1, conf=0.90)
        self.assertEqual((lo90, hi90), (0.375, 0.625))
        self.assertLess(lo95, lo90)
        self.assertGreater(hi95, hi90)


class FisherSmallTables(unittest.TestCase):
    def test_every_table_with_arms_up_to_eight_equals_exact_rational_arithmetic(self):
        # Independent reference: math.comb and Fractions, no logarithms. Tiny tables are where
        # a wrong support range shows up (a wrong lower end changes p by up to 5e-7 here).
        def exact(a, b, c, d):
            n1, n2, k = a + b, c + d, a + c
            total = comb_total = math.comb(n1 + n2, k)
            pm = lambda x: Fraction(math.comb(n1, x) * math.comb(n2, k - x), comb_total)  # noqa: E731
            p_obs = pm(a)
            tol = p_obs * (1 + Fraction(1, 10 ** 7))
            return float(sum(pm(x) for x in range(max(0, k - n2), min(k, n1) + 1) if pm(x) <= tol))
        # The log-factorial table is global and grows with use. Start from an empty one and an empty
        # cache: with a long table left over from other tests, an index that falls outside the support
        # wraps to a huge factorial and contributes nothing, which hides the very error under test.
        tables = worst = 0
        ms.fisher_exact.cache_clear()
        with mock.patch.object(ms, "_LF", [0.0]):
            for n1 in range(1, 9):
                for n2 in range(1, 9):
                    for a in range(n1 + 1):
                        for c in range(n2 + 1):
                            table = (a, n1 - a, c, n2 - c)
                            worst = max(worst, abs(ms.fisher_exact(*table) - exact(*table)))
                            tables += 1
        ms.fisher_exact.cache_clear()
        self.assertEqual(tables, 1936)
        self.assertLess(worst, 1e-12)


class InputChecks(unittest.TestCase):
    def test_impossible_counts_are_refused_not_computed(self):
        for k, n in [(11, 10), (-1, 10), (0, 0), (1.5, 10), (3, 10.5)]:
            with self.assertRaises(ValueError, msg=(k, n)):
                ms.cp_interval(k, n)
            with self.assertRaises(ValueError, msg=(k, n)):
                ms.cp_lower_one_sided(k, n)

    def test_impossible_tables_are_refused(self):
        for table in [(-1, 3, 2, 2), (0, 0, 0, 0), (2, -2, 1, 1)]:
            with self.assertRaises(ValueError, msg=table):
                ms.fisher_exact(*table)


class EdgeCases(unittest.TestCase):
    def test_binomial_probabilities_at_the_edges(self):
        self.assertEqual(ms.binom_pmf(0, 5, 0.0), 1.0)
        self.assertEqual(ms.binom_pmf(1, 5, 0.0), 0.0)
        self.assertEqual(ms.binom_pmf(5, 5, 1.0), 1.0)
        self.assertEqual(ms.binom_pmf(4, 5, 1.0), 0.0)
        self.assertEqual((ms.binom_pmf(-1, 5, 0.3), ms.binom_pmf(6, 5, 0.3)), (0.0, 0.0))
        self.assertEqual((ms.binom_cdf(-1, 5, 0.3), ms.binom_cdf(5, 5, 0.3), ms.binom_cdf(7, 5, 0.3)), (0.0, 1.0, 1.0))
        self.assertEqual((ms.binom_sf(0, 5, 0.3), ms.binom_sf(-2, 5, 0.3), ms.binom_sf(6, 5, 0.3)), (1.0, 1.0, 0.0))
        self.assertAlmostEqual(ms.binom_cdf(2, 5, 0.3) + ms.binom_sf(3, 5, 0.3), 1.0, places=12)

    def test_inputs_that_cannot_be_computed_are_refused(self):
        with self.assertRaises(ValueError):
            ms.wilson(1, 0)
        with self.assertRaises(ValueError):
            ms.wilson(1, -3)
        for p_max, k in [(0.0, 0), (1.0, 0), (0.1, -1)]:
            with self.assertRaises(ValueError, msg=(p_max, k)):
                ms.required_n(p_max, k)
        for mu, rho in [(0.0, 0.1), (1.0, 0.1), (0.5, 1.0), (0.5, -0.1)]:
            with self.assertRaises(ValueError, msg=(mu, rho)):
                ms.sample_cluster_counts(mu, 5, 5, rho, reps=2)
        with self.assertRaises(ValueError):
            ms.n_per_arm_for_power(0.5, 0.49, start=10, stop=40)


if __name__ == "__main__":
    unittest.main(verbosity=2)
