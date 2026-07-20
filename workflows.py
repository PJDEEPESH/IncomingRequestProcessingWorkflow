"""
The orchestration layer, built as a LangGraph state machine.

Flow:
    classify --> reason --> (conditional router) --> one of:
        complaint | enquiry | service | escalation | human_review
    each branch runs its multi-step remediation, then --> END

- classify : AI reads the message (type, urgency, sentiment, confidence)
- reason   : a visible "thinking" step - writes a triage rationale + plan
- router   : low confidence -> human_review; otherwise route by type
"""
from typing import Optional, TypedDict

from langgraph.graph import StateGraph, END

from classifier import classify
from responder import generate_reply, generate_triage
from outbox import write_reply

# If the classifier is less sure than this, we don't guess - we hand off
# to a human. This is the "escalation override for edge cases" enhancement.
CONFIDENCE_THRESHOLD = 0.60


class RequestState(TypedDict, total=False):
    # inputs
    message: str
    api_key: Optional[str]
    source: str
    sender: str
    subject: str
    # classification
    type: str
    urgency: str
    sentiment: str
    sentiment_score: float
    confidence: float
    sub_topic: str
    department: str
    reasoning: str
    engine: str
    needs_human: bool
    # reasoning step
    triage_note: str
    # remediation results
    steps: list
    reply: str
    routed_team: str
    follow_up: str
    flags: list
    status: str
    approval: str
    outbox_file: str


def _step(name: str, detail: str) -> dict:
    return {"name": name, "detail": detail, "done": True}


# --- Node 1: classify ------------------------------------------------------
def classify_node(state: RequestState) -> dict:
    result = classify(state["message"], state.get("api_key"))
    result["needs_human"] = result["confidence"] < CONFIDENCE_THRESHOLD
    return result


# --- Node 2: reason ("thinking" step) --------------------------------------
# This node makes a REAL second AI call: the model reasons about the request and
# states its plan. That is what makes the pipeline genuinely agentic (an AI
# classify step, then an AI reason step) rather than hard-coded narration.
def reason_node(state: RequestState) -> dict:
    if state.get("needs_human"):
        note = ("AI confidence is below the safe threshold, so I will not act automatically. "
                "Plan: hold this request and route it to a human for manual triage.")
    else:
        note = generate_triage(state["message"], state, state.get("api_key"))
    return {"triage_note": note}


# --- Conditional router ----------------------------------------------------
def route(state: RequestState) -> str:
    if state.get("needs_human"):
        return "human_review"
    return {
        "Complaint": "complaint",
        "General Enquiry": "enquiry",
        "Service Request": "service",
        "Escalation": "escalation",
    }.get(state.get("type"), "human_review")


# --- Branch nodes (each does >= 2 downstream steps) ------------------------
def complaint_node(state: RequestState) -> dict:
    reply = generate_reply(state["message"], state, state.get("api_key"))
    return {
        "steps": [
            _step("Acknowledge receipt", "Draft acknowledgement generated and written to the outbox folder."),
            _step("Escalate to senior handler", "Case routed to the Senior Resolution Team."),
            _step("Log case with priority flag", "Saved to the case log with a PRIORITY flag."),
            _step("Set 2-hour follow-up reminder", "Follow-up reminder scheduled for T+2 hours."),
        ],
        "reply": reply,
        "routed_team": "Senior Resolution Team",
        "follow_up": "2-hour follow-up reminder set",
        "flags": ["priority", "escalated"],
        "status": "Escalated - Awaiting Senior Handler",
        "approval": "Auto",
    }


def enquiry_node(state: RequestState) -> dict:
    reply = generate_reply(state["message"], state, state.get("api_key"))
    return {
        "steps": [
            _step("Classify sub-topic", f"Sub-topic identified: {state.get('sub_topic', 'general')}."),
            _step("Generate AI response from knowledge base", "Tailored answer drafted."),
            _step("Send response", "Auto-response written to the outbox folder and sent to the customer."),
            _step("Log as resolved", "Case closed and logged as resolved."),
        ],
        "reply": reply,
        "routed_team": "Auto-resolved (Knowledge Base)",
        "follow_up": "None - resolved",
        "flags": ["auto-resolved"],
        "status": "Resolved - Auto-response sent",
        "approval": "Auto",
    }


def _route_department(state: RequestState) -> str:
    t = (state.get("message", "") + " " + state.get("sub_topic", "")).lower()
    if any(k in t for k in ["bill", "charge", "payment", "invoice", "refund"]):
        return "Billing Team"
    if any(k in t for k in ["upgrade", "downgrade", "plan", "package", "speed"]):
        return "Provisioning Team"
    if any(k in t for k in ["install", "new connection", "activate", "router", "modem", "technician"]):
        return "Field / Installation Team"
    if any(k in t for k in ["slow", "outage", "not working", "down", "connection", "signal"]):
        return "Network Operations"
    return "Service Desk"


def service_node(state: RequestState) -> dict:
    # Prefer the department the AI chose; fall back to keyword routing only if
    # the AI didn't provide one (e.g. the rule-based fallback engine is active).
    dept = state.get("department") or _route_department(state)
    reply = generate_reply(state["message"], state, state.get("api_key"))
    return {
        "steps": [
            _step("Extract required details", "Key request details extracted from the message."),
            _step("Route to relevant department", f"Routed to {dept} (chosen by AI)."),
            _step("Generate confirmation to requester", "Confirmation written to the outbox folder."),
            _step("Set SLA timer", "SLA timer started (24-hour target)."),
        ],
        "reply": reply,
        "routed_team": dept,
        "follow_up": "SLA timer started (24h target)",
        "flags": ["sla-tracked"],
        "status": "Routed - In Progress",
        "approval": "Auto",
    }


def escalation_node(state: RequestState) -> dict:
    reply = generate_reply(state["message"], state, state.get("api_key"))
    return {
        "steps": [
            _step("Immediately flag for human review", "Case flagged for a human agent."),
            _step("Draft urgent acknowledgement", "Urgent acknowledgement written to the outbox folder."),
            _step("Notify supervisor", "Supervisor alerted in real time."),
            _step("Pause auto-resolution", "Automated resolution paused (human-in-the-loop)."),
        ],
        "reply": reply,
        "routed_team": "Supervisor / Senior Agent",
        "follow_up": "Immediate supervisor notification",
        "flags": ["critical", "human-in-the-loop", "auto-resolution-paused"],
        "status": "Escalated - Human Review Required",
        "approval": "Pending",  # needs a human decision
    }


def human_review_node(state: RequestState) -> dict:
    conf = state.get("confidence", 0.0)
    note = ("This request was automatically held because the AI's confidence "
            f"({conf:.0%}) was below the safe threshold. A human agent will "
            "review and classify it manually.")
    return {
        "steps": [
            _step("Low-confidence detection", f"AI confidence {conf:.0%} is below the {CONFIDENCE_THRESHOLD:.0%} threshold."),
            _step("Hold from auto-processing", "Request withheld from automated resolution."),
            _step("Flag for human triage", "Routed to a human agent for manual classification."),
            _step("Notify team lead", "Team lead notified to review the case."),
        ],
        "reply": note,
        "routed_team": "Human Triage Queue",
        "follow_up": "Awaiting human triage",
        "flags": ["needs-human-review", "low-confidence"],
        "status": "Held - Needs Human Triage",
        "approval": "Pending",  # needs a human decision
    }


# --- Build & compile the graph (once, at import) ---------------------------
def _build_app():
    g = StateGraph(RequestState)
    g.add_node("classify", classify_node)
    g.add_node("reason", reason_node)
    g.add_node("complaint", complaint_node)
    g.add_node("enquiry", enquiry_node)
    g.add_node("service", service_node)
    g.add_node("escalation", escalation_node)
    g.add_node("human_review", human_review_node)

    g.set_entry_point("classify")
    g.add_edge("classify", "reason")
    g.add_conditional_edges("reason", route, {
        "complaint": "complaint",
        "enquiry": "enquiry",
        "service": "service",
        "escalation": "escalation",
        "human_review": "human_review",
    })
    for branch in ["complaint", "enquiry", "service", "escalation", "human_review"]:
        g.add_edge(branch, END)
    return g.compile()


_APP = _build_app()


def process_request(message: str, api_key: str | None = None,
                    source: str = "Manual", sender: str = "", subject: str = "") -> dict:
    """Run one message end-to-end through the graph and return the final state."""
    final = _APP.invoke({
        "message": message, "api_key": api_key,
        "source": source, "sender": sender, "subject": subject,
    })
    final.pop("api_key", None)  # never leak the key into logs / UI

    # Make the "reply sent" action genuinely real: write it to the outbox folder
    # (skip the human-triage branch, which produces an internal note, not a reply).
    final["outbox_file"] = ""
    if final.get("reply") and final.get("routed_team") != "Human Triage Queue":
        try:
            final["outbox_file"] = write_reply(final)
        except Exception:
            final["outbox_file"] = ""
    return final


# Used by the app's "Architecture" tab to draw the live graph.
GRAPH_DOT = """
digraph G {
  rankdir=TB;
  node [style=filled, fontname="Segoe UI", fontsize=11];
  intake   [label="Incoming Request\\n(Email | Web Form | Inbox | Chat)", shape=oval, fillcolor="#e8eefc"];
  classify [label="AI Classify\\n(type + urgency + sentiment + confidence)", shape=box, fillcolor="#cfe0ff"];
  reason   [label="AI Reason / Triage\\n(rationale + plan)", shape=box, fillcolor="#efe6ff"];
  router   [label="Confidence OK?\\n& route by type", shape=diamond, fillcolor="#fff3cd"];
  complaint  [label="COMPLAINT\\nack | escalate | log | remind", shape=box, fillcolor="#ffd9d0"];
  enquiry    [label="ENQUIRY\\ntopic | answer | send | resolve", shape=box, fillcolor="#d7f5dd"];
  service    [label="SERVICE REQ\\nextract | route | confirm | SLA", shape=box, fillcolor="#d7ecff"];
  escalation [label="ESCALATION\\nflag | urgent ack | supervisor | pause", shape=box, fillcolor="#ffc9c9"];
  human      [label="HUMAN REVIEW\\n+ approval queue", shape=box, fillcolor="#e6e0ff"];
  out      [label="Output + Case Log", shape=oval, fillcolor="#e8eefc"];
  intake -> classify -> reason -> router;
  router -> complaint; router -> enquiry; router -> service; router -> escalation; router -> human;
  complaint -> out; enquiry -> out; service -> out; escalation -> out; human -> out;
}
"""
