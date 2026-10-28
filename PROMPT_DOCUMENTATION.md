# Prompt Documentation

> Edit this file before submitting. Replace bracketed notes with your own observations, and add any
> extra prompts you send. Reviewers want to see your real thinking, so keep your own wording.

## A. Prompts I gave the AI assistant while building the project

| # | My prompt (as sent) | What I was trying to achieve | Result / what changed |
|---|---|---|---|
| 1 | Shared the task PDF: "Can you help me with the requirements in the pdf so that I can get this job please?" | Get help meeting the assessment requirements | Assistant suggested checking the employer, avoiding the scraping option, and offered options |
| 2 | "A different project with the following requirements in python" | Switch to a Python-based project | Assistant asked which area of the PDF I meant |
| 3 | "yes it is related to the pdf document which one would you feel that will land me this job" | Pick the strongest area | Assistant recommended Automation (matches the "Automation Associate" title) and proposed a clinic enquiry triage tool |
| 4 | "yes build it and provide me the neccessary documents also please" | Build it and produce documentation | Built `triage.py`, sample data, README and these documents |
| 5 | "AI mode and not using claude API but normal" | Use a different AI provider instead of the Claude API | Switched to a provider-agnostic design: OpenAI, Gemini or local Ollama over plain HTTPS |
| 6 | [Add your follow-up prompts here, e.g. "add a priority column", "make replies shorter"] | [goal] | [result] |

## B. Prompt revision story (real iteration during the build)
- **Problem found in testing:** the first rule-based version labelled a complaint about waiting past an appointment as "booking",
  and labelled a question about "bulk billing" as "billing".
- **Fix:** reordered rules so safety and most-specific categories are checked first (urgent, complaint, billing, general_info, booking),
  and narrowed the billing keywords. All 10 sample messages then classified correctly.
- **Lesson:** order and specificity matter in classification; test with edge cases, not only easy ones.

- **Second revision:** replaced the single-provider API with a provider switch, and added two safety nets in code:
  invalid or off-schema AI output falls back to rules, and emergency messages are always forced to high priority.
  Tested the AI path offline with mocked responses (bad JSON, and a model that under-rated an emergency).

## C. Prompt used inside the application (system prompt)
```
You triage messages sent to a medical clinic (enquiries and online reviews).
Return ONLY a JSON object with these keys:
  category: one of booking, billing, complaint, praise, general_info, urgent_clinical
  sentiment: positive | neutral | negative
  priority: high | medium | low
  summary: max 15 words
  draft_reply: a polite reply of 2-4 sentences from the clinic team
Rules:
- If the message mentions symptoms that could be an emergency (chest pain, breathing trouble, severe bleeding),
  set category=urgent_clinical, priority=high, and the draft_reply must tell them to call emergency
  services (000 in Australia) or go to the nearest emergency department. Do not give other medical advice.
- Never diagnose, never promise refunds or outcomes, never invent clinic policies, hours or prices.
- For reviews, thank the person, apologise for the experience if negative, and invite them to call the clinic.
- Do not include markdown or any text outside the JSON.
```
**Why it is designed this way**
- A fixed JSON schema makes the output machine-readable; the code validates the category and falls back safely.
- Explicit "never" rules reduce risky outputs in a healthcare setting.
- A dedicated emergency rule overrides normal categorisation.
- Role and context ("medical clinic") are given up front; output format is last so it is followed strictly.
