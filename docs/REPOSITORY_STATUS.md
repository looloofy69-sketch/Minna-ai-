# Repository status

**Checked:** 2026-10-23  
**Repository:** https://github.com/looloofy69-sketch/Minna-ai-  
**Status:** source import completed; package-level verification remains incomplete.

## Current repository contents

The `main` branch now contains the source packages under `minna/` and `minna-field-kit/`, alongside the repository overview, documentation, and GitHub Actions workflow. The transfer archive was deleted by the import workflow after extraction.

The import used GitHub Actions run [#1](https://github.com/looloofy69-sketch/Minna-ai-/actions/runs/40009849712), which completed with conclusion **success**. The job validated archive member paths, confirmed both package README files, extracted both packages, and committed them to `main`.

## Existing verification evidence

- Source import workflow: **passed** (GitHub Actions run #1, 2026-10-23).
- M0 `scripts/minna_gates.py`: **passed** (all assertions passed).
- M0 `scripts/minna_math.py`: **passed** (all assertions passed; output includes the exact-interval correction requiring n=106 for a worst-case ±10 percentage-point margin at 95%, rather than the earlier normal-approximation n=97).
- Gradle/Kotlin build: **not run**; Gradle was unavailable in the previous working environment. The package contains a separate sandbox build script, but that has not been independently rerun here after import.
- Field-kit `python3 survey_cli.py selftest`: **not fully verified**; the command exceeded the available execution window after emitting test progress. No passing result is claimed.

Import success confirms extraction and commit, not full package acceptance. See the package READMEs and evidence files for the project's own verification details; those claims are not automatically independent reproductions.

## Remaining gates before field deployment

1. Run the field-kit self-test to completion and resolve any failures or timeouts.
2. Run the Kotlin build and tests in a suitable Java/Gradle environment.
3. Review the M0 safety-critical mutation tests and confirm they pass in a reproducible environment.
4. Complete native-speaker review of French and Arabic, cognitive pretesting, consent/privacy and retention review, recruitment design, and pre-registered decision thresholds.
5. Keep the field kit marked draft and the M0 package marked pre-alpha until those checks are complete.

## Truthfulness rule

A status in a package README is a claim from that package, not automatically an independently reproduced result. Record the command, environment, and outcome for each verification step.
