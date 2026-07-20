"""
FastAPI backend - a thin HTTP layer over the existing LangGraph pipeline.

The React/TypeScript frontend calls these endpoints; all the AI logic lives in
classifier.py / workflows.py / store.py and is reused unchanged.

Run:  uvicorn api:app --reload --port 8000
"""
import os

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import store
import evaluate
import seed
from classifier import classify_both
from workflows import process_request, CONFIDENCE_THRESHOLD

app = FastAPI(title="Incoming Request Processing API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # POC: allow the local dev frontend
    allow_methods=["*"],
    allow_headers=["*"],
)
store.init_db()
seed.seed_if_empty()  # populate the dashboard so a shared link is never empty

# The key is read from the backend .env by default (safer than sending it from
# the browser). Requests may still override it.
ENV_KEY = os.getenv("OPENAI_API_KEY")


class ProcessIn(BaseModel):
    message: str
    source: str = "Manual"
    sender: str = ""
    subject: str = ""
    api_key: str | None = None


class ApproveIn(BaseModel):
    id: int
    decision: str  # "Approved" | "Rejected"


class CompareIn(BaseModel):
    message: str
    api_key: str | None = None


def _key(override: str | None) -> str | None:
    return override or ENV_KEY


@app.get("/api/health")
def health():
    return {"ok": True, "ai_configured": bool(ENV_KEY), "threshold": CONFIDENCE_THRESHOLD}


@app.get("/api/inbox")
def inbox():
    path = os.path.join(os.path.dirname(__file__), "sample_requests.csv")
    return pd.read_csv(path).fillna("").to_dict(orient="records")


@app.post("/api/process-inbox")
def process_inbox():
    """Batch-process every message in the sample inbox and save each case."""
    path = os.path.join(os.path.dirname(__file__), "sample_requests.csv")
    df = pd.read_csv(path).fillna("")
    out = []
    for _, r in df.iterrows():
        res = process_request(str(r["message"]), _key(None),
                              str(r.get("source", "")), str(r.get("sender", "")),
                              str(r.get("subject", "")))
        res["message"] = str(r["message"])
        store.save_case(res)
        out.append({"source": res.get("source"), "sender": res.get("sender"),
                    "type": res["type"], "urgency": res["urgency"],
                    "sentiment": res["sentiment"], "routed_team": res["routed_team"],
                    "approval": res["approval"], "engine": res["engine"]})
    return out


@app.get("/api/accuracy")
def accuracy():
    """Run the labelled evaluation and return accuracy + confusion matrix."""
    return evaluate.evaluate()


@app.post("/api/process")
def process(inp: ProcessIn):
    res = process_request(inp.message, _key(inp.api_key), inp.source, inp.sender, inp.subject)
    res["message"] = inp.message
    res["id"] = store.save_case(res)
    return res


@app.get("/api/cases")
def cases():
    return store.get_cases_df().fillna("").to_dict(orient="records")


@app.get("/api/pending")
def pending():
    df = store.get_pending_df()
    return df.fillna("").to_dict(orient="records") if not df.empty else []


@app.post("/api/approve")
def approve(inp: ApproveIn):
    store.update_approval(inp.id, inp.decision)
    return {"ok": True}


@app.get("/api/kpis")
def kpis():
    return store.get_kpis()


@app.get("/api/stats")
def stats():
    return store.get_stats()


@app.get("/api/priority-queue")
def priority_queue():
    df = store.get_priority_queue()
    return df.fillna("").to_dict(orient="records") if not df.empty else []


@app.post("/api/compare")
def compare(inp: CompareIn):
    return classify_both(inp.message, _key(inp.api_key))


@app.post("/api/clear")
def clear():
    store.clear_cases()
    return {"ok": True}


# --- serve the built React frontend (single-service production deploy) ------
# In local dev the Vite server handles the UI; in production (Railway) FastAPI
# serves the built files so the whole app runs from ONE URL. Mounted last so it
# never shadows the /api/* routes above.
from fastapi.staticfiles import StaticFiles  # noqa: E402

_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(_DIST):
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="frontend")
