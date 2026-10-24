# Minna field kit v0.1 (Track P)

The part of the build plan that software cannot replace, made ready to run: interviews with women who sell, a survey of channels, devices, pains, privacy and price in English, French and Arabic, and an analysis program that tells you how little the numbers prove.

**Status: draft, not ready to field.** Section 4 lists what only people can supply. Python 3, standard library only. Five tests use scipy as an independent cross-check and are skipped when it is not installed (the last line of `selftest` then reads `OK (skipped=5)`). Last verified on 2026-10-23 with Python 3.13.16 and scipy 1.18.1.

The kit does not host the survey. Put the questions from `generated/` into whatever form tool you use (or print them), keep the wording, and export a CSV for `analyze`.

## 1. What is in the box

| Path | What it is |
|---|---|
| `interview_guide_en.md`, `interview_guide_fr.md` | 30-minute guide and notes sheet; the numerical tables are explicitly marked hypothetical and are not prevalence bounds for this purposive sample |
| `FIELDWORK_CHECKLIST.md` | A blocking checklist covering survey setup, research design, consent/privacy, analysis and fieldwork release gates |
| `content/*.json` | The survey: questions, options in 3 languages, skip logic, and the 37 estimates. The printed survey and the analysis both read these files, so they cannot drift apart |
| `generated/` | `survey_en.md`, `survey_fr.md`, `survey_ar.md`, `codebook.csv`, rendered from `content/` |
| `survey_cli.py` | `plan`, `render`, `synthetic`, `analyze`, `selftest` |
| `minna_stats.py`, `minna_text.py`, `survey_*.py` | The code: exact intervals, exact tests and power, text matching, loader, estimates, report |
| `tests/` | The tests |
| `scripts/mutate_kit.py` | Breaks the code in 158 deliberate ways and checks that the tests notice |
| `examples/` | A synthetic data file with a planted truth, and the report and estimates the program produces from it. It describes nobody |

## 2. Run it

```
python3 survey_cli.py selftest                       # every test, about a minute
python3 survey_cli.py plan                           # the sample-size arithmetic, computed now
python3 survey_cli.py plan --slow                    # adds the exact figure for 50% vs 40% (about 15 s more)
python3 survey_cli.py render                         # rebuild generated/ from content/
python3 survey_cli.py synthetic fake.csv --n 300     # fake data with a known truth
python3 survey_cli.py analyze fake.csv --out report.md --estimates-csv estimates.csv
python3 scripts/mutate_kit.py                        # mutation check, about 12 minutes on 2 cores
```

`analyze` takes the CSV export of any survey tool. Columns are matched by question id, by question text in any of the three languages, or by a text prefix of at least 12 characters; answers are matched by option code or by label in any language, with Arabic spelling variants and Arabic digits folded. Nothing is meant to be dropped silently: the report lists unmatched columns, unmapped answers, impossible numbers, skip-logic violations and item non-response before the estimates. The pipeline excludes answers to questions that were behind a failed skip gate from the relevant estimates. It refuses a file without consent (S1) and 18-or-older (S2) columns unless you pass `--assume-screened` to confirm those screens were enforced upstream. The survey is intended for women, but the current questionnaire does not independently verify gender eligibility; the live-form setup must enforce and document it before fielding.

## 3. The numbers to plan with (all printed by `plan`)

| Question | Answer | Note |
|---|---|---|
| Survey size for a worst-case margin of ±10 pp at 95%, exact interval | **106** | This is a statistical precision calculation under its sampling model—not a promise of representativeness. The normal approximation gives 97; the exact worst case at n=106 is about ±9.98 pp. |
| Interview discovery sample | 14 | The interviews are for task discovery; the detection and binomial-bound figures are hypothetical random-sample arithmetic and do not estimate prevalence under this purposive recruitment plan. |
| Two prices, 50% vs 30% stated acceptance, 80% power, 5% two-sided, exact test | 102 respondents **per price** | The normal approximation says 91. A survey sized for ±10 pp cannot also test price. |
| Two prices, 50% vs 40% | 404 per price | Printed by `plan --slow`. |
| 10 clusters of 10 (referral groups), ρ = 0.10 | The naive exact 95% interval covers 87.2% | ρ = 0.20: 79.3%. Design-effect calculations are a clustering sensitivity analysis; they do not repair selection bias. |

## 4. Before fielding (people, not code)

1. **Interviews first.** Use the 14 interviews to discover tasks, workarounds and costs; do not treat the count as prevalence evidence. Fix the qualitative go/no-go rubric in advance.
2. **Fix the Android threshold for D2 before fielding** (the current 80% is a placeholder). D2 is scoped to current sellers only, but the reported bounds are conditional on a sampling model and do not correct selection bias.
3. **Complete participant eligibility and consent setup.** The questionnaire screens for consent and age, but it does not independently verify that respondents are women. Implement and document a respectful women-only eligibility check in the platform or screener. Fill all organisation/storage/interview placeholders; the survey consent now warns that an anonymous response may not be retrievable for deletion after submission.
4. **Review privacy and retention.** Decide storage location, access, retention, audio handling, withdrawal/deletion cutoff for interviews, and whether the form provider collects IP addresses or other metadata. Obtain appropriate local data-protection/legal review before collecting data; this repository is not legal advice.
5. **Validate language and comprehension.** Native-speaker review of French and Arabic for Algerian usage, followed by cognitive pretesting with 5–8 target participants. Verify the claimed 10-minute survey duration.
6. **Plan recruitment realistically.** With a maximum of three interviews per channel, 14 interviews require at least five channels. Record channel and referral codes. This is purposive discovery, not a probability sample; intervals and clustering adjustments cannot repair selection bias or make results representative of all Algerian women.
7. **Implement random price assignment.** The generated questionnaire does not randomize participants. Configure the live form to assign each eligible seller to one price cell, record `price_cell`, and show the exact assigned price in W2. If assignment was not random, interpret the price contrast descriptively, not causally.
8. **Preserve question order.** The concept card is rendered after behavioural and pain questions to reduce priming; do not move it back to the opening screen.

## 5. What was verified, and how

Each row below is a test in `tests/`. Run all of them with `python3 survey_cli.py selftest`, or one file with `python3 tests/test_stats.py`.

| Claim | Evidence |
|---|---|
| Exact intervals are correct | The bounds satisfy their defining tail equations to 9 decimals; closed forms at k = 0 and k = n; mirror symmetry for every k at three sizes; coverage of at least 95% at 18 (n, p) points; agreement with scipy's beta-quantile form to 1e-10 on a grid of 10 sizes |
| ±10 pp needs n = 106, not 97 | The worst case is taken over every possible result (at n = 97 it sits at k = 41, about 0.42 n, not at 50%) and matches an exhaustive scipy scan to 10 decimals at n = 20, 50, 97 and 106. A second, separately written implementation of the same method in the M0 project (`scripts/minna_math.py`) gives identical margins at seven sample sizes (checked 2026-10-22) |
| The Fisher exact test and its exact power are right | scipy on 300 random tables (agreement to 1e-9); all 1,936 tables with both arms from 1 to 8 against exact fractions (difference below 1e-12); the fast exact power equals the brute-force definition to 12 decimals |
| Wilson, McNemar, bootstrap, design effect | scipy reference values for Wilson (including a grid) and for McNemar (to 12 decimals); the bootstrap interval equals the known quantiles of Binomial(40, ½)/40; simulated clustered counts have the beta-binomial mean and a variance within 8% of 1 + (m − 1)ρ times the independent variance |
| Text matching is stable across English, French and Arabic | Tests for accents, œ and apostrophes, hamza and alef forms, alef maksura, tatweel, diacritics, Persian letters, Arabic-Indic, Persian and full-width digits, punctuation, the six multi-select separators including the Arabic comma, thousands groups versus decimals, and refusal of ambiguous or colliding labels |
| The whole pipeline recovers a planted truth | The synthetic generator has a true value for each of the 37 estimates. Five file layouts of 400 respondents: all 44,491 planted cells come back exactly. 24 runs of 300: the mean of every estimate is within 3 pp of the truth (largest observed 1.35 pp) and the exact 95% intervals contain the truth in 850 of 888 cases (95.7%; the test floor is 93%). That check is coarse (it cannot see an error of about 2 pp), so the truths themselves are also checked against exact enumeration: 12 single-choice, 17 multi-choice and 8 pick-two estimates |
| Corrupt data is reported, not absorbed | Hand-built bad files: missing consent columns, impossible numbers, over-selection, duplicate columns, unmapped and misspelled answers, short and blank rows, an empty file |
| The tests are strong enough to notice real mistakes | `scripts/mutate_kit.py`. Record below |
| Shipped files are current | Tests regenerate `generated/` and `examples/` and compare, and run the generator under three hash seeds |

**Mutation record.** The first run (2026-10-20) used 118 hand-written mutants and the tests killed 67 (57%), although line coverage was already above 95%. The 51 survivors were real gaps: 38 in the loader, estimates, report, printed-form and command-line code (for example a warning that could vanish unnoticed, invalid answers counted in a denominator, excluded codes counted, the price test comparing the wrong cell), 6 in the statistics code, 5 in the text code and 2 in the survey content (the age question was not conditional on consent, and the seller question was not conditional on the 18+ answer). Closing them took a new file of 39 hand-built tests plus additions to the statistics, text and content tests, and changed the code in four places: a guard in the sample-size search that could never fire (deleted), an Arabic spelling fold with a wrong key that was never reached (corrected), the "wide" threshold that lived in two places (now one), and a generator that wrote a set in hash order, so the same seed gave different files in different runs (sorted). Later I added 8 mutants of the planted truth itself: 2 of the first 6 survived the existing tests (a dropped denominator moves the truth by only about 2 pp, too little for 24 runs of 300 to see), so I added 3 exact tests. Final run (2026-10-23, 162 tests): 158 mutants, 158 killed, 0 survived, 0 invalid, 0 errors, about 12 minutes on 2 cores. No mutant was excused as equivalent; the two code defects that survivors pointed to are recorded in `REMOVED_CODE` in the script.

**How far to trust that.** The mutants are ones I thought of, and the tests were written after seeing which survived, so a clean final run is expected and means little by itself; the 57% first pass is the informative figure. It measures the tests against these changes, not against every bug. Code coverage by lines and branches: 99% (3 of 1,030 statements and 3 of 382 branches never run: the `__main__` entry point, a rounding fallback in the generator and a raise that guards against an internal error). Neither number says anything about whether the survey measures what it should.

## 6. Correction to the plan

The M0 documents said "n ≥ 97 gives ±10 pp at 95%". 97 is the textbook normal approximation at p = 50%. With the exact interval the worst case is wider, so the smallest sufficient n is 106 (the Wilson interval's worst case at 97 is ±9.95 pp, so 97 was acceptable for that method; the number had no stated method). A second correction: a survey sent through a channel describes only the people that channel reaches, so it cannot test A-01 (reach) by itself. Both are fixed in the corrected M0 documents (`EVIDENCE.md` E-7, `BUILD_PLAN.md` §4, `ASSUMPTION_REGISTER.md` A-01).

## 7. Limits, stated plainly

- Intervals describe sampling noise **inside the recruited channels**, if respondents were independent. A convenience or referral sample breaks that. They say nothing about Algerian women in general.
- Stated interest, willingness to pay and recalled refusal rates overstate or distort behaviour. Treat them as screens; the pilot's payments and logs are the evidence.
- 37 estimates at 95% each: about 2 would miss by chance if they were independent; they are not, so the count varies. Choose the numbers that matter before reading them.
- Synthetic data tests the arithmetic, not the questions. Whether women understand and answer them honestly is what the pretest is for.
- Free-text "other" answers can still contain identifiers. The report prints the five most common, 40 characters each: read them before sharing a report.
- The interview bounds assume the criteria were fixed in advance and interviewees are independent. Referral chains break that: record the channel of every interview.
- Not verified at all: the translations, the 10-minute length, the consent and retention wording, the price cells and the Android threshold. Section 4 lists who has to do what.
