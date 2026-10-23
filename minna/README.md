# Minna

An AI assistant that completes bounded jobs for Algerian women, with explicit approval, durable evidence and no hidden data egress.

**Status:** pre-alpha. M0 (verified portable core) is complete; see `docs/BUILD_PLAN.md` for what comes next and what would make us stop.

## Layout

| Path | What it is |
|---|---|
| `core/` | The agent control plane (Activation → Policy → Approval → Egress → Run → Evidence), extracted unchanged from `Loofy147/llms-mcp-android` @ `78afd5d`, plus new tests. No Android, no third-party runtime dependencies |
| `docs/BUILD_PLAN.md` | Thesis, milestones, exit gates, decisions, gaps |
| `docs/ASSUMPTION_REGISTER.md` | Every assumption with a status tag and its source |
| `docs/EVIDENCE.md` | What was run, with results |
| `docs/PROVENANCE.md` | Which files came from upstream, with hashes |
| `scripts/` | Gate math, market math, mutation harness, offline build |

## Verify, strongest first

1. `python3 scripts/mutation_check.py core` — builds 12 broken variants of the safety-critical code and expects the tests to catch every one. Needs the offline toolchain below.
2. `scripts/sandbox_build_and_test.sh core` — compiles `core/` and runs all 43 tests using only jars bundled in a Gradle distribution (`GRADLE_LIB`, default `/opt/gradle/lib`; verified with Gradle 8.14.3 only). Used for the evidence in `docs/EVIDENCE.md`.
3. `python3 scripts/minna_gates.py` and `python3 scripts/minna_math.py` — sample-size gates and market arithmetic, assertions included.
4. `gradle :core:test` — the normal path. **Not yet executed:** the Gradle files and `.github/workflows/ci.yml` were written where Maven Central was unreachable. The first run on your machine is part of M0 acceptance.

## Rules of the project

- Every claim is tagged **[E]** established, **[I]** inference, **[H]** hypothesis or **[U]** unknown, and has a source.
- A safety control without a test that fails when it is removed is not counted as implemented.
- Context about a user is only what the user states. Nothing is inferred from gender or demographics.

No licence chosen yet.
