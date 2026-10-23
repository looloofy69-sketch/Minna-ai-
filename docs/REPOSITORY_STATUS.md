# Repository status

**Checked:** 2026-10-23  
**Repository:** https://github.com/looloofy69-sketch/Minna-ai-  
**Status:** bootstrap documentation only; source import pending.

## What was inspected

The GitHub repository was public but empty at inspection time: no commits, no branches, no files, and a default branch configured as `main`.

Two uploaded source archives are available in the working conversation:

- `minna-m0-corrected.zip` — 51 archive entries, containing the Kotlin M0 runtime, Gradle files, CI configuration, scripts, tests, and design/evidence documentation.
- `minna-field-kit.zip` — 36 archive entries, containing multilingual survey content, generated questionnaires/codebook, Python analysis code, tests, and synthetic examples.

The intended import preserves the original top-level directories, `minna/` and `minna-field-kit/`, rather than merging similarly named files or flattening their histories.

## Verification performed in this session

- M0 `scripts/minna_gates.py`: **passed** (all assertions passed).
- M0 `scripts/minna_math.py`: **passed** (all assertions passed; output includes the exact-interval correction requiring n=106 for a worst-case ±10 percentage-point margin at 95%, rather than the earlier normal-approximation n=97).
- Gradle/Kotlin build: **not run**; Gradle is not installed in this environment.
- Field-kit `python3 survey_cli.py selftest`: **not fully verified**; the command exceeded the available execution window after emitting test progress. No passing result is claimed.

These checks validate only the commands listed above. They do not constitute full project acceptance.

## Gates before field deployment

1. Import the code and preserve source provenance.
2. Run the field-kit test suite in a suitable execution environment and resolve any failures or timeouts.
3. Run the standard Gradle build and Kotlin tests; the source README says this path had not yet been executed.
4. Complete the field kit's stated human checks: native-speaker review of French and Arabic, cognitive pretest, consent/retention review, recruitment design, and the pre-registered decision thresholds.
5. Keep the field kit marked as draft until those checks are actually complete.

## Truthfulness rule

A status in an archive README is a claim made by that package, not automatically an independently reproduced result. Record the command, environment, and outcome for each new verification step.