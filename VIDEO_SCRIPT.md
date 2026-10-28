# Video Outline (target 2.5 to 3 minutes). Speak in your own words.

**0:00-0:20 Problem.** Clinics receive bookings, billing questions, complaints and reviews across channels. Sorting them manually is slow and urgent messages can be missed.

**0:20-0:50 AI tools and why.** [Name the tools you used.] I used an AI assistant to plan and write the Python code and the in-app prompt. In the app, the classifier can call OpenAI, Gemini or a local Ollama model. [Say which you actually ran and why.]

**0:50-1:20 Prompt engineering.** Started broad, then added: a strict JSON schema, safety rules (no diagnosis, emergency escalation), and a human-approval step. Show the system prompt on screen.

**1:20-1:45 Challenges.** My first rule-based version mislabelled a long-wait complaint as "booking" and "bulk billing" as "billing". I tested edge cases, reordered the rules and narrowed keywords. Also added a fallback so a bad AI response never crashes the run.

**1:45-2:30 Demo.** In the terminal: `python triage.py sample_enquiries.csv --no-ai`. Open `output/triaged_results.csv` (point at the chest-pain message flagged high priority) and `weekly_report.md`. Then run AI mode, e.g. `--provider gemini` or `--provider ollama`, and compare replies with the rules.

**2:30-3:00 Outcome and next steps.** It turns an inbox into a prioritised, reviewable queue and a weekly report. Next: email/Sheets integration and measuring accuracy against human labels.

**Before recording:** run it yourself, change one thing (e.g. add a category or edit a reply), and be ready to explain it.
