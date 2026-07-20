"""
SQLite case log = the audit trail + the data behind the dashboard and the
human-approval queue. Every processed request is saved here.
"""
import json
import os
import sqlite3
from datetime import datetime

import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "cases.db")

COLUMNS = [
    ("created_at", "TEXT"), ("source", "TEXT"), ("sender", "TEXT"),
    ("subject", "TEXT"), ("message", "TEXT"), ("type", "TEXT"),
    ("urgency", "TEXT"), ("sentiment", "TEXT"), ("sentiment_score", "REAL"),
    ("confidence", "REAL"), ("engine", "TEXT"), ("triage_note", "TEXT"),
    ("routed_team", "TEXT"), ("status", "TEXT"), ("flags", "TEXT"),
    ("follow_up", "TEXT"), ("reply", "TEXT"), ("steps", "TEXT"),
    ("approval", "TEXT"),
]

URGENCY_RANK = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    """Create the table, and migrate old DBs by adding any missing columns."""
    with _conn() as c:
        c.execute("CREATE TABLE IF NOT EXISTS cases (id INTEGER PRIMARY KEY AUTOINCREMENT)")
        existing = {row[1] for row in c.execute("PRAGMA table_info(cases)")}
        for name, coltype in COLUMNS:
            if name not in existing:
                c.execute(f"ALTER TABLE cases ADD COLUMN {name} {coltype}")


def save_case(state: dict) -> int:
    with _conn() as c:
        cur = c.execute("""
            INSERT INTO cases (created_at, source, sender, subject, message, type,
                urgency, sentiment, sentiment_score, confidence, engine, triage_note,
                routed_team, status, flags, follow_up, reply, steps, approval)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            state.get("source", "Manual"), state.get("sender", ""),
            state.get("subject", ""), state.get("message", ""),
            state.get("type", ""), state.get("urgency", ""),
            state.get("sentiment", ""), state.get("sentiment_score", 0.0),
            state.get("confidence", 0.0), state.get("engine", ""),
            state.get("triage_note", ""), state.get("routed_team", ""),
            state.get("status", ""), ", ".join(state.get("flags", [])),
            state.get("follow_up", ""), state.get("reply", ""),
            json.dumps(state.get("steps", [])), state.get("approval", "Auto"),
        ))
        return cur.lastrowid


def get_cases_df() -> pd.DataFrame:
    with _conn() as c:
        return pd.read_sql_query("SELECT * FROM cases ORDER BY id DESC", c)


def update_approval(case_id: int, decision: str):
    """Human decision on a pending case: 'Approved' or 'Rejected'."""
    new_status = ("Approved - Actioned by human" if decision == "Approved"
                  else "Rejected - Returned to queue")
    with _conn() as c:
        c.execute("UPDATE cases SET approval=?, status=? WHERE id=?",
                  (decision, new_status, case_id))


def get_pending_df() -> pd.DataFrame:
    """Cases waiting on a human decision (the approval queue)."""
    df = get_cases_df()
    if df.empty:
        return df
    pend = df[df["approval"] == "Pending"].copy()
    if pend.empty:
        return pend
    pend["rank"] = pend["urgency"].map(URGENCY_RANK).fillna(9)
    return pend.sort_values(["rank", "id"]).drop(columns=["rank"])


def get_priority_queue() -> pd.DataFrame:
    """All open (not resolved/approved) cases, most urgent first."""
    df = get_cases_df()
    if df.empty:
        return df
    open_df = df[~df["status"].str.startswith(("Resolved", "Approved"), na=False)].copy()
    if open_df.empty:
        return open_df
    open_df["rank"] = open_df["urgency"].map(URGENCY_RANK).fillna(9)
    return open_df.sort_values(["rank", "id"]).drop(columns=["rank"])


def get_kpis() -> dict:
    df = get_cases_df()
    if df.empty:
        return {"total": 0}
    total = len(df)
    auto = int((df["approval"] == "Auto").sum())
    return {
        "total": total,
        "automation_rate": round(100 * auto / total),
        "avg_confidence": round(100 * df["confidence"].mean()),
        "pending": int((df["approval"] == "Pending").sum()),
        "critical": int((df["urgency"] == "Critical").sum()),
    }


def get_stats() -> dict:
    df = get_cases_df()
    if df.empty:
        return {"total": 0, "by_type": {}, "by_urgency": {}, "by_status": {}, "by_sentiment": {}}
    return {
        "total": len(df),
        "by_type": df["type"].value_counts().to_dict(),
        "by_urgency": df["urgency"].value_counts().to_dict(),
        "by_status": df["status"].value_counts().to_dict(),
        "by_sentiment": df["sentiment"].value_counts().to_dict(),
    }


def clear_cases():
    with _conn() as c:
        c.execute("DELETE FROM cases")
