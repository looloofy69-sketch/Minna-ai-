# Import the Minna source packages

The repository contains bootstrap documentation and an import workflow. The original source code is still in the two package archives; the repository connector cannot upload a binary archive directly.

## One-time upload

1. Download `minna-source.tar.xz` from the ChatGPT conversation link provided with this guide.
2. Open https://github.com/looloofy69-sketch/Minna-ai- on GitHub.
3. Choose **Add file → Upload files**.
4. Upload the file using this exact repository path: `source-archives/minna-source.tar.xz`.
5. Commit the upload directly to `main` as the repository owner `looloofy69-sketch`.

The GitHub Actions workflow at `.github/workflows/bootstrap-import.yml` will validate the archive structure, confirm both package README files are present, then commit the extracted directories as `minna/` and `minna-field-kit/`. It removes the uploaded transfer archive from the repository during import.

## Expected result

- `minna/` contains the M0 runtime and its supporting files.
- `minna-field-kit/` contains the user-research and survey-analysis package.
- The import is one commit, preserving package boundaries and the source files within each archive.

## Failure handling

If the workflow fails, inspect **Actions → Import Minna source bundle** and read the failed step's logs. The workflow intentionally refuses to overwrite either directory if it already exists. It does not run the project tests during import.

## Verification still required

- Run the Gradle/Kotlin build and tests in a Java/Gradle environment.
- Run the field-kit self-test suite to completion.
- Complete native-speaker, cognitive-pretest, consent/privacy, and recruitment-design review before any live field study.
