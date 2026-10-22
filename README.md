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
| 0 | Config and setup | written, not yet run in Colab |
| 1 | Gemini and CrewAI smoke test | written, not yet run in Colab |
| 2–11 | Data, tools, baseline, agents, evaluation, demo | not started |

## Data sources and licenses

Not filled in yet. Stage 2 will check which corpora are available and record each one's license here.

## Privacy

Only public or synthetic emails are sent to Gemini. The free tier may use inputs to improve Google's models.
