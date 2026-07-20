"""
Generates the customer-facing reply for a request. The tone changes per
request type (apologetic for complaints, informative for enquiries, etc.).

AI writes the reply; if the AI is unavailable we drop to a safe template so
the branch still produces an output.
"""
from llm import get_client, DEFAULT_MODEL

TONE = {
    "Complaint": "empathetic and apologetic - acknowledge the problem, take ownership, and say it is being escalated to a senior handler",
    "General Enquiry": "friendly, clear and informative - answer the question directly and concisely",
    "Service Request": "professional and confirming - restate what will be done and the next step",
    "Escalation": "urgent, calm and reassuring - acknowledge the seriousness and promise immediate human attention",
}

TEMPLATE = {
    "Complaint": ("Thank you for reaching out, and I'm sorry for the trouble this has caused. "
                  "I've logged your complaint with priority and escalated it to a senior handler "
                  "who will follow up with you within 2 hours."),
    "General Enquiry": ("Thanks for your question! Here's the information you asked for. "
                        "If you need anything else, just reply to this message and we'll be happy to help."),
    "Service Request": ("Thank you - I've received your request and routed it to the right team. "
                        "You'll receive a confirmation shortly and we'll keep you updated on progress."),
    "Escalation": ("I completely understand your urgency and I'm sorry for the experience so far. "
                   "I've flagged this for immediate human review and notified a supervisor, who will "
                   "personally look into it right away."),
}


def template_reply(rtype: str) -> str:
    return TEMPLATE.get(rtype, TEMPLATE["General Enquiry"])


def generate_triage(message: str, classification: dict, api_key: str | None = None) -> str:
    """
    The 'reasoning' node's brain: the AI thinks about the request and states its
    reasoning + a recommended action plan in 1-2 sentences. This is a real LLM
    call (not a template), which is what gives the pipeline its agentic feel.
    Falls back to a templated note if the AI is unavailable.
    """
    rtype = classification.get("type", "General Enquiry")
    urg = classification.get("urgency", "")
    sent = classification.get("sentiment", "")
    fallback = (f"{classification.get('reasoning', '') or 'Assessed the request intent and tone.'} "
                f"Emotion reads as {sent}. Plan: handle as a {rtype} ({urg} urgency).")

    client = get_client(api_key)
    if client is None:
        return fallback
    try:
        resp = client.chat.completions.create(
            model=DEFAULT_MODEL,
            temperature=0.3,
            max_tokens=90,
            messages=[
                {"role": "system", "content": (
                    "You are a support triage supervisor. In 2 short sentences, give your "
                    "reasoning about this request and the recommended action plan. Be concise and specific.")},
                {"role": "user", "content": (
                    f'Message: "{message}"\n'
                    f"Classified as: {rtype}, urgency {urg}, sentiment {sent}.\n"
                    "Give your triage reasoning and the plan.")},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return fallback


def generate_reply(message: str, classification: dict, api_key: str | None = None) -> str:
    """Write a short, tone-appropriate reply for the given request."""
    rtype = classification.get("type", "General Enquiry")
    client = get_client(api_key)
    if client is None:
        return template_reply(rtype)

    tone = TONE.get(rtype, "professional and helpful")
    system = ("You are a customer support agent for BlueStream Broadband. "
              "Write a short reply of 3-5 sentences. Do not invent specific "
              "account numbers, prices, or dates - keep it reassuring but general.")
    user = (f'Customer message:\n"{message}"\n\n'
            f"Request type: {rtype}\n"
            f"Write a reply that is {tone}.")
    try:
        resp = client.chat.completions.create(
            model=DEFAULT_MODEL,
            temperature=0.4,
            max_tokens=250,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return template_reply(rtype)
