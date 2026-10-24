# Agentic Phishing Email Detection and Explanation

A college AI project. Given a raw email (headers and body), the system returns:

- a verdict: phishing, suspicious, or legitimate
- a risk score from 0 to 100
- plain-English reasons, each tied to specific evidence
- a recommended action for the reader

It uses three CrewAI agents on the Google Gemini free tier:

- **Technical Analyst**: deterministic Python checks on headers and URLs. It runs offline.
- **Content Analyst**: an LLM that identifies the email's intent and its social-engineering tactics.
- **Verdict and Explainer**: merges both reports. If the analysts disagree, it asks one of them a single follow-up question.

## How to run

1. Open `phishing_detection.ipynb` in Google Colab (File → Upload notebook).
2. Add your Gemini API key in Colab Secrets (the key icon in the sidebar) under the name `GEMINI_API_KEY`, and turn on notebook access for it. Never paste the key into a cell.
3. Run the cells top to bottom. When asked, allow Google Drive access. Cached results are stored under `/MyDrive/phish_project/`.

A run from an empty cache spends about 420 Gemini requests (the free tier allows 500 a day), and the Stage 11 demo only works from the cache. To reuse the results from development instead:

1. Upload `phish_project_cache.zip` (it holds the `cache/` and `results/` folders) to the top of My Drive.
2. Run the Stage 0 setup cells so Drive is mounted, then run this in a new cell:
   ```
   !unzip -n /content/drive/MyDrive/phish_project_cache.zip -d /content/drive/MyDrive/phish_project/
   ```
3. Then use Runtime → Run all. Every LLM step should report "0 new requests".

### Running locally (development)

The same notebook also runs on a local machine, which is how development is done:
1. Create a venv with Python 3.13 at `%USERPROFILE%\.venvs\phishing` (outside OneDrive) and install `requirements.txt` into it.
2. Put the key in a `.env` file in this folder, as one line: `GEMINI_API_KEY=...`. The `.env` file is git-ignored.
3. Run `~/.venvs/phishing/Scripts/python run_notebook.py`, or add `--until "Checkpoint 2"` to stop early. Outputs go to `runtime/executed.ipynb`, which is also git-ignored.

Locally, data, cache and results are stored in `runtime/` rather than on Google Drive.

## Status

| Stage | What it covers | Status |
|---|---|---|
| 0 | Config and setup | passed in Colab (Python 3.13, crewai 1.15.28) |
| 1 | Gemini and CrewAI smoke test | passed in Colab on both models |
| 2 | Data download, parsing, license table | passed locally (1,302 phishing, 4,150 legitimate) |
| 3 | Dedupe, split, 100-email subset, demo picks | passed locally (5,185 after dedupe; subset 50/50) |
| 4 | Technical Analyst tools, tools-only metrics | passed locally (precision 1.0, recall 0.26, F1 0.41) |
| 5 | TF-IDF + logistic regression baseline | passed locally (F1 0.97 held-out, 0.99 subset; see leakage note) |
| 6 | LLM plumbing: cache, daily counter, throttle, retry, parsing | passed locally (survived 4 real 503s; cache hit on rerun) |
| 7 | Agents and capped disagreement round | passed locally |
| 8 | LLM-only configuration | passed locally |
| 9 | Evaluation of all four configurations on the 100-email subset | passed locally (0 errors) |
| 9b | Robustness set: 20 synthetic modern legitimate emails | passed locally |
| 10 | Explanation quality rubric on six verdicts | passed locally (no API calls) |
| 11 | Cache-only demo with network connections switched off | passed locally (0 new requests) |

All evaluation uses `gemini-3.5-flash-lite` with prompt version v3. `gemini-3.1-flash-lite` is only the fallback, used if the primary model fails the smoke test.

## Results

### 100-email subset (50 phishing, 50 legitimate)

"Suspicious" counts as a phishing prediction. A failed analysis counts as wrong.

| Configuration | Precision | Recall | F1 | Gemini requests |
|---|---|---|---|---|
| Tools only (Technical Analyst) | 1.00 | 0.26 | 0.413 | 0 |
| TF-IDF + logistic regression baseline | 0.98 | 1.00 | 0.990 | 0 |
| LLM only | 1.00 | 0.94 | 0.969 | 100 |
| Full system (three agents) | 1.00 | 0.92 | 0.958 | 276 |

The full system ran 38 disagreement rounds. Four of them changed the label, and four quotes not found in the email were dropped as hallucinated.

### Robustness set (20 modern legitimate emails)

| Configuration | Flagged phishing | Flagged suspicious | False-positive rate |
|---|---|---|---|
| Tools only | 0 | 0 | 0/20 |
| TF-IDF baseline | 11 | 6 | 17/20 (0.85) |
| LLM only | 0 | 0 | 0/20 |
| Full system | 0 | 0 | 0/20 |

The baseline's near-perfect subset score doesn't hold up on modern legitimate mail: it flags 85% of it. That points to it learning the era gap (below) rather than phishing signals.

### Explanation quality (Stage 10)

Six full-system verdicts were scored 1–3 for grounded, understandable and action, out of 9. The four correct verdicts average 8.75/9 and the two misses average 5.5/9. One rater (Claude) scored them with no inter-rater check, so treat this as an illustration.

## Limitations

- **Era gap.** See the note under Data sources. The robustness set tests it, but only with 20 emails, and Claude wrote them rather than taking them from real mailboxes.
- **The full system doesn't beat LLM-only.** It uses 2.8 times the requests for a slightly lower recall.
- **Passing authentication read as reassurance.** In three of the four full-system misses, the first reason cites passing SPF/DKIM/DMARC, The Verdict prompt doesn't tell the agent to treat passing authentication as neutral.
- **The disagreement round can cause misses.** On `d469ad8478093057` the round lowered the score from 50 to 35, which turned a correct "suspicious" into a miss. Three of the four label changes moved scores down.
- **Attachments are never read.** `da18baee8ba4579e` carries its phishing in a `.htm` attachment, and the parser only reads body parts.
- **Small sample.** 100 emails, one model, one prompt version.

## Data sources and licenses

Checked on 2026-10-22. The data is downloaded at run time into Google Drive and is not stored in this repo.

| Source | Used as | Years | License / terms |
|---|---|---|---|
| [Nazario phishing corpus](https://monkey.org/~jose/phishing/), 2023–2025 mailboxes | phishing | 2023–2025 | CC-BY-4.0. Attribution: Jose Nazario. |
| [SpamAssassin public corpus](https://spamassassin.apache.org/old/publiccorpus/), 20030228 easy_ham, easy_ham_2, hard_ham | legitimate | ~2002 | No formal license. Offered publicly for testing spam filters, and copyright stays with the original senders. |

Considered but not used:
- SpamAssassin spam, because spam isn't phishing.
- Enron raw mail: 2001, 443 MB, no auth headers.
- [Zenodo "Phishing Email Curated Datasets"](https://zenodo.org/records/8339691) (CC-BY-4.0): no full headers, labels spam rather than phishing, and the Enron copy is preprocessed.

**Limitation:** the phishing emails come from 2023–2025 and the legitimate ones from about 2002, so a model could separate them by era rather than by phishing signals. The notebook reduces this by removing date, routing and auth headers from the inputs to the baseline and the LLM-only config. The Technical Analyst only scores an authentication header when it shows an outright fail.

## Privacy

Only public or synthetic emails are sent to Gemini. The free tier may use inputs to improve Google's models.
