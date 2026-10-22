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

## Status

| Stage | What it covers | Status |
|---|---|---|
| 0 | Config and setup | passed in Colab (Python 3.13, crewai 1.15.28) |
| 1 | Gemini and CrewAI smoke test | passed in Colab on both models |
| 2 | Data download, parsing, license table | written, not yet run in Colab |
| 3–11 | Splits, tools, baseline, agents, evaluation, demo | not started |

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
