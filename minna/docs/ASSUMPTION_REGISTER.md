# Minna — assumption register v0.1

Date: 2026-10-12 · Evidence retrieved 2026-10-11 unless stated.
Tags: **[E]** established (executed here, or two independent sources) · **[I]** inference · **[H]** hypothesis · **[U]** unknown / unverified.
Rule: a row may only be upgraded by evidence added to this file in the same commit. A contradicted row is fixed before any code that relies on it.

## Audience and market

| ID | Assumption | Status | Evidence / correction | Next test |
|---|---|---|---|---|
| A-01 | Women are as reachable online as men | **Contradicted for social media [E]; internet-use gap [U]** | Women are 41.6% of social-media user identities vs 49.0% of the population, so female/male presence ≈ 0.74 (0.71–0.77 across the adult-share uncertainty). Ad-tool reach, not unique people ([DataReportal](https://datareportal.com/reports/digital-2026-algeria)). Illustrative bracket for women online: 11.4M (floor) – 15.7M (same gap as social) – 18.5M (parity). GSMA's MENA mobile-internet gap is 12% (2024) but Algeria is not covered ([GSMA](https://www.gsma.com/gender-gap-2025/)) | A first-party channel survey describes only the people the channel reaches and cannot see who is offline, so it does not test reach by itself; a sample frame that does not depend on being online is needed. Precision: n ≥ 106 for a worst-case ±10 pp at 95% with the exact interval (97 was the normal approximation, E-7) |
| A-02 | Women's economic participation is low | **[E] as modeled** | ILO-modeled female participation 14.142% vs male 66.409% (2025); female 14.801% in 2018 ([WB female](https://api.worldbank.org/v2/country/DZ/indicator/SL.TLF.CACT.FE.ZS?format=json&mrv=8), [WB male](https://api.worldbank.org/v2/country/DZ/indicator/SL.TLF.CACT.MA.ZS?format=json&mrv=8)). Modeled data may undercount home-based work [I]. Tertiary enrolment parity index 1.346 in 2024: women's ratio is 34.6% higher than men's ([WB](https://api.worldbank.org/v2/country/DZ/indicator/SE.ENR.TERT.FM.ZS?format=json&mrv=10)) | Interviews: what work, paid how, found how |
| A-03 | Women entrepreneurs' main barrier is lack of a good assistant | **[H]** | One World Bank/We-Fi program names marketing/reach, import competition, product formalities and online payment systems; it trained 119 women, 74% integrated new online platforms ([World Bank](https://www.worldbank.org/en/news/feature/2025/12/09/we-fi-feature-story-how-women-entrepreneurs-in-algeria-are-going-digital)). Single program, no control group | Interviews; pilot |
| A-04 | A women-specific assistant beats a general one | **[H]** | No comparison found. Advantage must come from distribution, trust or workflow fit, not features | Pilot vs unassisted baseline |
| A-05 | WhatsApp is the main channel | **[U]** | No reliable figure found. Facebook 27.5M, YouTube 25.4M, TikTok 24.8M (adults), Instagram 13.5M reach (ad tools) | Channel survey |
| A-06 | Android dominates among target users | **[U]** | Not researched | Channel survey (device OS) |

## Integrations

| ID | Assumption | Status | Evidence / correction | Next test |
|---|---|---|---|---|
| A-07 | Couriers expose merchant APIs Minna can call | **[U] official; [I] likely** | A seller-platform vendor documents Yalidine (API ID + token from the merchant dashboard; access may need enabling by Yalidine, usually for verified businesses) and Maystro (one token) ([DZBuild Yalidine](https://help.dzbuild.com/en/articles/16345639-yalidine), [DZBuild Maystro](https://dzbuild.com/docs/couriers/maystro)). A third-party Python client exists, unaffiliated as far as the page states ([PyPI](https://pypi.org/project/yalidine/)). Official docs not read; cancellation, webhooks and lookup-by-reference not stated | Read official docs; one live contract run |
| A-08 | Cash on delivery dominates and refusals are costly | **[U]** | Figures such as "95% COD" and "20–30% refused" appear in a trade blog with no primary source; not relied on | Capture own data in the pilot |
| A-09 | Minna can move money | **Rejected for v1** | Payments sit under a regulatory workstream (8-ministry committee, [World Bank](https://www.worldbank.org/en/news/feature/2025/12/09/we-fi-feature-story-how-women-entrepreneurs-in-algeria-are-going-digital)). v1 reads and drafts only | Revisit after counsel |

## Law and safety

| ID | Assumption | Status | Evidence / correction | Next test |
|---|---|---|---|---|
| A-10 | A cloud model is fine for user content | **Constrained [E per two law-firm summaries]** | Law 18-07 (10 Jun 2018), amended by Law 25-11 (24 Jul 2025): transfers abroad need ANPDP authorization and adequate protection (Art. 44); derogations include express consent (Art. 45); health, religion, political opinion are sensitive ([DLA Piper](https://www.dlapiperdataprotection.com/?c=DZ&t=law), [Gide](https://www.gide.com/en/news-insights/protection-of-personal-data-focus-on-algerian-regulations/)). Official Gazette not read | Algerian counsel (D3) |
| A-11 | Law 25-11 makes a DPO mandatory and authorizations take 30–60 days | **[U], not relied on** | Only in secondary articles with no primary citation, internally inconsistent ([example](https://algeriatech.news/algeria-anpdp-law-11-25-dpo-mandatory-compliance-2026/)) | Counsel |
| A-12 | Maximum penalties | **[U]** | Sources disagree: fines up to 1,000,000 DZD (DLA Piper) vs 500,000 DZD (Gide) | Gazette |
| A-13 | Connectivity is reliable | **Contradicted [E]** | Social/messaging restricted during baccalaureate exams in 2024 and 2025 ([Internet Society Pulse](https://pulse.internetsociety.org/en/shutdowns/internet-suspended-in-algeria-9-june-2024/): 16 shutdowns, 232 hours since 2019; [Algérie Eco](https://algerie-eco.com/?p=219649)). Exposure of services on own domains [U] | Offline-first queue; avoid exam windows for pilots |
| A-14 | Current LLMs handle Algerian Darija | **[U]** | No Algerian benchmark found. A 2025 study covers MSA, Saudi and Darija (Algerian not mentioned) ([RANLP](https://preview.aclanthology.org/setup/2025.ranlp-1.8)) | Own eval set (M1) |
| A-15 | A ministry AI-models-for-Algeria programme will supply Darija models | **[U], not relied on** | One secondary report of a March 2026 statement; no timeline or primary source ([source](https://algeriatech.news/sovereign-ai-models-algerian-values-culture-2026/)) | — |
| A-16 | Shared or monitored devices are a risk | **[H]** | Standard design concern; no data gathered | Interviews |

## Engineering (this repository)

| ID | Assumption | Status | Evidence | Reproduce |
|---|---|---|---|---|
| A-17 | The control plane runs outside Android | **[E]** | 9 source files, zero Android references (imports and fully qualified), compile on JDK 21 / Kotlin 2.0.21; upstream tests pass | `scripts/sandbox_build_and_test.sh core` |
| A-18 | The safety branches are protected by tests | **[E] after M0; false upstream** | Upstream suite killed 6 of 12 mutants; two controls ticked in upstream's checklist (scope check, egress data classes) were untested. All 12 killed after M0 | `scripts/mutation_check.py core` |
| A-19 | `PolicyEngine` enforces approval for high-impact effects | **Contradicted [E]** | Approval is opt-in per Action once HIGH_IMPACT is enabled (GAP-02, pinned by test) | `KnownGapCharacterizationTest` |
| A-20 | Approvals are bound to the approver | **Contradicted [E]** | Approver identity is recorded, never authorized (GAP-03, pinned by test) | `KnownGapCharacterizationTest` |
| A-21 | The Gradle build and CI files work | **[U]** | Not executed: Maven Central and the Gradle plugin portal are blocked in the authoring sandbox | First `gradle :core:test` on your machine |
