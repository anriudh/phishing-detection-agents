# Agentic Phishing Email Detection and Explanation

## 1. Summary

This project builds a phishing detector that explains its decisions. Given a raw email, it returns a verdict (phishing, suspicious or legitimate), a risk score from 0 to 100, reasons tied to evidence quoted from the email, and a recommended action. Three CrewAI agents do the work on the Google Gemini free tier (`gemini-3.5-flash-lite`): a deterministic Technical Analyst, an LLM Content Analyst, and a Verdict agent that can run one capped disagreement round.

The system was compared with three other configurations on the same 100 held-out emails (50 phishing, 50 legitimate): the Technical Analyst's tools alone, a TF-IDF + logistic regression baseline, and a single LLM prompt with no agents.

The main findings:

- **The baseline scores highest (F1 0.990), but for the wrong reason.** On 20 modern legitimate emails it flags 17 as phishing or suspicious (85%). It has mostly learned to tell 2002 mailing-list posts from modern mail.
- **Both LLM configurations do well and hold up on modern mail.** LLM-only reaches F1 0.969 and the full system 0.958, with no false positives on either the subset or the 20 modern legitimate emails.
- **The full agent system doesn't beat the single prompt.** It uses 2.8 times the requests (276 against 100), and its recall is slightly lower (0.92 against 0.94).
- **The explanations are good when the verdict is right** (8.75/9 on a small rubric) and weaker when it is wrong (5.5/9).

## 2. System design

| Agent | How it works | Gemini requests |
|---|---|---|
| Technical Analyst | 13 deterministic Python checks on headers and URLs | 0 (1 only when asked a follow-up) |
| Content Analyst | LLM that reads the subject, body and link domains, and identifies intent and social-engineering tactics | 1 |
| Verdict and Explainer | LLM that merges both reports into a score, reasons, evidence and an action | 1, or 2 after a disagreement round |

**Technical Analyst.** The checks look for reply-to and return-path mismatches, display names that claim a domain or brand the sender doesn't own, look-alike letters from other scripts, explicit SPF/DKIM/DMARC failures, link text that doesn't match the link target, brand names inside foreign hosts, look-alike domains, punycode, URL shorteners, raw IP links and heavily abused top-level domains. Each check's most severe finding adds 35, 20 or 10 points, capped at 100. The weights were set by hand and were never tuned on the test subset.

**Content Analyst.** It gives a score, the email's intent, the tactics used and exact quotes as evidence. Python checks every quote against the email and drops any that don't appear in it.

**Disagreement round.** Python, not the LLM, decides whether the analysts disagree: their scores are 40 or more points apart, or one is 70 or above while the other is below 40. When they do, the Verdict agent writes one question to one analyst, that analyst answers, and the Verdict agent writes its final answer. The follow-up is a single `if` in Python, not a loop, so there is no code path to a second round. Agents cannot delegate to each other. An email therefore costs at most 4 requests.

**Labels.** The Verdict agent gives only a score. Python maps it to a label: 70 or more is phishing, 40 to 69 is suspicious, and below 40 is legitimate. The label can never contradict the score.

**Running on a free tier.** All LLM calls go through one function. It caches every step on disk so that interrupted runs resume, keeps a per-model daily request counter on Pacific time, throttles to 12 requests a minute, retries 429 and 503 errors with growing waits, and repairs an unparseable answer at most once. CrewAI's own retries are switched off, so every request is counted.

## 3. Data and evaluation set-up

| Source | Used as | Years | Emails | License |
|---|---|---|---|---|
| Nazario phishing corpus | phishing | 2023–2025 | 1,302 | CC-BY-4.0 |
| SpamAssassin public corpus (easy_ham, easy_ham_2, hard_ham) | legitimate | ~2002 | 4,150 | offered publicly for filter testing |

Full headers were required, because the Technical Analyst reads them. Duplicates were removed on normalised body text before splitting, which left 5,185 emails. These were split 80/20 into train and held-out sets, stratified by source. The test subset is 100 held-out emails, 50 of each class. The baseline trains on the train split only. Nothing was tuned on the subset.

**The era gap.** No public corpus with full headers has phishing and legitimate mail from the same period. Here the phishing is modern and the legitimate mail is from about 2002, so a model can separate the classes by date formats, header styles or the presence of authentication headers. To reduce this:

- the baseline sees only the subject and body, with digits, links and the corpus owner's name removed;
- the Content Analyst sees no headers at all, and the LLM-only configuration sees no date, routing or authentication headers;
- the Technical Analyst scores authentication only when a check explicitly fails.

**The robustness set** tests whether the gap still distorts the results. It is 20 modern legitimate emails: account alerts, receipts, verification codes, payment reminders, shared files and ordinary personal and work mail. Many of them use phishing vocabulary such as "verify", "payment" and "expires". They are synthetic. Claude, a different LLM from the one under test, wrote them, without looking at the Technical Analyst's checks.

## 4. Results

### 4.1 The 100-email subset

"Suspicious" counts as a phishing prediction, and a failed analysis counts as wrong. There were no failed analyses.

| Configuration | Precision | Recall | F1 | Gemini requests |
|---|---|---|---|---|
| Tools only | 1.00 | 0.26 | 0.413 | 0 |
| TF-IDF baseline | 0.98 | 1.00 | 0.990 | 0 |
| LLM only | 1.00 | 0.94 | 0.969 | 100 |
| Full system | 1.00 | 0.92 | 0.958 | 276 |

As expected, the tools alone are precise but miss most phishing. Much phishing has no technical trick at all, for example a plain request sent from a webmail account. The "obvious" demo phish scores 0 with the tools because it passes SPF and DKIM and imitates a bank that isn't in the brand list. The "subtle" one, which looks normal to a person, scores 90.

In the full system the disagreement round ran on 38 of the 100 emails and changed the label on 4 of them. Python dropped 4 quotes that weren't in the email.

### 4.2 The robustness set

| Configuration | Phishing | Suspicious | False-positive rate |
|---|---|---|---|
| Tools only | 0 | 0 | 0/20 |
| TF-IDF baseline | 11 | 6 | 17/20 (85%) |
| LLM only | 0 | 0 | 0/20 |
| Full system | 0 | 0 | 0/20 |

The baseline's top features confirm what this table suggests. Its phishing words are real phishing language ("your account", "password", "invoice"), but its legitimate words mostly describe 2002 technical mailing lists ("wrote", "linux", "rpm"). It learned "mailing-list post or not", and modern legitimate mail is not a mailing-list post. Its 0.990 F1 says more about the dataset than about phishing detection. The LLM configurations and the tools make no false positives here, even on emails full of phishing vocabulary.

## 5. Error analysis

The full system missed four phishing emails, and LLM-only missed three of the same four. The extra miss, `da18…`, was caught by LLM-only, which rated it suspicious at 55.

| Email | What it is | Why it was missed |
|---|---|---|
| `d469ad8478093057` | MetaMask referral lure from candymail.ch | The disagreement round lowered the score from 50 to 35 |
| `da18baee8ba4579e` | Credential phish in an `.htm` attachment | The parser reads body parts, not attachments, so the payload was never seen |
| `9707d726f4f78fca` | Fake order confirmation | Plausible transactional text and no technical signal |
| `bfd96e721832d068` | Staples "account not found" notice | Plausible transactional text and no technical signal |

Three patterns stand out.

1. **Passing authentication read as reassurance.** In three of the four misses, the verdict's first reason cites passing SPF, DKIM and DMARC as a sign of safety. The Verdict prompt says only that *missing* authentication is not evidence. The warning that clean headers don't make an email safe is in the Technical Analyst's follow-up prompt, which the Verdict agent never sees. Passing these checks only shows that the mail came from the domain it claims, and an attacker can own that domain or send through a real service such as Google Drive.
2. **The disagreement round can make things worse.** On `d469…`, the Technical Analyst scored 55 (a MetaMask display name on an unrelated domain) and the Content Analyst scored 0. The Verdict agent asked the Content Analyst, accepted its benign reading, and lowered the score from 50 to 35. That turned a correct "suspicious" into a miss. Of the four label changes, three moved the score down, and all four emails were phishing. The round tends to settle a disagreement in favour of the more reassuring analyst.
3. **Attachments are a blind spot.** An email whose body is only a disclaimer can still carry its attack in an attachment. This is a scope limit of the parser, not of the agents.

None of these were fixed by changing prompts. Tuning on the evaluation set would have made the reported numbers optimistic.

## 6. Explanation quality

Six full-system verdicts were scored by hand on three questions, each from 1 to 3. **Grounded:** is the evidence real, and does it cover what matters? **Understandable:** can a non-expert follow it, and does it agree with the verdict? **Action:** is the recommended action right for what the email really is?

| Case | Email | Grounded | Understandable | Action | Total /9 |
|---|---|---|---|---|---|
| Correct phishing | `7deba0cab6553440` | 3 | 3 | 3 | 9 |
| Correct phishing | `a62c055b1cf2435e` | 3 | 3 | 3 | 9 |
| Correct legitimate | `12865f8f440c21cc` | 2 | 3 | 3 | 8 |
| Correct legitimate (hard ham) | `9fb1f5ad3619e7ca` | 3 | 3 | 3 | 9 |
| Miss | `d469ad8478093057` | 2 | 1 | 2 | 5 |
| Miss | `da18baee8ba4579e` | 2 | 3 | 1 | 6 |

The correct cases average 8.75/9 and the misses 5.5/9. When the verdict is right, the evidence is real and specific, for example the Cyrillic letters hidden in "Wellsfargo" in the subtle demo phish. The two misses fail in different ways. In `d469…` the reasons list two red flags and the verdict still says legitimate. In `da18…` the reasoning is consistent but rests on the wrong evidence, and it tells the reader that no action is needed on a credential-phishing attachment. One rater (Claude) did the scoring with no inter-rater check, so these scores are an illustration, not a measurement.

## 7. Limitations

- **The era gap** affects all the subset numbers. The robustness set addresses it only partly: it has 20 emails, they are synthetic, and they contain no phishing.
- **Small scale.** 100 test emails, one model, one prompt version and one run. A difference of one or two emails, such as 0.94 against 0.92 recall, is within noise.
- **Narrow legitimate mail.** Most legitimate emails are 2002 technical mailing-list posts, which is not a typical inbox.
- **Free-tier model.** Results come from a small Flash Lite model. A larger model may use the disagreement round better.
- **Out of scope:** attachments, images, and phishing in languages other than English (a few Spanish and German phishing emails stay in the data because they are part of the labelled corpus).
- **Privacy.** Only public and synthetic emails were sent to Gemini, because the free tier may use inputs to improve Google's models.

## 8. Conclusions and future work

On this data, a single well-prompted LLM call is the best trade-off. It nearly matches the agent system's accuracy, costs a third of the requests, explains its verdicts, and, unlike the baseline, doesn't flag modern legitimate mail. The multi-agent design gives a cleaner audit trail, with separate technical and content reports and a recorded follow-up question, but the disagreement round as built doesn't pay for its extra requests. When it changes a label, it mostly moves the score toward the more reassuring analyst.

Possible next steps:

- Keep the higher score when a disagreement round only produces a benign explanation.
- Tell the Verdict agent explicitly to treat passing authentication as neutral.
- Parse HTML and text attachments.
- Evaluate on a legitimate corpus from the same period as the phishing, and on real rather than synthetic modern mail.

## Disclosures

The 20 robustness emails were written by Claude (Anthropic) for this project in October 2026. Claude also scored the explanation rubric. The Gemini model under test generated neither.
