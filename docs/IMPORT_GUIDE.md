# Import the Minna source packages

**Current state:** The source bundle was imported successfully on 2026-10-23. The `main` branch contains both `minna/` and `minna-field-kit/`. See [REPOSITORY_STATUS.md](REPOSITORY_STATUS.md) and [GitHub Actions run #1](https://github.com/looloofy69-sketch/Minna-ai-/actions/runs/40009849712).

## How the import was performed

1. Upload the combined `minna-source.tar.xz` bundle to the repository root (the path must be exactly `minna-source.tar.xz`).
2. Commit directly to `main` as the repository owner `looloofy69-sketch`.
3. The workflow at `.github/workflows/bootstrap-import.yml` validates archive member paths and checks both package README files before extraction.
4. On success, the workflow commits `minna/` and `minna-field-kit/` and deletes the transfer archive from the repository.

The workflow is deliberately restricted to commits triggered by the repository owner. It refuses to overwrite either source directory if that directory already exists. Do not rerun the import against an existing package tree without reviewing and changing that safeguard.

## Verification still required

- Run the Gradle/Kotlin build and tests in a Java/Gradle environment.
- Run the field-kit self-test suite to completion.
- Complete native-speaker review, cognitive pretesting, consent/privacy, and recruitment-design review before any live field study.
