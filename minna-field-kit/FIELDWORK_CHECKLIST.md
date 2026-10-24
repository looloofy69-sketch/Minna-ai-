# Fieldwork readiness checklist (v0.1)

**Status: BLOCKED — no real participants or survey responses should be collected yet.**

This checklist separates software completion from research and participant-safeguarding readiness. Check an item only after evidence is recorded in the repository or the research log.

## A. Instrument and analysis

- [ ] Confirm the live-form screen order matches `generated/survey_en.md`, `survey_fr.md` or `survey_ar.md`. Behavioural questions and the pain ranking must precede the Minna concept card.
- [ ] Confirm the live form enforces consent, age 18+, and women-only eligibility. The current questionnaire directly asks consent and age but does not itself verify gender eligibility. Document how the additional eligibility check is performed and how non-eligible responses are excluded.
- [ ] Configure every `show_if` rule exactly as described in the generated form/codebook. Export a small synthetic form test and verify the resulting CSV against the loader.
- [ ] Fix the two price cells based on interviews; assign them randomly to eligible current sellers; store the assigned `price_cell` and display the corresponding amount in W2. Test both price cells end-to-end before recruitment.
- [ ] Run `python3 survey_cli.py render` and confirm the generated forms and codebook have no unexplained diffs.
- [ ] Run each test module to completion and record interpreter/version, dependencies, command, and result. Run the long mutation suite separately and record its result; do not infer its status from unit-test success.
- [ ] Confirm out-of-scope answers are excluded from every estimate and that the report visibly flags all data-quality issues.

## B. Research design and interpretation

- [ ] Fix the interview qualifying criteria and the qualitative go/no-go decision rule before the first interview. Do not use the hypothetical binomial tables as prevalence bounds for purposive/channel-capped recruitment.
- [ ] Recruit 14 interviews across at least five distinct channels if retaining the three-per-channel cap. Record the channel and referral chain for each interview; note missing or unreachable groups.
- [ ] Define the survey's target population and intended inference before deciding the sample size. The n=106 calculation describes sampling precision under its model; it does not make a convenience/referral sample representative.
- [ ] Keep current sellers separate from women planning to sell in analysis and decision-making. Any broader target segment needs an explicit, pre-registered rationale.
- [ ] Pilot the live form with five to eight target participants. Observe comprehension and timing; do not coach answers. Revise wording before the real collection begins and version the instrument.
- [ ] Review translations in French and Arabic with native speakers familiar with Algerian usage; check Arabic register and the intended use of Darija in interviews.

## C. Consent, privacy and safety

- [ ] Replace all consent placeholders, including organisation and storage location, and make the survey provider's metadata collection clear.
- [ ] Approve a written data-management plan: data controller/owner, access roles, storage location, retention/deletion dates, backup policy, sharing rules and incident procedure.
- [ ] Confirm that the survey's anonymity wording matches the provider configuration. Do not promise individual deletion after submission unless a tested response-identification/deletion mechanism exists.
- [ ] Set an interview withdrawal/deletion cutoff, issue participants an interview code, and ensure any code-to-contact link is stored separately with restricted access.
- [ ] Decide whether audio is necessary. Obtain separate audio permission, restrict access, specify transcription/deletion dates, and do not upload identifiable customer chats or screenshots.
- [ ] Prepare local support contacts and fieldworker safety procedures before interviews; do not send follow-up messages to a shared/controlled phone unless the participant has said it is safe.
- [ ] Obtain appropriate local privacy/legal review before fielding. The kit does not substitute for legal advice.

## D. Analysis release gate

- [ ] Inspect every run's data-quality section before interpreting estimates. Resolve or explicitly document unexpected answers, unrecognized columns, unknown price cells and missingness.
- [ ] Distinguish arithmetic confidence intervals, clustering sensitivity and recruitment selection bias in every report. None is a substitute for the others.
- [ ] Preselect a small set of primary decision metrics; treat the other 37 estimates as exploratory.
- [ ] Never present synthetic example outputs as observed research results.
- [ ] Update this checklist with dated evidence and an owner for each completed gate before marking the field kit ready.
