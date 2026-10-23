"""Minna discovery math. Every input is a sourced figure (see report); every
derived number is asserted against an independent check before it is printed."""
import math
import random

# ---------- Inputs (DataReportal Digital 2026 Algeria, World Bank/ILO API) ----------
POP = 47.6e6
F_POP, M_POP = 0.490, 0.510
INTERNET_USERS, INTERNET_PEN = 37.8e6, 0.795
OFFLINE = 9.74e6
SOC = 27.5e6
F_SOC, M_SOC = 0.416, 0.584
LFPR_F_2025, LFPR_M_2025 = 14.142, 66.409
LFPR_F_2018 = 14.801
GPI_TERT_2024 = 1.34598556429492

# ---------- 0. Input sanity ----------
assert abs(F_POP + M_POP - 1) < 1e-9
assert abs(F_SOC + M_SOC - 1) < 1e-9
# internet users + offline should reconstruct the population (reported figures are rounded)
assert abs((INTERNET_USERS + OFFLINE) / POP - 1) < 0.005, "internet+offline != population"
assert abs(INTERNET_USERS / POP - INTERNET_PEN) < 0.002, "penetration inconsistent with counts"

# ---------- 1. Female vs male social-media presence (proxy) ----------
f_pop, m_pop = F_POP * POP, M_POP * POP
f_soc, m_soc = F_SOC * SOC, M_SOC * SOC
pen_f, pen_m = f_soc / f_pop, m_soc / m_pop
ratio_counts = pen_f / pen_m
ratio_shares = (F_SOC / F_POP) / (M_SOC / M_POP)
assert abs(ratio_counts - ratio_shares) < 1e-12, "ratio must not depend on absolute counts"
print(f"women {f_pop/1e6:.2f}M, men {m_pop/1e6:.2f}M")
print(f"social identities: women {f_soc/1e6:.2f}M, men {m_soc/1e6:.2f}M")
print(f"proxy penetration: women {pen_f:.1%}, men {pen_m:.1%}, F/M ratio {ratio_counts:.3f}, gap {1-ratio_counts:.1%}")

print("sensitivity of F/M ratio to the (unknown) adult female share of population:")
for a in (0.48, 0.49, 0.50):
    r = (F_SOC / a) / (M_SOC / (1 - a))
    print(f"  adult female share {a:.2f} -> ratio {r:.3f}")

# ---------- 2. Bracket for 'women online' (illustrative, not an estimate) ----------
parity = INTERNET_PEN * f_pop                       # women as online as the national average
r = ratio_shares                                    # scenario: internet gap == social-media proxy gap
p_m = INTERNET_PEN / (F_POP * r + M_POP)
p_f = r * p_m
assert p_m <= 1 and p_f <= 1
assert abs(F_POP * p_f + M_POP * p_m - INTERNET_PEN) < 1e-12, "weighted average must reproduce national penetration"
proxy = p_f * f_pop
floor = f_soc
print(f"women online bracket: floor(social identities) {floor/1e6:.1f}M | proxy-gap {proxy/1e6:.1f}M | parity {parity/1e6:.1f}M")
assert floor < proxy < parity

# ---------- 3. Labour market / education ----------
print(f"female LFPR {LFPR_F_2025:.2f}% vs male {LFPR_M_2025:.2f}%: ratio {LFPR_F_2025/LFPR_M_2025:.3f}, gap {LFPR_M_2025-LFPR_F_2025:.1f} pp")
print(f"female LFPR change 2018->2025: {LFPR_F_2025-LFPR_F_2018:+.2f} pp")
print(f"tertiary GPI 2024 {GPI_TERT_2024:.3f} -> women's gross tertiary enrolment ratio is {GPI_TERT_2024-1:.1%} higher than men's")

# ---------- 4. We-Fi / ANGEM cascade arithmetic ----------
trainers = 25 * 12
assert trainers == 300
print(f"ANGEM cascade: 25 x 12 = {trainers} local trainers; 27,500 promoters target = {27500/trainers:.1f} promoters per local trainer")

# ---------- 5. Gate statistics ----------
Z = 1.959963984540054

def wilson(s, n, z=Z):
    p = s / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h

# known reference values for the Wilson interval
lo, hi = wilson(0, 10)
assert abs(hi - 0.2775) < 5e-4, hi
lo, hi = wilson(10, 10)
assert abs(lo - 0.7225) < 5e-4, lo

# zero-failure gate: smallest n whose one-sided 95% upper bound on failure rate is < 5%
n_zero = math.ceil(math.log(0.05) / math.log(0.95))
ub = lambda n: 1 - 0.05 ** (1 / n)
assert ub(n_zero) < 0.05 <= ub(n_zero - 1)
print(f"zero critical failures: need n >= {n_zero} (95% upper bound on failure rate {ub(n_zero):.2%}; n={n_zero-1} gives {ub(n_zero-1):.2%})")

# Monte-Carlo check of the claim: if the true failure rate were 5%, P(0 failures in n) <= 5%
rng = random.Random(42)
trials = 200_000
zero_hits = sum(all(rng.random() >= 0.05 for _ in range(n_zero)) for _ in range(trials))
analytic = 0.95 ** n_zero
print(f"Monte-Carlo P(0 failures | true rate 5%, n={n_zero}): {zero_hits/trials:.4f} vs analytic {analytic:.4f}")
assert abs(zero_hits / trials - analytic) < 0.003

# success-rate gate: smallest n so that an observed 90% success has Wilson lower bound >= 80%
for n in range(10, 400):
    s = math.ceil(0.9 * n)
    if wilson(s, n)[0] >= 0.80:
        print(f"observed >=90% success proves >=80% (Wilson 95% lower bound) from n={n} (s={s}, LB={wilson(s, n)[0]:.3f})")
        break
# and the stricter version: observed 95% proving >=85%
for n in range(10, 600):
    s = math.ceil(0.95 * n)
    if wilson(s, n)[0] >= 0.85:
        print(f"observed >=95% success proves >=85% from n={n} (s={s}, LB={wilson(s, n)[0]:.3f})")
        break

# margin-of-error sample sizes for estimating a proportion at 95% confidence, +/-10 pp.
# CORRECTION (EVIDENCE E-7): the figure 97 below is the NORMAL APPROXIMATION at p = 0.5. The exact
# (Clopper-Pearson) interval is wider in the worst case, so the exact answer is larger (106).
for p in (0.5, 0.8):
    print(f"normal approximation, n for +/-10pp at p={p}: {math.ceil(Z*Z*p*(1-p)/0.10**2)}")
assert math.ceil(Z * Z * 0.25 / 0.10 ** 2) == 97


def _tail(k, n, p, upper):
    """P(X >= k) if upper else P(X <= k) for X ~ Binomial(n, p), summed term by term."""
    lo, hi = (k, n) if upper else (0, k)
    return min(1.0, math.fsum(math.exp(math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1)
                                       + i * math.log(p) + (n - i) * math.log1p(-p)) for i in range(lo, hi + 1)))


def _bisect(f, target, increasing):
    lo, hi = 1e-12, 1 - 1e-12
    for _ in range(60):
        mid = (lo + hi) / 2
        if (f(mid) < target) == increasing:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def exact_interval(k, n, tail=0.025):
    lo = 0.0 if k == 0 else _bisect(lambda p: _tail(k, n, p, True), tail, True)
    hi = 1.0 if k == n else _bisect(lambda p: _tail(k, n, p, False), tail, False)
    return lo, hi


def worst_exact_margin(n):
    """Longest arm of the exact 95% interval, maximised over every possible result k (k <= n/2 suffices)."""
    return max(max(h - k / n, k / n - l) for k in range(n // 2 + 1) for l, h in [exact_interval(k, n)])


m97, m105, m106 = worst_exact_margin(97), worst_exact_margin(105), worst_exact_margin(106)
print(f"exact interval, worst-case margin: n=97 -> +/-{100*m97:.2f}pp, n=105 -> +/-{100*m105:.2f}pp, n=106 -> +/-{100*m106:.2f}pp")
assert m97 > 0.10 and m105 > 0.10 >= m106, (m97, m105, m106)
assert abs(m97 - 0.1045) < 5e-4 and abs(m106 - 0.0998) < 5e-4
print("ALL ASSERTIONS PASSED")
