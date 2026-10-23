"""minna_stats: exact small-sample statistics for Minna's field research.

Standard library only. Each public function is checked in tests/test_stats.py
against closed forms, against the gate table in the build plan, and (when scipy
is installed) against scipy.

Scope warning. Every interval here describes sampling noise for a SIMPLE RANDOM
sample. A convenience, referral or training-cascade sample is not one. See
design_effect() and simulate_cluster_coverage() for how far the stated
confidence can fall, and read the result as "within this recruitment channel".
"""
from __future__ import annotations

import bisect
import math
import random
from functools import lru_cache
from statistics import NormalDist

# --------------------------------------------------------------------------
# Binomial core
# --------------------------------------------------------------------------


_LF = [0.0]  # _LF[i] = lgamma(i + 1) = log(i!), grown on demand


def _log_fact(n: int) -> list[float]:
    while len(_LF) <= n:
        _LF.append(math.lgamma(len(_LF) + 1))
    return _LF


def _log_pmf(k: int, n: int, p: float) -> float:
    if k < 0 or k > n:
        return -math.inf
    if p <= 0.0:
        return 0.0 if k == 0 else -math.inf
    if p >= 1.0:
        return 0.0 if k == n else -math.inf
    lf = _log_fact(n)
    return lf[n] - lf[k] - lf[n - k] + k * math.log(p) + (n - k) * math.log1p(-p)


def binom_pmf(k: int, n: int, p: float) -> float:
    return math.exp(_log_pmf(k, n, p))


def binom_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p)."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    return min(1.0, math.fsum(binom_pmf(i, n, p) for i in range(k + 1)))


def binom_sf(k: int, n: int, p: float) -> float:
    """P(X >= k) for X ~ Binomial(n, p)."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    return min(1.0, math.fsum(binom_pmf(i, n, p) for i in range(k, n + 1)))


def _check(k: int, n: int) -> None:
    if not (isinstance(k, int) and isinstance(n, int)) or n < 1 or not 0 <= k <= n:
        raise ValueError(f"need integers with 0 <= k <= n and n >= 1, got k={k!r}, n={n!r}")


def _solve(f, target: float, increasing: bool, iters: int = 60) -> float:
    # 60 halvings of [0, 1] leave an interval of 2**-60, below double precision.
    lo, hi = 0.0, 1.0
    for _ in range(iters):
        mid = (lo + hi) / 2
        if (f(mid) < target) == increasing:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# --------------------------------------------------------------------------
# Exact (Clopper-Pearson) intervals. `tail` is the probability left in ONE tail.
# --------------------------------------------------------------------------


@lru_cache(maxsize=None)
def cp_lower(k: int, n: int, tail: float) -> float:
    """p such that P(X >= k | p) = tail; 0 when k == 0."""
    _check(k, n)
    if k == 0:
        return 0.0
    return _solve(lambda p: binom_sf(k, n, p), tail, increasing=True)


@lru_cache(maxsize=None)
def cp_upper(k: int, n: int, tail: float) -> float:
    """p such that P(X <= k | p) = tail; 1 when k == n."""
    _check(k, n)
    if k == n:
        return 1.0
    return _solve(lambda p: binom_cdf(k, n, p), tail, increasing=False)


def cp_interval(k: int, n: int, conf: float = 0.95) -> tuple[float, float]:
    """Two-sided exact interval at level `conf`."""
    tail = round((1 - conf) / 2, 12)
    return cp_lower(k, n, tail), cp_upper(k, n, tail)


def cp_lower_one_sided(k: int, n: int, conf: float = 0.95) -> float:
    """With probability >= conf the true proportion is at least this."""
    return cp_lower(k, n, round(1 - conf, 12))


def cp_upper_one_sided(k: int, n: int, conf: float = 0.95) -> float:
    """With probability >= conf the true proportion is at most this."""
    return cp_upper(k, n, round(1 - conf, 12))


def wilson(k: float, n: float, conf: float = 0.95) -> tuple[float, float]:
    """Wilson score interval. k and n may be non-integers (effective sample sizes)."""
    if n <= 0:
        raise ValueError("n must be positive")
    z = NormalDist().inv_cdf(1 - (1 - conf) / 2)
    ph = k / n
    denom = 1 + z * z / n
    centre = (ph + z * z / (2 * n)) / denom
    half = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


# --------------------------------------------------------------------------
# Sample sizes
# --------------------------------------------------------------------------


def required_n(p_max: float, k: int, alpha: float = 0.05) -> int:
    """Smallest n such that seeing at most k failures proves failure rate < p_max
    (exact binomial, one-sided). This is the build plan's gate table."""
    if not 0 < p_max < 1 or k < 0:
        raise ValueError("need 0 < p_max < 1 and k >= 0")
    n = k + 1
    while binom_cdf(k, n, p_max) > alpha:
        n += 1
    return n


def margin_at(n: int, k: int, conf: float = 0.95) -> float:
    """Longer arm of the exact interval for k successes in n."""
    lo, hi = cp_interval(k, n, conf)
    ph = k / n
    return max(hi - ph, ph - lo)


def worst_case_margin(n: int, conf: float = 0.95) -> float:
    """Largest margin over ALL outcomes k = 0..n (the interval for n-k mirrors the
    one for k, so k <= n/2 suffices). The maximum is NOT at k = n/2: it sits near
    k = 0.42 n, so no shortcut window is used."""
    return max(margin_at(n, k, conf) for k in range(0, n // 2 + 1))


def worst_case_k(n: int, conf: float = 0.95) -> int:
    """The k <= n/2 at which worst_case_margin(n) is attained."""
    return max(range(0, n // 2 + 1), key=lambda k: margin_at(n, k, conf))


def n_for_margin(margin: float, conf: float = 0.95, lookahead: int = 30) -> int:
    """Smallest n whose worst-case exact margin is <= `margin`.

    Found by bisection between 20 and 1.25 * the textbook n + 10; the bisection
    has itself evaluated n - 1 and found it above the target (the floor of 20
    aside, which is never an answer for realistic margins). Afterwards the margin
    must stay at or below the target for the next `lookahead` values of n, or the
    call refuses. That the margin falls with n below the answer is assumed by the
    bisection and verified by tests over 60..200, not proven in general. Cost grows
    like n^2 per evaluation: a margin of 0.10 takes seconds, 0.05 takes minutes."""
    lo, hi = 20, math.ceil(normal_n_for_margin(margin, conf) * 1.25) + 10
    if worst_case_margin(hi, conf) > margin:
        raise ValueError("upper search bound too small; margin unusually tight")
    while lo < hi:
        mid = (lo + hi) // 2
        if worst_case_margin(mid, conf) <= margin:
            hi = mid
        else:
            lo = mid + 1
    if any(worst_case_margin(m, conf) > margin for m in range(lo, lo + lookahead + 1)):
        raise ValueError("margin rises again just above the answer; scan linearly")
    return lo


def normal_n_for_margin(margin: float, conf: float = 0.95) -> int:
    """Textbook n = z^2 * 0.25 / margin^2, rounded up. The plan's 'n >= 97' is this."""
    z = NormalDist().inv_cdf(1 - (1 - conf) / 2)
    return math.ceil(z * z * 0.25 / (margin * margin))


# --------------------------------------------------------------------------
# Interview arithmetic (discovery, not prevalence)
# --------------------------------------------------------------------------


def prob_detect(prevalence: float, n: int) -> float:
    """Chance that at least one of n independent interviewees has the trait."""
    return 1 - (1 - prevalence) ** n


def n_to_detect(prevalence: float, conf: float = 0.95) -> int:
    """Smallest n for which a trait with this prevalence is seen at least once
    with probability >= conf."""
    alpha = round(1 - conf, 12)
    n = 1
    while (1 - prevalence) ** n > alpha:
        n += 1
    return n


def min_detectable_prevalence(n: int, conf: float = 0.95) -> float:
    """Smallest prevalence that n interviews see at least once with probability >= conf."""
    return 1 - round(1 - conf, 12) ** (1.0 / n)


# --------------------------------------------------------------------------
# Clustered (referral / cascade) samples
# --------------------------------------------------------------------------


def design_effect(mean_cluster_size: float, icc: float) -> float:
    """Kish design effect for equal clusters: 1 + (m - 1) * rho."""
    return 1 + (mean_cluster_size - 1) * icc


def wilson_deff(k: int, n: int, mean_cluster_size: float, icc: float,
                conf: float = 0.95) -> tuple[float, float]:
    """Wilson interval at the effective sample size n / deff (proportion unchanged)."""
    deff = design_effect(mean_cluster_size, icc)
    return wilson(k / deff, n / deff, conf)


def sample_cluster_counts(mu: float, n_clusters: int, m: int, rho: float,
                          reps: int, seed: int = 1) -> list[int]:
    """`reps` simulated totals k of respondents answering yes, when respondents
    come in n_clusters clusters of size m. Each cluster has its own probability
    theta ~ Beta with mean mu and intra-cluster correlation rho (rho = 0 means
    every theta equals mu); respondents inside a cluster answer independently
    given theta. Theory: Var(k) = n * mu * (1 - mu) * (1 + (m - 1) * rho)."""
    if not 0 < mu < 1 or not 0 <= rho < 1:
        raise ValueError("need 0 < mu < 1 and 0 <= rho < 1")
    rng = random.Random(seed)
    if rho > 0:
        s = (1 - rho) / rho
        a, b = mu * s, (1 - mu) * s
    out = []
    for _ in range(reps):
        k = 0
        for _c in range(n_clusters):
            theta = rng.betavariate(a, b) if rho > 0 else mu
            k += sum(1 for _i in range(m) if rng.random() < theta)
        out.append(k)
    return out


def simulate_cluster_coverage(mu: float, n_clusters: int, m: int, rho: float,
                              reps: int = 2000, conf: float = 0.95, seed: int = 1) -> dict:
    """Share of simulated surveys whose interval contains the true mu, for
    (a) the naive exact interval, which treats all n = n_clusters * m respondents
    as independent, and (b) the Wilson interval at the effective sample size,
    using the TRUE rho (in practice rho is unknown; see the sensitivity table)."""
    n = n_clusters * m
    naive = adjusted = 0
    for k in sample_cluster_counts(mu, n_clusters, m, rho, reps, seed):
        lo, hi = cp_interval(k, n, conf)
        naive += lo <= mu <= hi
        lo, hi = wilson_deff(k, n, m, rho, conf)
        adjusted += lo <= mu <= hi
    return {"naive_exact": naive / reps, "design_effect_wilson": adjusted / reps,
            "n": n, "deff": design_effect(m, rho), "reps": reps}


# --------------------------------------------------------------------------
# Two groups: Fisher exact test and its exact power
# --------------------------------------------------------------------------


@lru_cache(maxsize=None)
def fisher_exact(a: int, b: int, c: int, d: int) -> float:
    """Two-sided p-value for the 2x2 table [[a, b], [c, d]]: the total probability of
    all tables (same margins) that are no more likely than the observed one.
    Same rule and tolerance as scipy.stats.fisher_exact."""
    n1, n2, k = a + b, c + d, a + c
    total = n1 + n2
    if min(a, b, c, d) < 0 or total == 0:
        raise ValueError("counts must be non-negative and not all zero")
    lo, hi = max(0, k - n2), min(k, n1)
    lf = _log_fact(total)
    base = lf[n1] + lf[n2] + lf[k] + lf[total - k] - lf[total]

    def pmf(x: int) -> float:
        # hypergeometric: C(n1, x) * C(n2, k - x) / C(total, k)
        return math.exp(base - lf[x] - lf[n1 - x] - lf[k - x] - lf[n2 - k + x])

    p_obs = pmf(a)
    return min(1.0, math.fsum(p for p in (pmf(x) for x in range(lo, hi + 1))
                              if p <= p_obs * (1 + 1e-7)))


def mcnemar_exact(b: int, c: int) -> float:
    """Exact two-sided p-value for two answers given by the SAME respondents (for
    example 'chose task A' vs 'chose task B' in a pick-two question). b = chose A but
    not B, c = chose B but not A; respondents who chose both or neither carry no
    information. Under 'no difference' each discordant respondent is equally likely
    to be either kind: p = 2 * P(Binomial(b + c, 1/2) <= min(b, c)), capped at 1."""
    if b < 0 or c < 0:
        raise ValueError("counts must be non-negative")
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * binom_cdf(min(b, c), n, 0.5))


@lru_cache(maxsize=None)
def _fisher_rejections(n1: int, n2: int, alpha: float) -> tuple[tuple[int, ...], ...]:
    """For every total s of 'yes' answers, the counts x1 (yes in group 1) at which the
    two-sided Fisher test rejects at `alpha`. One hypergeometric pass per s, using the
    same rule and tolerance as fisher_exact: the p-value of x is the total probability
    of all x' that are no more likely than x (probability <= p(x) * (1 + 1e-7))."""
    total = n1 + n2
    lf = _log_fact(total)
    out = []
    for s in range(total + 1):
        lo, hi = max(0, s - n2), min(s, n1)
        base = lf[n1] + lf[n2] + lf[s] + lf[total - s] - lf[total]
        xs = list(range(lo, hi + 1))
        pm = [math.exp(base - lf[x] - lf[n1 - x] - lf[s - x] - lf[n2 - s + x]) for x in xs]
        order = sorted(range(len(xs)), key=pm.__getitem__)
        sorted_p = [pm[i] for i in order]
        cum, run = [], 0.0
        for v in sorted_p:
            run += v
            cum.append(run)
        rejected = []
        for x, v in zip(xs, pm):
            pos = bisect.bisect_right(sorted_p, v * (1 + 1e-7))
            if min(1.0, cum[pos - 1]) <= alpha:
                rejected.append(x)
        out.append(tuple(rejected))
    return tuple(out)


def fisher_power(p1: float, p2: float, n1: int, n2: int | None = None,
                 alpha: float = 0.05) -> float:
    """Exact probability that the two-sided Fisher test rejects at `alpha` when the
    true rates are p1 and p2 (all outcomes enumerated, no simulation). Cost O(n^2)."""
    n2 = n1 if n2 is None else n2
    pm1 = [binom_pmf(x, n1, p1) for x in range(n1 + 1)]
    pm2 = [binom_pmf(x, n2, p2) for x in range(n2 + 1)]
    return math.fsum(pm1[x1] * pm2[s - x1]
                     for s, xs in enumerate(_fisher_rejections(n1, n2, alpha)) for x1 in xs)


def normal_n_per_arm(p1: float, p2: float, power: float = 0.8, alpha: float = 0.05) -> int:
    """Textbook normal-approximation sample size per group for two proportions
    (no continuity correction). A guide only: the exact test needs more."""
    z = NormalDist().inv_cdf
    n = (z(1 - alpha / 2) + z(power)) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2)) / (p1 - p2) ** 2
    return math.ceil(n)


def n_per_arm_for_power(p1: float, p2: float, power: float = 0.8, alpha: float = 0.05,
                        start: int = 10, stop: int = 400) -> int:
    """First n per arm whose exact power reaches `power`. Exact-test power is
    sawtooth in n, so a slightly larger n can fall back under; see tests."""
    for n in range(start, stop):
        if fisher_power(p1, p2, n, alpha=alpha) >= power:
            return n
    raise ValueError("no n found below stop")


# --------------------------------------------------------------------------
# Ratio of sums with respondents as the unit (for recall-based rates)
# --------------------------------------------------------------------------


def bootstrap_ratio(nums: list[float], dens: list[float], reps: int = 4000,
                    conf: float = 0.95, seed: int = 1) -> tuple[float, float, float]:
    """Pooled ratio sum(nums)/sum(dens) with a percentile interval from resampling
    RESPONDENTS (parcels inside one respondent are not independent). Approximate:
    percentile intervals can undercover when few respondents have non-zero counts."""
    pairs = [(a, b) for a, b in zip(nums, dens) if b > 0]
    if not pairs:
        raise ValueError("no respondent with a positive denominator")
    n = len(pairs)
    est = sum(a for a, _ in pairs) / sum(b for _, b in pairs)
    rng = random.Random(seed)
    vals = []
    for _ in range(reps):
        sa = sb = 0.0
        for _i in range(n):
            a, b = pairs[rng.randrange(n)]
            sa += a
            sb += b
        vals.append(sa / sb)
    vals.sort()
    tail = (1 - conf) / 2
    return est, vals[int(tail * reps)], vals[min(reps - 1, int((1 - tail) * reps))]


def proportion(k: int, n: int, conf: float = 0.95, wide_margin: float = 0.15) -> dict:
    """Point estimate, exact interval and the margin, with a width flag (margin above
    `wide_margin`; the survey passes the value from content/meta.json)."""
    lo, hi = cp_interval(k, n, conf)
    ph = k / n
    margin = max(hi - ph, ph - lo)
    return {"k": k, "n": n, "p": ph, "lo": lo, "hi": hi, "margin": margin,
            "wide": margin > wide_margin}
