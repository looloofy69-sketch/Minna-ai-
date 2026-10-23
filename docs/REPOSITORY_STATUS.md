# Repository status

**Checked:** 2026-10-23  
**Repository:** https://github.com/looloofy69-sketch/Minna-ai-  
**Status:** bootstrap documentation committed; source import is prepared but awaits one binary-file upload.

## Current repository contents

The repository includes a project overview, this status record, an import guide, and a GitHub Actions workflow that will import the source archive. The actual `minna/` and `minna-field-kit/` source directories have not yet been committed.

This session's GitHub integration can commit text files but did not provide a reliable direct binary-archive upload path. A chunked Base64 workaround proved unreliable, so the incomplete temporary chunks were removed rather than treated as a source import.

## Next import step

Create `source-archives/minna-source.tar.xz` in the repository by uploading the combined bundle linked in the conversation, then commit directly to `main` as `looloofy69-sketch`. The `.github/workflows/bootstrap-import.yml` workflow validates archive entries, checks the two package README files, imports the source directories, and removes the temporary archive. See [IMPORT_GUIDE.md](IMPORT_GUIDE.md).

## Existing verification evidence

- M0 `scripts/minna_gates.py`: **passed** (all assertions passed).
- M0 `scripts/minna_math.py`: **passed** (all assertions passed; output includes the exact-interval correction requiring n=106 for a worst-case ±10 percentage-point margin at 95%, rather than the earlier normal-approximation n=97).
- Gradle/Kotlin build: **not run**; Gradle was unavailable in the working environment.
- Field-kit `python3 survey_cli.py selftest`: **not fully verified**; the command exceeded the available execution window after emitting test progress. No passing result is claimed.

These checks validate only the listed commands. They do not constitute full project acceptance.

## Gates before field deployment

1. Import the code and preserve package boundaries.
2. Run the field-kit test suite to completion and resolve failures or timeouts.
3. Run the Gradle build and Kotlin tests in a suitable environment.
4. Complete native-speaker review of French and Arabic, cognitive pretesting, consent/retention review, recruitment design, and pre-registered decision thresholds.
5. Keep the field kit marked draft until those checks are actually complete.

## Truthfulness rule

A status in a package README is a claim from that package, not automatically an independently reproduced result. Record the command, environment, and outcome for each verification step.
