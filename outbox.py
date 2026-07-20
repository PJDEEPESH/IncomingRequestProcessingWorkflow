"""
Makes ONE remediation action genuinely real: the generated reply is written to
an `outbox/` folder as a .txt file. So "auto-response sent" is literally true -
the file exists on disk - instead of being only a label.

The other steps (route to team, notify supervisor, set SLA/reminder) remain
simulated in this POC; in production they map to Salesforce / Twilio / email /
a scheduler. Being explicit about that boundary is the honest, mature framing.
"""
import os
from datetime import datetime

OUTBOX_DIR = os.path.join(os.path.dirname(__file__), "outbox")


def write_reply(state: dict) -> str:
    """Write the reply to outbox/ and return the relative path."""
    os.makedirs(OUTBOX_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    rtype = (state.get("type") or "request").replace(" ", "")
    fname = f"{ts}_{rtype}.txt"
    path = os.path.join(OUTBOX_DIR, fname)

    content = (
        f"To:        {state.get('sender', '') or 'customer'}\n"
        f"Channel:   {state.get('source', '')}\n"
        f"Subject:   Re: {state.get('subject', '') or state.get('type', '')}\n"
        f"Type:      {state.get('type', '')} / {state.get('urgency', '')}\n"
        f"Routed to: {state.get('routed_team', '')}\n"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"{'-' * 56}\n"
        f"{state.get('reply', '')}\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return os.path.join("outbox", fname).replace("\\", "/")
