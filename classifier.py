"""
Step 1 of the pipeline: read an incoming customer message and decide
  - type      (Complaint / General Enquiry / Service Request / Escalation)
  - urgency   (Low / Medium / High / Critical)
  - sentiment (Angry / Frustrated / Neutral / Positive) + intensity score
  - confidence (0-1, used later to trigger human review when the AI is unsure)

Primary engine = OpenAI (understands nuance, sarcasm, mixed intent).
Fallback engine = keyword rules (keeps the demo alive if the API is unavailable).
"""
import json
from llm import get_client, DEFAULT_MODEL

TYPES = ["Complaint", "General Enquiry", "Service Request", "Escalation"]
URGENCIES = ["Low", "Medium", "High", "Critical"]
SENTIMENTS = ["Angry", "Frustrated", "Neutral", "Positive"]
DEPARTMENTS = ["Billing Team", "Provisioning Team", "Field / Installation Team",
               "Network Operations", "Service Desk"]

SYSTEM_PROMPT = """You are a triage assistant for a broadband/telecom provider's
customer support inbox (company name: BlueStream Broadband).

Classify each incoming customer message. Return STRICT JSON only, with keys:
- "type": one of ["Complaint", "General Enquiry", "Service Request", "Escalation"]
- "urgency": one of ["Low", "Medium", "High", "Critical"]
- "sentiment": one of ["Angry", "Frustrated", "Neutral", "Positive"]
- "sentiment_score": a number 0 to 1 (how strong the emotion is)
- "confidence": a number from 0 to 1 (how sure you are of the type)
- "sub_topic": a short label (e.g. "billing", "outage", "plan upgrade", "hours")
- "department": the best team to handle it, one of ["Billing Team", "Provisioning Team", "Field / Installation Team", "Network Operations", "Service Desk"]
- "reasoning": one short sentence explaining the decision

Guidance:
- Complaint = something went wrong and the customer is unhappy (usually High).
- General Enquiry = a question asking for information (usually Low).
- Service Request = asking to do/change something (upgrade, install, cancel) (usually Medium).
- Escalation = angry, threatening to leave, demanding a manager, repeated failures, legal/urgent (Critical).
- Read tone and sarcasm carefully - "great, no internet AGAIN" is an angry Complaint/Escalation, not positive."""


def classify_ai(message: str, api_key: str | None = None):
    """Ask OpenAI to classify. Returns a dict or None on any failure."""
    client = get_client(api_key)
    if client is None:
        return None
    resp = client.chat.completions.create(
        model=DEFAULT_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Classify this message. Respond in JSON:\n\n{message}"},
        ],
    )
    data = json.loads(resp.choices[0].message.content)
    return _validate(data)


def _validate(data: dict) -> dict:
    """Clamp/validate a raw classification dict so it can never break the pipeline."""
    rtype = data.get("type") if data.get("type") in TYPES else "General Enquiry"
    urgency = data.get("urgency") if data.get("urgency") in URGENCIES else "Low"
    sentiment = data.get("sentiment") if data.get("sentiment") in SENTIMENTS else "Neutral"

    def _num(v, default=0.5):
        try:
            return max(0.0, min(1.0, float(v)))
        except (TypeError, ValueError):
            return default

    department = data.get("department") if data.get("department") in DEPARTMENTS else ""
    return {
        "type": rtype,
        "urgency": urgency,
        "sentiment": sentiment,
        "sentiment_score": round(_num(data.get("sentiment_score"), 0.5), 2),
        "confidence": round(_num(data.get("confidence"), 0.5), 2),
        "sub_topic": str(data.get("sub_topic", "general"))[:60],
        "department": department,
        "reasoning": str(data.get("reasoning", ""))[:240],
    }


# --- Fallback: simple keyword rules ---------------------------------------
ESCALATION_KW = ["manager", "supervisor", "unacceptable", "furious", "immediately",
                 "legal", "sue", "cancel my account", "third time", "days now",
                 "still not", "ridiculous", "worst", "escalate", "compensation", "now or"]
COMPLAINT_KW = ["charged twice", "overcharged", "double charged", "wrong", "not working",
                "no internet", "so slow", "disappointed", "complaint", "refund",
                "error", "failed", "poor", "keeps dropping", "no signal", "again"]
SERVICE_KW = ["upgrade", "downgrade", "change my plan", "new connection", "activate",
              "install", "cancel", "reschedule", "set up", "switch to", "move house",
              "transfer", "add a line", "book", "appointment", "pause"]
ENQUIRY_KW = ["what", "how", "when", "where", "hours", "price", "cost", "how much",
              "available", "do you", "can i", "is there", "which", "?"]

POSITIVE_KW = ["thank", "thanks", "great job", "love", "appreciate", "awesome", "happy", "excellent"]

URGENCY_BY_TYPE = {
    "Escalation": "Critical",
    "Complaint": "High",
    "Service Request": "Medium",
    "General Enquiry": "Low",
}


def compute_sentiment_rules(text: str, rtype: str):
    """Very simple emotion read for the fallback engine."""
    low = text.lower()
    caps_ratio = sum(1 for c in text if c.isupper()) / max(1, sum(1 for c in text if c.isalpha()))
    bang = text.count("!")

    if any(k in low for k in ESCALATION_KW) or caps_ratio > 0.3 or bang >= 2:
        return "Angry", round(min(0.95, 0.7 + bang * 0.05 + caps_ratio), 2)
    if rtype == "Complaint" or any(k in low for k in COMPLAINT_KW):
        return "Frustrated", 0.6
    if any(k in low for k in POSITIVE_KW) and "not " not in low:
        return "Positive", 0.7
    return "Neutral", 0.3


def classify_rules(message: str):
    """Keyword-based fallback. Never calls the network."""
    text = message.lower()
    scores = {
        "Escalation": sum(2.0 for kw in ESCALATION_KW if kw in text),
        "Complaint": sum(1.5 for kw in COMPLAINT_KW if kw in text),
        "Service Request": sum(1.2 for kw in SERVICE_KW if kw in text),
        "General Enquiry": sum(0.6 for kw in ENQUIRY_KW if kw in text),
    }
    best = max(scores, key=scores.get)
    top = scores[best]
    total = sum(scores.values())

    if top == 0:
        best, conf = "General Enquiry", 0.40
    else:
        conf = round(min(0.9, 0.55 + (top / (total + 1)) * 0.4), 2)

    sentiment, s_score = compute_sentiment_rules(message, best)
    return {
        "type": best,
        "urgency": URGENCY_BY_TYPE[best],
        "sentiment": sentiment,
        "sentiment_score": s_score,
        "confidence": conf,
        "sub_topic": "keyword-match",
        "reasoning": "Classified by keyword rules (AI engine unavailable).",
    }


def classify(message: str, api_key: str | None = None):
    """
    Public entry point. Tries AI first, falls back to rules, and tags which
    engine actually produced the answer (useful for the demo + audit log).
    """
    result = None
    try:
        result = classify_ai(message, api_key)
    except Exception:
        result = None  # any API/parse error -> fall back gracefully

    if result is None:
        result = classify_rules(message)
        result["engine"] = "Rule-based (fallback)"
    else:
        result["engine"] = "AI (OpenAI)"
    return result


def classify_both(message: str, api_key: str | None = None):
    """
    Run BOTH engines on the same message so the UI can show, side by side,
    where the AI beats naive keyword rules (e.g. sarcasm).
    """
    rules = classify_rules(message)
    rules["engine"] = "Rule-based"
    ai = None
    try:
        ai = classify_ai(message, api_key)
    except Exception:
        ai = None
    if ai is not None:
        ai["engine"] = "AI (OpenAI)"
    return {"ai": ai, "rules": rules}
