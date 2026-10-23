"""Minna build-gate sample sizes. One method everywhere: exact binomial, one-sided, alpha = 5%.

A gate passes only if, were the TRUE failure rate equal to the tolerated maximum p_max, observing <= k
failures in n trials would happen with probability <= 5%. The guarantee holds only if trials are
independent and drawn from the distribution you care about; it says nothing about any other one
(a redactor tested on its own templates certifies the templates, not real text).

Every printed number is asserted against an independent computation (closed form, hand-checkable
values, or Monte-Carlo) before the script reports success."""
import math
import random

ALPHA = 0.05
KS = (0, 1, 2, 3, 4)
P_MAXES = (0.20, 0.10, 0.05, 0.02, 0.01, 0.005, 0.001)


def binom_cdf(k, n, p):
    """P(X <= k) for X ~ Binomial(n, p), exact."""
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


def tail_ge(s, n, p):
    """P(X >= s) for X ~ Binomial(n, p), exact."""
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(s, n + 1))


def min_n(p_max, k, alpha=ALPHA, n_cap=20000):
    """Smallest n such that P(X <= k | p_max) <= alpha."""
    for n in range(max(k + 1, 1), n_cap):
        if binom_cdf(k, n, p_max) <= alpha:
            return n
    raise ValueError("n_cap too small")


# ---- closed form for k = 0 must agree with the exact search ----
for p in P_MAXES:
    closed = math.ceil(math.log(ALPHA) / math.log(1 - p))
    assert closed == min_n(p, 0), (p, closed, min_n(p, 0))

# ---- hand-checkable reference values ----
assert 0.8**14 <= 0.05 < 0.8**13        # 14 clean trials prove failure < 20%
assert 0.9**29 <= 0.05 < 0.9**28        # 29 clean trials prove failure < 10%
assert 0.95**59 <= 0.05 < 0.95**58      # 59: the classic rule of three (3/n ~ 5%)
assert 0.99**299 <= 0.05 < 0.99**298    # 299 clean trials prove failure < 1%
assert min_n(0.20, 0) == 14 and min_n(0.10, 0) == 29 and min_n(0.05, 0) == 59 and min_n(0.01, 0) == 299

print("Samples n needed so that <=k observed failures proves true failure rate < p_max (95% confidence):")
print(f"{'p_max':<10}" + "".join(f"{'k=' + str(k):>8}" for k in KS))
table = {}
for p in P_MAXES:
    row = [min_n(p, k) for k in KS]
    table[p] = row
    print(f"{p:<10.3f}" + "".join(f"{v:>8}" for v in row))

# sanity: allowing more failures never needs fewer samples; a tighter tolerance never needs fewer samples
for p, row in table.items():
    assert all(a < b for a, b in zip(row, row[1:])), (p, row)
ps = sorted(table)  # ascending p_max: ps[0] is the tightest tolerance
for tight, loose in zip(ps, ps[1:]):
    for i in range(len(KS)):
        assert table[tight][i] >= table[loose][i], (tight, loose, i)

# ---- Monte-Carlo check of one exact claim: p=1%, k=1, n=473 -> P(<=1 failure) <= 5% ----
n_chk = table[0.01][1]
rng = random.Random(7)
trials = 60_000
hits = 0
for _ in range(trials):
    fails = 0
    for _ in range(n_chk):
        if rng.random() < 0.01:
            fails += 1
            if fails > 1:
                break
    if fails <= 1:
        hits += 1
analytic = binom_cdf(1, n_chk, 0.01)
print(f"Monte-Carlo P(<=1 failure | p=1%, n={n_chk}): {hits/trials:.4f} vs exact {analytic:.4f}")
assert abs(hits / trials - analytic) < 0.004
assert analytic <= ALPHA < binom_cdf(1, n_chk - 1, 0.01)

# ---- pilot of n users against the hypothesis "weekly retention = 50%" (placeholder: set YOUR threshold first) ----
# hand-checkable reference values for n=15, p=0.5 (denominator 2**15 = 32768)
assert abs(binom_cdf(3, 15, 0.5) - 576 / 32768) < 1e-12
assert abs(binom_cdf(4, 15, 0.5) - 1941 / 32768) < 1e-12
assert abs(tail_ge(12, 15, 0.5) - 576 / 32768) < 1e-12
assert abs(tail_ge(11, 15, 0.5) - 1941 / 32768) < 1e-12

print()
print("Pilot decision thresholds vs a 50% weekly-retention hypothesis (one-sided 5% each way):")
print(f"{'users':<8}{'reject >=50% if retained <=':>30}{'reject <=50% if retained >=':>30}{'inconclusive':>16}")
for n in (15, 30, 60):
    kill = max(s for s in range(n + 1) if binom_cdf(s, n, 0.5) <= ALPHA)
    prove = min(s for s in range(n + 1) if tail_ge(s, n, 0.5) <= ALPHA)
    assert kill < prove
    print(f"{n:<8}{kill:>30}{prove:>30}{f'{kill+1}-{prove-1}':>16}")
    if n == 15:
        assert (kill, prove) == (3, 12)

print("ALL ASSERTIONS PASSED")
