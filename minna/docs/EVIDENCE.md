# Evidence log

What was actually run, with results. Re-run to refresh; append dated entries, never rewrite old ones.
Run 2026-10-12, re-verified on the shipped tree 2026-10-13. Toolchain: JDK 21.0.12, Kotlin compiler 2.0.21, JUnit 4.13.2 (+ hamcrest-core 1.3), `-jvm-target 17`.
The compiler and test jars are the ones bundled in the Gradle 8.14.3 distribution on the authoring machine (see E-5).

## E-1 The control plane builds and passes outside Android

Static scan of upstream `Loofy147/llms-mcp-android` @ `78afd5d`:

| Area | Files | Android imports |
|---|---|---|
| `runtime/*.kt` | 10 | 9 files: 0 · `AndroidRuntimeFactory.kt`: 1 |
| `runtime/t2/*` | 2 | 5 (Android service and store) |
| `data/*.kt` | 6 | `CredentialStore` 4, `ModelProvider` 1, `SettingsStore` 1; `AnthropicClient`, `RuntimeToolGateway`, `ToolRegistry`: 0 (but use org.json / OkHttp) |
| `app/src/test` | 7 | 0 |

The 9 portable files also contain no fully qualified `android.` / `androidx.` use, and import nothing outside the JDK, the Kotlin standard library and the project.

Build and test of `core/` (the 9 files + 6 upstream tests, then + 3 new test files):

| Step | Result |
|---|---|
| Compile 9 main files | 0 errors, 63 classes |
| Upstream tests alone | `OK (33 tests)`; 33 `@Test` methods in the sources, so every test ran |
| With the 3 new test files | `OK (43 tests)`; 43 `@Test` methods |
| Byte identity of the 15 extracted files | 15 identical, 0 different (`docs/PROVENANCE.md`) |

A first attempt crashed inside the compiler (`NoClassDefFoundError: org/jetbrains/annotations/NotNull`). The cause was the compiler's own classpath, not the source; adding `annotations-24.0.1.jar` from the same Gradle distribution fixed it.

Reproduce: `scripts/sandbox_build_and_test.sh core`

## E-2 Mutation check of the safety-critical branches

`scripts/mutation_check.py` applies 12 single-expression changes, one at a time, to the control plane and rebuilds. A mutant is KILLED if at least one test fails and SURVIVED if all tests still pass.

| Mutant (what is broken) | Upstream tests (33) | With M0 tests (43) | Test that kills it |
|---|---|---|---|
| `replay_guard_removed` | KILLED | KILLED | `idempotencyKeyProducesStableEffectIdentityAndBlocksReplay` (upstream) |
| `consumed_approval_executes` | **SURVIVED** | KILLED | `secondResolverOfAnAlreadyConsumedApprovalFailsClosedAndNeverExecutes` |
| `policy_deny_executes` | KILLED | KILLED | `deniedActionDoesNotExecute` (upstream) |
| `denied_approval_executes` | **SURVIVED** | KILLED | `deniedApprovalEndsDeniedAndNeverExecutes` |
| `approved_plan_drift_unchecked` | **SURVIVED** | KILLED | `approvalIsRejectedWhenThePlanDriftsAfterItWasRequested` |
| `scope_escalation_unchecked` | **SURVIVED** | KILLED | `invocationScopeBeyondTheDeclaredCapabilityScopeIsRejectedBeforeExecution` |
| `failed_effect_not_marked_unknown` | KILLED | KILLED | `laterEffectFailureDoesNotEraseEarlierCompletedEffect` (upstream) |
| `blank_identity_allowed` | **SURVIVED** | KILLED | `blankIdentityIsDeniedAndNeverExecutes` |
| `egress_https_unchecked` | KILLED | KILLED | `deniesNonHttpsDestination` (upstream) |
| `egress_embedded_credentials_unchecked` | KILLED | KILLED | `deniesEmbeddedCredentialsInDestination` (upstream) |
| `egress_host_allowlist_unchecked` | KILLED | KILLED | `deniesUnlistedHost` (upstream) |
| `egress_data_class_unchecked` | **SURVIVED** | KILLED | `egressDeniesDataClassesOutsideTheAllowedSet` |
| **Score** | **6 / 12 (50%)** | **12 / 12 (100%)** | |

Two of the six survivors are controls that upstream's `REVIEW_CHECKLIST_v0.2.md` ticks as implemented: "Required scope is checked against the Action capability declaration" and "Declared egress data classes are checked against policy". Both were implemented; neither had a test that failed when it was removed.

Limits of this measure: 12 hand-picked mutants over the branches named in the control-plane invariants, not an automated sweep of all code. A 100% score on this set says nothing about code outside it.

Reproduce: `python3 scripts/mutation_check.py core` (all 12 killed) and, for the "before" column, the same command on a copy of `core/` with the three new test files removed (6 killed, 6 survived).

## E-3 Gate and market arithmetic

- `python3 scripts/minna_gates.py`: exact-binomial sample sizes for 7 tolerances × 5 allowed-failure counts, with closed-form checks, hand-checkable reference values (for example 0.8^14 ≤ 5% < 0.8^13, 0.99^299 ≤ 5% < 0.99^298), a Monte-Carlo check of the 473-sample row (simulated 0.0498 vs exact 0.0498) and pilot thresholds for 15, 30 and 60 users. `ALL ASSERTIONS PASSED`.
- `python3 scripts/minna_math.py`: female/male social-media presence ratio 0.741 (0.712–0.772 across the adult-share uncertainty), the 11.4M / 15.7M / 18.5M bracket for women online, participation and parity arithmetic, the 25 × 12 = 300 trainer cascade. `ALL ASSERTIONS PASSED`.
- Method change: an earlier message gave "4 failures in 47 tasks proves ≥80% success" using a two-sided Wilson interval. The plan now uses one method, exact one-sided binomial, which gives 4 failures in 44. Both are valid; the Wilson figure is the more conservative.

## E-4 Behaviour pinned by `KnownGapCharacterizationTest` (passing today)

| Gap | What the passing test shows |
|---|---|
| GAP-02 | `PolicyEngine(allowHighImpact = true)` returns ALLOW for a HIGH_IMPACT Action whose `approvalMode` is NEVER. With the default policy the same Action is DENIED |
| GAP-03 | A Run requested by "alice" is approved and executed by approver "mallory"; the approver is recorded in `resolvedBy`, never checked |

Both are acceptable for a single-user, on-device runtime and unacceptable for a product that acts for several users. Each test names the milestone that flips it.

## E-5 Limits of the authoring sandbox

- Maven Central (`repo.maven.apache.org`) and the Gradle plugin portal (`plugins.gradle.org`) return 403 on CONNECT: a network-policy denial for that session. Gradle therefore could not resolve the Kotlin plugin, and the Gradle build was not run. This was reported, not routed around.
- Consequence: `core/` was verified with the compiler and JUnit jars already inside the Gradle distribution. Anything needing Maven artifacts (org.json, OkHttp) could not be built here.

## E-6 Not verified

The Gradle build files and `.github/workflows/ci.yml`; `RuntimeToolGatewayTest` and the code it needs (org.json, OkHttp); Android instrumented tests and any behaviour on a device; courier APIs (official documentation not read); anything about redaction, which is not built yet.

## E-7 Correction: the survey sample size (2026-10-20)

**What was written.** "A channel and device survey (n ≥ 97 gives ±10 pp at 95%)" (BUILD_PLAN §4) and "n ≥ 97 for ±10 pp at 95%" (A-01 next test). `scripts/minna_math.py` printed 97 without saying which method it used.

**What is true [E].** 97 = ⌈1.96² × 0.25 / 0.10²⌉, the normal approximation at p = 0.5. With the exact (Clopper-Pearson) interval the worst case over all possible results sits near k = 0.42 n, not at 50%, and it is wider: ±10.45 pp at n = 97, ±10.03 pp at n = 105, ±9.98 pp at n = 106. So 106 is the smallest n whose worst-case margin is within ±10 pp. The Wilson interval's worst case at n = 97 is ±9.95 pp, so 97 was acceptable for that method; the error was not saying which method the number belonged to.

**Size.** 9 respondents and 0.45 pp of margin. Small, but it was written as a guarantee.

**A second correction.** The A-01 next test implied a first-party survey could test reach. It describes only the people the channel reached; who is offline is invisible to it. The field kit's report says so in its first section.

**Two implementations agree.** `scripts/minna_math.py` (stdlib, written for this correction) and the field kit's `minna_stats.py` (separate code, cross-checked against scipy) give the same margins to four decimals. `minna_math.py` now asserts that 105 fails and 106 passes.

Reproduce: `python3 scripts/minna_math.py`; in the field kit, `python3 survey_cli.py plan`.
