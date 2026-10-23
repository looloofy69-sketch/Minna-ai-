# Minna

Minna is an early-stage AI assistant project focused on bounded, useful jobs for Algerian women, with explicit approval, durable evidence, and no hidden data egress.

## Two connected workstreams

### M0 — agent runtime and safety controls
The M0 source package contains a Kotlin runtime core, approval and policy controls, runtime/evidence storage, tests, build files, CI configuration, and design/evidence documents. Its package README identifies it as **pre-alpha**.

### Field kit — user research and survey analysis
The field kit contains interview guides and survey material in English, French, and Arabic, plus Python tools for rendering forms, generating synthetic data, analysing survey exports, and reporting uncertainty. Its package README explicitly says **draft, not ready to field**.

## Repository status

The two source packages have been imported into `main` as `minna/` and `minna-field-kit/`. GitHub Actions workflow run [#1](https://github.com/looloofy69-sketch/Minna-ai-/actions/runs/40009849712) completed successfully. The temporary `minna-source.tar.xz` transfer archive was removed after import. See [docs/REPOSITORY_STATUS.md](docs/REPOSITORY_STATUS.md) for what was and was not verified, and [docs/IMPORT_GUIDE.md](docs/IMPORT_GUIDE.md) for the import procedure.

## Principles

- Distinguish evidence, inference, hypotheses, and unknowns.
- Treat safety controls as implemented only when tests detect their removal.
- Do not infer personal attributes from a user's demographics.
- Do not generalize convenience- or referral-sample survey findings to all Algerian women.
- Do not treat synthetic-data tests as evidence that survey wording or consent language is valid.
- No license has been selected; this remains an explicit project decision.
