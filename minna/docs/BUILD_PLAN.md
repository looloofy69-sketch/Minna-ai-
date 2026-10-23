# Minna — build plan v0.1

Date: 2026-10-12 · Status: M0 complete and verified; M1 not started · Decisions pending: D1–D4 (§7)
Tags: **[E]** established (executed in this repo, or two independent sources) · **[I]** inference · **[H]** hypothesis · **[U]** unknown or unverified.
Every tagged claim has its source in `ASSUMPTION_REGISTER.md` or its run in `EVIDENCE.md`.

## 1. Thesis, and what would falsify it

Thesis **[H]**: an assistant that completes bounded jobs on the user's behalf (not one that only answers) lowers the transaction-cost and skill barriers for Algerian women who are already online and already earning or seeking income.

We stop or pivot if any of these happens:
- interviews in the chosen segment find no repeated, painful task that Minna can complete (checked before M2 is built);
- pilot retention falls at or below the kill threshold in §5 (M4);
- counsel finds the data flow unlawful and no compliant design exists (checked before M3).

## 2. What software can and cannot reduce

| Barrier | Evidence | Software can | Software cannot |
|---|---|---|---|
| Finding customers, marketing | Named by the We-Fi Algeria program [E, one program] | Draft and schedule posts and replies in Darija and French | Beat import competition [E] |
| Order handling, shipping | Courier merchant APIs described in vendor docs [U official] | Order → parcel, status, rate lookup, with approval | Fix refused cash-on-delivery parcels (rate unverified [U]); it can only measure them |
| Skills and know-how | ANGEM cascade: 25 master trainers × 12 local trainers = 300; target 27,500 promoters, about 92 per local trainer [E arithmetic; mechanism not explained] | Guided workflows, plain-language explanations | Replace training programs; partner with them [H] |
| Payments, formalities | An 8-ministry steering committee works on them [E] | Checklists, status explainers | Change regulation. v1 never moves money |
| Connectivity | Exam-period restrictions in 2024 and 2025 [E] | Offline queue, safe retry | Override network restrictions |
| Trust, privacy | Unresearched [U] | Local-first storage, consent, deletion, no data sale | Prove trust; interviews decide |

## 3. Architecture and why

Default for D2: a local-first Android pilot on the extracted core.

```
Surface (Android UI) → AssistantRuntime → control plane (core/) → CapabilityExecutor → connectors (add-ons)
                                               │                                       courier, message drafts, documents
                                               └ Policy → Approval → Egress → Run → Evidence (journal)
Model router → Egress: classify → redact → destination/purpose → allow-listed provider API
```

Principles. Each one is meant to be a test, not a slogan.
1. Model output is never authority. Inherited; all 12 safety-branch mutants are now killed [E].
2. Personal data leaves the device only as redacted or structured payloads to allow-listed hosts. Today the gate checks destination and data class only; redaction is M1 [E].
3. Every external effect has identity, idempotency and a reconciliation path. Inherited and partly tested; the courier connector in M2 is the first real proof.
4. Context is stated, never inferred. "Women's context" means what the user tells Minna (language, business, wilayas served, courier). Nothing is inferred from gender or demographics. Every stored fact is visible, editable and deletable.
5. Add-ons are capabilities with a contract (identity, effect class, scope, approval, idempotency, reconciliation) and ship only if they pass the connector conformance suite (M2). No marketplace in v1.
6. No third-party dependencies in `core/`, so it builds and tests anywhere [E].

Why local-first by default **[I]**: fewer processing obligations than a central store under Law 18-07, whose Art. 44 gates transfers abroad [E, two law-firm summaries]; no backend to operate; it reuses your strongest asset. Costs: Android-only reach (share among target users unknown [U]); background execution and approval UI are open upstream [E].

| Option | Legal footprint | Reach | Build cost | Reuse |
|---|---|---|---|---|
| Android local-first (default) | smallest [I] | Android only [U share] | lowest | highest |
| Web/PWA + server | central store, full controller duties [I] | any phone | highest: backend, authN, multi-tenant hardening (GAP-02/03/04) | core only |
| Messaging bot | platform terms [U] | channel use unverified [U]; restricted during exams [E] | medium | core only |

## 4. Milestones and exit gates

No calendar dates: there is no velocity data yet. M0 supplies the first measurement; re-plan after M1. A milestone is done only when its gate holds and the review protocol (§6) is complete.

| M | Deliverable | Exit gate (all must hold) | Needs |
|---|---|---|---|
| **M0 ✔** | Verified portable core: 15 files byte-identical to upstream @78afd5d; 3 new test files; mutation harness | 43/43 tests on plain JVM; 12/12 mutants killed (6/12 upstream); zero Android references | — |
| **M1** | Safe egress and hardened policy: `RedactedText` type so raw text cannot reach a provider; HIGH_IMPACT always needs approval (flips GAP-02); Law 18-07 data classes, default-deny to remote; consent ledger; Algerian-format redactor; dialect eval set | Redaction miss rate: ≤1 miss in 473 independent held-out spans per class ⇒ <1%; ≤0 in 598 for ID and payment numbers ⇒ <0.5%. All 12 mutants plus one per new safety branch killed | M0; formats verified against official sources; D1 by end of M1 |
| **M2** | One job end to end (wedge-dependent). A: order message → courier parcel (create, status) with approval, idempotency and reconciliation. Connector conformance suite | (a) ≥299 injected ambiguous-timeout runs with 0 duplicate effects ⇒ <1% (simulated); (b) ≤4 failures in 44 realistic Darija/French/Arabizi tasks ⇒ failure <20%; (c) one live contract run with a consenting merchant | M1; D1; official courier docs read [U] |
| **M3** | Pilot surface: approval screens, consent UX, Arabic and French strings, offline queue, app lock, no message content in notifications; approver authorization (flips GAP-03) | ≥299 simulated reconnect trials with 0 duplicates; counsel sign-off (D3) before any real user data; second mutation sweep | M2; D3 |
| **M4** | Pilot: 15-user smoke test, then 60-user decision | Thresholds in §5, fixed before recruiting (D4) | M3; recruiting path [U] |

Track P runs in parallel from day 1 and software never replaces it: segment interviews, a channel and device survey (n ≥ 106 keeps the worst-case margin within ±10 pp at 95% with the exact interval; the earlier figure 97 is the normal approximation and is 0.45 pp short, see E-7), willingness-to-pay. A draft kit for all three is delivered separately as `minna-field-kit`. ANGEM and CNAM run the documented programs [E]; whether they would partner is [U], and nobody has been contacted.

## 5. Gate catalogue

Method everywhere: exact binomial, one-sided, α = 5%. It holds only for independent trials drawn from the distribution you care about: a redactor tested on its own templates certifies the templates, not real text. Reproduce with `python3 scripts/minna_gates.py` (assertions inside).

Samples n needed so that at most k observed failures proves the true failure rate is below p_max:

| p_max | k=0 | k=1 | k=2 | k=3 | k=4 |
|---|---|---|---|---|---|
| 20% | 14 | 22 | 30 | 37 | 44 |
| 10% | 29 | 46 | 61 | 76 | 89 |
| 5% | 59 | 93 | 124 | 153 | 181 |
| 2% | 149 | 236 | 313 | 386 | 456 |
| 1% | 299 | 473 | 628 | 773 | 913 |
| 0.5% | 598 | 947 | 1,258 | 1,549 | 1,829 |
| 0.1% | 2,995 | 4,742 | 6,294 | 7,752 | 9,151 |

Pilot decision thresholds against a 50% weekly-retention hypothesis (placeholder; D4 sets the real one before recruiting):

| Users | Reject "≥50%" if retained ≤ | Reject "≤50%" if retained ≥ | Inconclusive |
|---|---|---|---|
| 15 | 3 | 12 | 4–11 |
| 30 | 10 | 20 | 11–19 |
| 60 | 23 | 37 | 24–36 |

Fifteen users can only detect extreme outcomes; a decision needs about 60.

## 6. Review protocol (every milestone, in this order)

1. **Claim diff.** Every new factual claim gets a tag and a source in `ASSUMPTION_REGISTER.md`. Unsourced means [U].
2. **Falsification first.** Write down what result would make us stop, before running the test.
3. **Re-run everything.** Tests, `scripts/mutation_check.py`, `scripts/minna_gates.py`; append the dated output to `EVIDENCE.md`.
4. **Safety review.** New effects, data classes, egress destinations and approval paths. Each new safety branch gets a mutant.
5. **Register update.** A contradicted assumption is fixed in the docs before more code depends on it.

## 7. Decisions for the owner

| ID | Decision | Default | Needed by |
|---|---|---|---|
| D1 | Wedge: **A** micro-business operator (orders → courier → customer replies) or **C** graduate career/freelance | A for M2: the only segment I found evidence for (named barriers, a ministry-level steering committee, real integration points); C was not researched. Risk: A overlaps two niches you rejected as weak, so the women-specific advantage must come from distribution and trust, not features. C stays interview-only | End of M1 |
| D2 | Surface: Android local-first, web/PWA + server, or messaging bot | Android local-first | Before M3; the channel survey can flip it |
| D3 | Engage an Algerian data-protection lawyer. Questions: is redacted text still personal data; is express consent (Art. 45) enough for model-API calls; is a DPO required of a small controller (sources conflict); which ANPDP declarations apply | Yes, before any real user data | Before M3 |
| D4 | Pilot success metric and threshold | Placeholder: ≥50% weekly retention | Before recruiting |

Assumed, veto freely: a new repo with `core/` extracted unchanged (package names kept so the Android app can depend on it later); the upstream repo frozen; no licence chosen yet.

## 8. Gaps log

| ID | Gap | Status |
|---|---|---|
| GAP-01 | Upstream suite left 6 of 12 safety branches unprotected, including two its own checklist ticks (scope check, egress data classes) | **Closed in M0** |
| GAP-02 | With HIGH_IMPACT enabled, approval is opt-in per Action rather than enforced by policy | Open → M1 (pinned by `KnownGapCharacterizationTest`) |
| GAP-03 | Approver identity is recorded but never authorized | Open → M3 (pinned) |
| GAP-04 | Journal stores re-read the whole file on every operation [I, from reading the code]; fine on one phone, not for a multi-tenant server | Open; matters only if D2 flips |
| GAP-05 | `RuntimeToolGatewayTest`, the org.json and OkHttp code, the Gradle build and CI are untested here | Open → first run on your machine |

## 9. Out of scope for v1

Moving money; legal, family-law, health or safety advice; Tamazight; a plugin marketplace, multi-agent coordination and server tenancy (all rejected upstream until measured workloads justify them); anything inferred from a user's gender.
