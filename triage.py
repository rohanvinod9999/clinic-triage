#!/usr/bin/env python3
"""Clinic Enquiry & Review Triage.

Reads patient enquiries/reviews from a CSV, classifies each one, drafts a safe
reply for staff to approve, flags urgent items, and writes a weekly report.

Optional AI mode works with OpenAI, Google Gemini, or a local Ollama model (no key, free).
Without --provider it uses a transparent rule-based classifier so it runs anywhere.
Use made-up or de-identified data only.
"""
import argparse, csv, json, os, re, sys, urllib.request, urllib.error
from collections import Counter

CATEGORIES = ["booking", "billing", "complaint", "praise", "general_info", "urgent_clinical"]
# Provider -> (default model, API key env var). Ollama runs locally and needs no key.
PROVIDERS = {
    "openai": ("gpt-4o-mini", "OPENAI_API_KEY"),
    "gemini": ("gemini-2.0-flash", "GEMINI_API_KEY"),
    "ollama": ("llama3.1", None),
}

SYSTEM_PROMPT = """You triage messages sent to a medical clinic (enquiries and online reviews).
Return ONLY a JSON object with these keys:
  category: one of {cats}
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
- Do not include markdown or any text outside the JSON.""".format(cats=", ".join(CATEGORIES))

RULES = [  # (category, regex) checked in order: safety first, then most specific
    ("urgent_clinical", r"chest pain|can'?t breathe|trouble breathing|severe bleeding|unconscious|suicid"),
    ("complaint", r"wait|rude|disappoint|nightmare|terrible|awful|unhappy"),
    ("billing", r"charged|invoice|refund|billed|billing|medicare number|payment"),
    ("general_info", r"telehealth|opening hours|do you offer|bulk bill"),
    ("booking", r"book|appointment|reschedul|cancel|available|free\b"),
    ("praise", r"wonderful|thank|great|excellent|amazing|lovely"),
]
REPLIES = {
    "urgent_clinical": "Thank you for contacting us. If you are experiencing chest pain or another emergency symptom, please call 000 or go to your nearest emergency department now. Please do not wait for an appointment.",
    "billing": "Thank you for letting us know. Our accounts team will review this and get back to you. You can also call the clinic to speak with them directly.",
    "booking": "Thanks for getting in touch. Our reception team will check availability and confirm a time with you shortly.",
    "complaint": "Thank you for your feedback, and we are sorry your experience fell short. Please call the clinic so a manager can look into this properly.",
    "praise": "Thank you so much for the kind words. We have shared them with the team and look forward to seeing you again.",
    "general_info": "Thanks for your enquiry. A member of our team will reply with the details you asked about.",
}

def rule_based(message):
    text = message.lower()
    cat = next((c for c, rx in RULES if re.search(rx, text)), "general_info")
    sentiment = {"praise": "positive", "complaint": "negative", "urgent_clinical": "negative"}.get(cat, "neutral")
    priority = "high" if cat == "urgent_clinical" else "medium" if cat in ("billing", "complaint") else "low"
    return {"category": cat, "sentiment": sentiment, "priority": priority,
            "summary": message[:80].strip(), "draft_reply": REPLIES[cat], "engine": "rules"}

def _post(url, payload, headers):
    req = urllib.request.Request(url, json.dumps(payload).encode(), {"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def call_llm(provider, model, message):
    """Send one message to the chosen provider and return the raw text reply."""
    if provider == "openai":
        d = _post("https://api.openai.com/v1/chat/completions",
                  {"model": model, "response_format": {"type": "json_object"},
                   "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": message}]},
                  {"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]})
        return d["choices"][0]["message"]["content"]
    if provider == "gemini":
        url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % model
        d = _post(url, {"system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                        "contents": [{"role": "user", "parts": [{"text": message}]}],
                        "generationConfig": {"responseMimeType": "application/json"}},
                  {"x-goog-api-key": os.environ["GEMINI_API_KEY"]})
        return d["candidates"][0]["content"]["parts"][0]["text"]
    if provider == "ollama":
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        d = _post(host + "/api/chat", {"model": model, "stream": False, "format": "json",
                  "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                               {"role": "user", "content": message}]}, {})
        return d["message"]["content"]
    raise ValueError("unknown provider: " + provider)

def ai_classify(provider, model, message):
    raw = call_llm(provider, model, message)
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    data = json.loads(raw)
    if data.get("category") not in CATEGORIES:
        raise ValueError("unknown category: %r" % data.get("category"))
    for k in ("sentiment", "priority", "summary", "draft_reply"):
        data.setdefault(k, "")
    if data["category"] == "urgent_clinical":  # safety net: never trust the model to downgrade emergencies
        data["priority"] = "high"
    data["engine"] = "ai:" + provider
    return data

def classify(ai, message):
    if ai:
        try:
            return ai_classify(ai[0], ai[1], message)
        except Exception as e:  # bad JSON, API error, etc.: fall back, never crash the batch
            print("  AI failed (%s); using rules." % type(e).__name__, file=sys.stderr)
    return rule_based(message)

def write_report(rows, path):
    cats = Counter(r["category"] for r in rows)
    sent = Counter(r["sentiment"] for r in rows)
    urgent = [r for r in rows if r["priority"] == "high"]
    lines = ["# Weekly Enquiry & Review Report", "",
             "Total messages: **%d**" % len(rows), "", "## By category"]
    lines += ["- %s: %d" % (c, n) for c, n in cats.most_common()]
    lines += ["", "## Sentiment"] + ["- %s: %d" % (s, n) for s, n in sent.most_common()]
    lines += ["", "## Needs human attention now"]
    lines += ["- #%s (%s): %s" % (r["id"], r["category"], r["summary"]) for r in urgent] or ["- None"]
    neg = [r for r in rows if r["sentiment"] == "negative" and r["source"] == "google_review"]
    lines += ["", "## Negative public reviews to follow up"]
    lines += ["- #%s %s: %s" % (r["id"], r["patient_name"], r["summary"]) for r in neg] or ["- None"]
    lines += ["", "_All draft replies require staff approval before sending._"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="CSV with columns id,source,received,patient_name,message")
    ap.add_argument("--outdir", default="output")
    ap.add_argument("--provider", choices=list(PROVIDERS), default=os.environ.get("TRIAGE_PROVIDER"),
                    help="AI provider: openai, gemini or ollama (local, no key). Omit for rule-based mode.")
    ap.add_argument("--model", help="override the provider's default model")
    ap.add_argument("--no-ai", action="store_true", help="force rule-based mode")
    args = ap.parse_args()

    ai = None
    if args.provider and not args.no_ai:
        default_model, key_var = PROVIDERS[args.provider]
        if key_var and not os.environ.get(key_var):
            sys.exit("Set %s first (or use --provider ollama, or --no-ai)." % key_var)
        ai = (args.provider, args.model or default_model)
    print("Mode:", "AI (%s, %s)" % ai if ai else "rule-based")

    with open(args.input, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = {"id", "source", "received", "patient_name", "message"} - set(reader.fieldnames or [])
        if missing:
            sys.exit("Input CSV is missing columns: " + ", ".join(sorted(missing)))
        inputs = list(reader)

    rows = []
    for item in inputs:
        res = classify(ai, item["message"])
        rows.append({**item, **{k: res.get(k, "") for k in
                    ("category", "sentiment", "priority", "summary", "draft_reply", "engine")}})
        print("#%s -> %s [%s]" % (item["id"], res["category"], res["priority"]))

    os.makedirs(args.outdir, exist_ok=True)
    with open(os.path.join(args.outdir, "triaged_results.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    write_report(rows, os.path.join(args.outdir, "weekly_report.md"))
    print("Wrote %s/triaged_results.csv and weekly_report.md" % args.outdir)

if __name__ == "__main__":
    main()
