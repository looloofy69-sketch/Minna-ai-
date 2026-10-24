# Interview guide v0.1: women who sell (30 minutes)

Part of Track P. Software cannot replace this step: it is where the plan's first stop condition is tested ("interviews in the chosen segment find no repeated, painful task that Minna can complete"). Language: run the interview in Darija, with French terms as the interviewee uses them. French version: `interview_guide_fr.md`.

## 0. Fix these before interview 1 (write them down, date them, do not change them later)

| Decision | Default proposed here | Who decides |
|---|---|---|
| Number of interviews | 14 for structured task discovery, not prevalence estimation; section 8 gives hypothetical binomial arithmetic only | project owner |
| What counts as a **qualifying** interview | The interviewee describes a task she does **at least weekly**, gives a **concrete recent example**, states a **cost** (minutes, money lost, customers lost, errors) and the task is **inside v1 scope** (read, draft, create a parcel, look up status, with approval; no money movement; no legal, health or safety advice) | project owner |
| "Go" threshold (how many qualifying interviews to continue to M2) | Not set by this kit: fix a decision rule before interviewing, based on evidence of repeated, costly, in-scope tasks and credible counter-evidence—not on a prevalence confidence bound | project owner |
| Recruitment | At least **5** distinct channels (training programme, social group, personal network, courier customers, local market or association) and **at most 3 interviews per channel**, so no channel exceeds 3 of 14 (about 21%) | research lead |

Because recruitment is purposive and capped by channel, these interviews do not form a probability sample. Record channel and referral chain for every interview. Do not interpret the section 8 table as a confidence interval for these participants, the recruited channels, or women in Algeria. Use the interviews to discover and document tasks, not to estimate prevalence.

## 1. Rules for the interviewer

1. Ask about **what happened last time**, never about what she would do or might like. Opinions about an idea are cheap and flattering; a described Tuesday is evidence.
2. **Do not mention the assistant** until section 7, and only after every behaviour question is done. Never pitch, never defend the idea, never promise a feature, a price or a date.
3. Let silences run. Count to five before the next question.
4. Write what she **said and did**, in her words, with numbers. Mark your own interpretations with "I:".
5. Never ask for names, phone numbers or addresses of her customers. If she shows a chat, she masks names and numbers first. No photographs of screens unless she agrees and the personal details are covered.
6. If she gets uncomfortable, skip the question and say so in the notes. A skipped question is data; a pressured answer is noise.

| Instead of | Ask |
|---|---|
| Would you use an assistant that does this? | Tell me about the last time this took you too long. What did you do? |
| Do you find delivery difficult? | Walk me through the last parcel you sent, from the message to the parcel leaving your hands. |
| How much would you pay? | In the last year, have you paid for anything to help with your business (an app, a person, a course)? What, and how did you pay? |
| Is privacy important to you? | Does anyone else use your phone or read your messages? What do you do about that? |

## 2. Opening and consent (3 minutes)

Say, in your own words:

> Thank you for your time. I work with [ORGANISATION]. We are studying how women who sell use their phones for orders and delivery, to decide whether a phone assistant would be useful and how it should work. This is not a sales visit and nothing is being sold. The conversation takes about 30 minutes. You can skip any question and stop at any time. I will not ask for your name or for your customers' details. I take notes without your name, only an interview number. May I also record the audio? You can say no and we continue with notes only. If you agree, the recording is kept [WHERE / HOW LONG] and used only for this study. You can ask us to delete the notes or recording associated with your interview number until [WITHDRAWAL DEADLINE] by contacting [CONTACT]. After that, if findings have been aggregated and the link removed, we may no longer be able to locate individual records. Do you agree to take part?

Tick in the notes: agreed to take part [ ] · agreed to audio [ ]. If she is under 18, thank her and stop. The wording of the consent and the retention period are for the data-protection lawyer to confirm (decision D3).

## 3. Warm-up (3 minutes)

- What do you sell, and how long have you been selling?
- How did you start? Who helped you?
- In a normal week, how many orders do you handle? Where do they come from?

Record: segment (sells monthly / sometimes / plans to sell), channels, volume.

## 4. The last order, step by step (10 minutes, the core)

"Tell me about the last order you handled, from the first message to the money in your hand."

Follow the order of events. At each step ask: **what did you do, with which app or paper, how long did it take, what went wrong?**

Probes, only if she has not covered them:
- The first message: in which app? Which language or script (Darija in Arabic letters, Latin letters, French)?
- How did you confirm the details? How many messages back and forth?
- How did you prepare and pack it?
- How did it get to the customer? If a delivery company: which one, how did you create the parcel, where did you type the address, who paid the fee?
- What happened after: delivered, refused, returned, lost, late? What did you do then?
- When and how did the money arrive?

Fill in the step table in section 9 while she talks.

## 5. Pain and what she already does about it (6 minutes)

- Which of those steps do you like least? Which takes the most time?
- The last time that went wrong, what did you do?
- Has anyone helped you with it (a relative, an employee, a friend)? Have you paid anyone?
- Have you tried an app, a spreadsheet or a template for it? Why did you stop, or why do you still use it?
- In the last month, how many parcels were refused or came back? What did that cost you?

This section is where the evidence is. A person who has already paid, built a workaround or lost money on a problem has shown you the problem is real; a person who says it is "hard" has shown you nothing yet.

## 6. Money, phone and privacy (4 minutes)

- What do you spend in a month on mobile data and phone credit?
- In the last year, have you paid for anything for your business? How did you pay (cash, CCP / BaridiMob, card)?
- Who else uses your phone, or reads your messages? Do you share any account?
- If a program read your customers' messages to help you, what would worry you? What would you want to check first?

Ask the last one as an open question and write her words. Do not read out options.

## 7. The idea, last (3 minutes)

Only now read the card:

> Imagine an assistant on your phone. You tell it what you need, for example "send this order to the delivery company". It prepares the action and shows it to you. Nothing is sent or created until you approve it. It does not move money. This is an idea we are studying; it is not available yet.

Then ask:
- Think of last week. Was there a moment you would have used it? Which one?
- What would you check before you approve something?
- What would make you stop using it?
- Which of your tasks would you **not** hand to it, even with approval?

Do not ask "would you use it?" and do not ask for a price here. If she names a price on her own, write it with her reason.

## 8. What the counts can and cannot prove

Count only **qualifying** interviews (section 0). The tables below are mathematical reference values under a hypothetical independent random-sample model. They are **not valid prevalence estimates or confidence bounds for this purposive recruitment protocol**. Computed with `python3 survey_cli.py plan`; checked by the kit's tests.

| Qualifying of 14 | Hypothetical lower bound* | Hypothetical upper bound* |
|---|---|---|
| 0 of 14 | 0.0% | 19.3% |
| 1 of 14 | 0.4% | 29.7% |
| 2 of 14 | 2.6% | 38.5% |
| 3 of 14 | 6.1% | 46.6% |
| 4 of 14 | 10.4% | 54.0% |
| 5 of 14 | 15.3% | 61.0% |
| 6 of 14 | 20.6% | 67.5% |
| 7 of 14 | 26.4% | 73.6% |
| 8 of 14 | 32.5% | 79.4% |
| 9 of 14 | 39.0% | 84.7% |
| 10 of 14 | 46.0% | 89.6% |
| 11 of 14 | 53.4% | 93.9% |
| 12 of 14 | 61.5% | 97.4% |
| 13 of 14 | 70.3% | 99.6% |
| 14 of 14 | 80.7% | 100.0% |

If you stop at 10 interviews:

| Qualifying of 10 | Hypothetical lower bound* | Hypothetical upper bound* |
|---|---|---|
| 0 of 10 | 0.0% | 25.9% |
| 1 of 10 | 0.5% | 39.4% |
| 2 of 10 | 3.7% | 50.7% |
| 3 of 10 | 8.7% | 60.7% |
| 4 of 10 | 15.0% | 69.6% |
| 5 of 10 | 22.2% | 77.8% |
| 6 of 10 | 30.4% | 85.0% |
| 7 of 10 | 39.3% | 91.3% |
| 8 of 10 | 49.3% | 96.3% |
| 9 of 10 | 60.6% | 99.5% |
| 10 of 10 | 74.1% | 100.0% |

*These bounds are mathematical reference values under the hypothetical random-sample model; they are **not valid prevalence estimates for this recruitment protocol**.

How to use the interviews:
- Interviews discover tasks and test whether a problem is concrete, recurring, costly and inside the planned product scope. They do not establish how common it is.
- Do not use 0 of 14, 14 of 14, or any other count as a population prevalence bound or automatic stop condition. Record what was observed, what contradicted the hypothesis, and which channels were missing.
- Fourteen is a **discovery** sample. The survey's n=106 precision calculation also assumes an appropriate sampling model; it cannot make a convenience sample representative. Use survey results as channel-specific descriptive evidence unless the sampling design justifies a wider inference.

## 9. Notes sheet (one per interview, no names)

| Field | Value |
|---|---|
| Interview number / date / interviewer | |
| Language(s) used | |
| Recruitment channel | |
| Segment (sells monthly / sometimes / plans to) | |
| Consent: taking part / audio | |
| Orders per week; channels; languages written | |

Last-order steps:

| Step | Tool or paper | Minutes | What went wrong | Quote |
|---|---|---|---|---|
| First message | | | | |
| Confirming details | | | | |
| Packing | | | | |
| Parcel creation | | | | |
| Tracking / calling the customer | | | | |
| Money received | | | | |

Evidence for each pain she named (use the highest level that applies):

| Level | Meaning |
|---|---|
| 0 | Opinion or a hypothetical ("it would be hard") |
| 1 | A real past event, no cost stated |
| 2 | A real past event with a cost: minutes, money, customers, errors |
| 3 | She paid, built a workaround, or hired help because of it |

Qualifying? Weekly or more [ ] · concrete recent example [ ] · cost stated [ ] · inside v1 scope [ ] · all four = qualifying.

Also note: tasks she would not hand over; what she would check before approving; who else touches her phone; any price she named unprompted and why; anything that contradicted what we expected.

## 10. Safeguarding and ethics

- Keep to business topics. Do not ask about family finances, relationships or safety at home. If she raises them, listen, do not give legal or personal advice, offer to pause or stop, and offer the support contacts the research lead has prepared before fieldwork: [SUPPORT CONTACTS].
- Meet in a place she chooses and feels comfortable in; no home visits alone; tell a colleague where and when.
- If she says someone controls her phone, do not follow up with messages to that phone unless she has said it is safe to.
- Keep notes under interview numbers. Keep the sheet that links numbers to contact details (if one exists at all) apart from the notes.
- Nothing here has been checked by a lawyer. Retention, recording and consent wording are decision D3.

## 11. After each interview (within 24 hours)

1. Finish the notes while you remember. Mark anything you inferred with "I:".
2. Fill in the qualifying check and the evidence level.
3. Add the interview to the tally (counts only, no names). After every 5 interviews, list what surprised you and what contradicted the plan.
4. Do not change the criteria. If you think they were wrong, write that down and finish the planned interviews under the original criteria first.
5. At the end, write one page: the count of qualifying interviews out of the total, the concrete tasks and costs observed, the three most common workarounds, the strongest counter-evidence, and the recruitment channel breakdown. Do not interpret the table as prevalence evidence.
