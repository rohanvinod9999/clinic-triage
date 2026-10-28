# Clinic Enquiry & Review Triage (Python + AI)

An automation that reads patient enquiries and online reviews from a CSV, classifies each one,
drafts a safe reply for staff approval, flags urgent items, and produces a weekly report.

**Domain:** Healthcare / Technology | **Area:** Automation | **Language:** Python 3.9+

## Why
Small clinics get bookings, billing questions, complaints and public reviews through many channels.
Sorting them by hand is slow, and urgent or reputation-damaging messages can be missed.

## How it works
1. Reads `id, source, received, patient_name, message` from a CSV.
2. Classifies each message: booking, billing, complaint, praise, general_info, urgent_clinical.
3. Drafts a short reply. Staff must approve before anything is sent.
4. Writes `output/triaged_results.csv` and `output/weekly_report.md`.

**Two modes**
- **AI mode** (`--provider openai | gemini | ollama`): any LLM, via plain HTTPS calls, so no extra packages are needed.
  - `openai`: set `OPENAI_API_KEY` (default model `gpt-4o-mini`)
  - `gemini`: set `GEMINI_API_KEY` (default model `gemini-2.0-flash`; Google offers a free tier)
  - `ollama`: runs a model on your own computer, free and no key (install Ollama, then `ollama pull llama3.1`)
- **Rule-based mode** (default, or `--no-ai`): keyword rules, so it runs with no key or network.

If an AI call fails or returns invalid JSON, that message falls back to the rules instead of crashing the batch.
Emergency messages are forced to high priority even if the model under-rates them.
Model names change over time; override with `--model` if a default is retired.

## Try it in the browser (no install)
Open `index.html` (or the live link: **`https://YOUR-USERNAME.github.io/clinic-triage/`**).
1. It loads sample data automatically. Click **Run triage** to see categories, priorities and draft replies.
2. Engine **Rules** needs no key. To try **AI** mode, choose Gemini or OpenAI and paste your own API key
   (a free Gemini key is available from Google AI Studio). The key stays in your browser's memory only.
3. Upload your own CSV, edit the draft replies, and download the results and weekly report.

## Run the Python version
```bash
python triage.py sample_enquiries.csv --no-ai                        # no key needed
export GEMINI_API_KEY=your_key && python triage.py sample_enquiries.csv --provider gemini
python triage.py sample_enquiries.csv --provider ollama              # local, free
```
Options: `--model NAME`, `--outdir FOLDER`. Python 3.9+, standard library only.

## Safety design
- Messages mentioning emergency symptoms are forced to high priority and the reply directs to emergency services.
- The prompt forbids diagnosing, promising refunds, or inventing clinic policies.
- Drafts are for human approval only. Use made-up or de-identified data; do not upload real patient information to any AI service without proper agreements and consent.

## Limitations and next steps
- Keyword rules are simple and English-only; AI mode handles nuance better.
- Next: connect to email/Google Sheets, add reply tone settings, and log accuracy against human labels.
