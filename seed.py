"""
Seeds the case log with representative data so the dashboard, approvals, and
case log are never empty for a first-time visitor (important when sharing the
live Railway link). Runs ONLY if the log is empty, so it never duplicates and
is safe to call on every startup. Re-seeds automatically after a restart.
"""
import store


def _c(msg, source, sender, subject, typ, urg, sent, ss, conf, team, status,
       flags, follow, appr, reply):
    return {
        "message": msg, "source": source, "sender": sender, "subject": subject,
        "type": typ, "urgency": urg, "sentiment": sent, "sentiment_score": ss,
        "confidence": conf, "engine": "AI (OpenAI)",
        "triage_note": f"{typ} ({urg}). Emotion reads as {sent}. Routed to {team}.",
        "routed_team": team, "status": status, "flags": flags, "follow_up": follow,
        "reply": reply, "steps": [{"name": "Processed", "detail": "Seeded example.", "done": True}],
        "approval": appr,
    }


SEED = [
    _c("I've been charged twice for my broadband this month and nobody is helping me.",
       "Email", "priya.sharma@gmail.com", "Double charged", "Complaint", "High", "Frustrated", 0.6, 0.90,
       "Senior Resolution Team", "Escalated - Awaiting Senior Handler", ["priority", "escalated"],
       "2-hour follow-up reminder set", "Auto", "I'm sorry for the double charge - I've escalated this with priority."),
    _c("What are your customer support opening hours on weekends?",
       "Web Form", "anon-web-4821", "Hours", "General Enquiry", "Low", "Neutral", 0.2, 0.93,
       "Auto-resolved (Knowledge Base)", "Resolved - Auto-response sent", ["auto-resolved"],
       "None - resolved", "Auto", "Our weekend support is open 9am-6pm. Happy to help further!"),
    _c("I'd like to upgrade my current plan to the 1 Gbps fibre package please.",
       "Email", "raj.kumar@outlook.com", "Upgrade", "Service Request", "Medium", "Neutral", 0.3, 0.89,
       "Provisioning Team", "Routed - In Progress", ["sla-tracked"],
       "SLA timer started (24h target)", "Auto", "Thanks - your upgrade request has been routed to Provisioning."),
    _c("This is the THIRD time my internet is down this week. I want a manager now or I'm cancelling.",
       "Shared Inbox", "support-inbox", "URGENT", "Escalation", "Critical", "Angry", 0.92, 0.94,
       "Supervisor / Senior Agent", "Escalated - Human Review Required",
       ["critical", "human-in-the-loop", "auto-resolution-paused"],
       "Immediate supervisor notification", "Pending", "I understand your urgency - a supervisor is reviewing this now."),
    _c("My connection has been extremely slow for 3 days, videos won't load. Please help.",
       "Chat", "live-chat-visitor", "Slow", "Complaint", "High", "Frustrated", 0.62, 0.86,
       "Senior Resolution Team", "Escalated - Awaiting Senior Handler", ["priority", "escalated"],
       "2-hour follow-up reminder set", "Auto", "Sorry about the slow speeds - I've raised this with priority."),
    _c("How much does it cost to add a second router to my home network?",
       "Web Form", "anon-web-5533", "Pricing", "General Enquiry", "Low", "Neutral", 0.2, 0.9,
       "Auto-resolved (Knowledge Base)", "Resolved - Auto-response sent", ["auto-resolved"],
       "None - resolved", "Auto", "Adding a second router is straightforward - here are the options."),
    _c("My latest bill is way higher than usual and I don't understand the extra charges.",
       "Email", "li.wei@hotmail.com", "Bill query", "Complaint", "Medium", "Frustrated", 0.55, 0.82,
       "Billing Team", "Routed - In Progress", ["sla-tracked"],
       "SLA timer started (24h target)", "Auto", "I've asked our Billing team to review and explain the charges."),
    _c("Please cancel my subscription effective at the end of this billing cycle.",
       "Email", "meera.nair@yahoo.com", "Cancel", "Service Request", "Medium", "Neutral", 0.3, 0.88,
       "Service Desk", "Routed - In Progress", ["sla-tracked"],
       "SLA timer started (24h target)", "Auto", "Your cancellation request has been logged for end of cycle."),
    _c("Thank you, the technician who came yesterday was excellent and fixed everything!",
       "Chat", "live-chat-visitor", "Thanks", "General Enquiry", "Low", "Positive", 0.8, 0.85,
       "Auto-resolved (Knowledge Base)", "Resolved - Auto-response sent", ["auto-resolved"],
       "None - resolved", "Auto", "Thank you so much for the kind words - I'll pass them on!"),
    _c("I need a new broadband connection installed at my new flat next week.",
       "Email", "sam.oliveira@gmail.com", "New connection", "Service Request", "Medium", "Neutral", 0.3, 0.87,
       "Field / Installation Team", "Routed - In Progress", ["sla-tracked"],
       "SLA timer started (24h target)", "Auto", "Great - I've routed your installation request to our field team."),
    _c("You promised a technician yesterday and nobody showed up. This is completely unacceptable.",
       "Shared Inbox", "support-inbox", "Missed technician", "Escalation", "Critical", "Angry", 0.9, 0.9,
       "Supervisor / Senior Agent", "Escalated - Human Review Required",
       ["critical", "human-in-the-loop", "auto-resolution-paused"],
       "Immediate supervisor notification", "Pending", "I'm very sorry - a supervisor is personally looking into this."),
    _c("hmm not sure honestly, just wanted to check something about my account i think",
       "Shared Inbox", "support-inbox", "Account question", "General Enquiry", "Low", "Neutral", 0.3, 0.45,
       "Human Triage Queue", "Held - Needs Human Triage", ["needs-human-review", "low-confidence"],
       "Awaiting human triage", "Pending", "This request was held for a human agent to review."),
]


def seed_if_empty() -> int:
    """Insert the seed rows only if the case log is currently empty."""
    if store.get_kpis().get("total", 0) == 0:
        for row in SEED:
            store.save_case(row)
        return len(SEED)
    return 0
