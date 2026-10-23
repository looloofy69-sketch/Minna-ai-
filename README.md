# Minna

Minna is an early-stage AI assistant project focused on bounded, useful jobs for Algerian women, with explicit approval, durable evidence, and no hidden data egress.

## Two connected workstreams

### M0 — agent runtime and safety controls
The `minna-m0-corrected.zip` source package contains a Kotlin runtime core, approval and policy controls, runtime/evidence storage, tests, build files, CI configuration, and design/evidence documents. Its package README identifies the project as **pre-alpha**.

### Field kit — user research and survey analysis
The `minna-field-kit.zip` source package contains interview guides and survey material in English, French, and Arabic, plus Python tools for rendering forms, generating synthetic data, analysing survey exports, and reporting uncertainty. Its package README explicitly says **draft, not ready to field**.

## Important status

This repository was empty when inspected on 2026-10-23. This first commit initializes the project overview only; the contents of the two source archives have **not yet been imported into GitHub**. Do not treat this repository as a runnable codebase until that import is complete.

See [docs/REPOSITORY_STATUS.md](docs/REPOSITORY_STATUS.md) for the source and verification status.

## Principles

- Distinguish established evidence, inference, hypotheses, and unknowns.
- Treat safety controls as implemented only when tests detect their removal.
- Do not infer personal attributes from a user's demographics.
- Do not generalize convenience- or referral-sample survey findings to all Algerian women.
- Do not treat synthetic-data tests as evidence that survey wording or consent language is valid.

## Intended repository layout

Once the source import is complete, retain the package boundaries to preserve provenance:

- `minna/` — M0 runtime, documentation, scripts, build configuration, and CI.
- `minna-field-kit/` — field research material, survey definitions, analysis tools, tests, and synthetic examples.

No license has been selected in the source package; licensing remains an explicit project decision.
