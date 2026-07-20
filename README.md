# Incoming Request Processing Workflow

**POC for Firstsource** — an AI-powered prototype that receives, classifies, and
processes incoming customer requests for a broadband/telecom support inbox
("BlueStream Broadband"), then executes a distinct, multi-step **remediation
workflow** for each request type.

Built as an **agentic LangGraph state machine**: one AI classifier feeds a
conditional router that branches into type-specific workflows, each running its
own downstream actions and producing a customer reply plus an audit-log entry.

---

## 1. What it does (end to end)

```
Intake (Email · Web Form · Shared Inbox · Chat)
     → AI Classify (type + urgency + sentiment + confidence)
     → AI Reason / Triage (rationale + plan)          ← visible "thinking" node
     → Router:  low confidence? → HUMAN REVIEW
                otherwise route by type ↓
   COMPLAINT · ENQUIRY · SERVICE REQUEST · ESCALATION
     → each runs its multi-step remediation
     → Output (reply + actions) + Case Log (SQLite) + Human Approval (held cases)
```

## 2. Classification logic

The AI (OpenAI) returns **type**, **urgency**, a **confidence** score, a
**sub-topic**, and one-line **reasoning**. It reads tone and sarcasm — e.g.
*"Oh great, no internet AGAIN"* is correctly caught as an angry complaint, not
positive feedback.

If OpenAI is unavailable, a **rule-based fallback** keeps the system running
(graceful degradation). The engine used is recorded on every case.

**Human-in-the-loop override:** if confidence < **60%**, the request is *not*
guessed — it is held and routed to a human triage queue.

## 3. Remediation strategy per branch

| Branch | Urgency | Steps executed | Output |
|--------|---------|----------------|--------|
| **Complaint** | High | Acknowledge → escalate to senior → log w/ priority flag → 2-hr follow-up | Apology draft + escalation + priority case log |
| **General Enquiry** | Low | Classify sub-topic → AI answer → send → log resolved | Auto-response + resolved status |
| **Service Request** | Medium | Extract details → route to department → confirm → start SLA timer | Routing + confirmation + SLA flag |
| **Escalation** | Critical | Flag for human → urgent ack → notify supervisor → pause auto-resolution | Supervisor alert + urgent draft + human-in-the-loop |
| **Human Review** *(override)* | — | Detect low confidence → hold → flag for triage → notify lead | Held case + human triage |

Service requests are further routed to the right department (Billing,
Provisioning, Field/Installation, Network Operations) based on content.

## 4. Tools used

| Purpose | Tool |
|---------|------|
| Language | Python 3.10 |
| AI classification + replies | OpenAI (`gpt-4o-mini`) with rule-based fallback |
| Orchestration | **LangGraph** state machine (conditional branching) |
| Backend API | **FastAPI** (+ uvicorn) |
| Frontend UI | **React + TypeScript + Vite** (charts via Recharts) |
| Backup UI | Streamlit (single-command fallback) |
| Audit trail | SQLite |
| Corporate-network SSL | `truststore` (uses the OS cert store so OpenAI HTTPS works) |

## 5. Setup & run

**First-time setup**

```powershell
# 1) Python backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt          # add --trusted-host pypi.org --trusted-host files.pythonhosted.org if SSL errors

# 2) React frontend
cd frontend
npm install
cd ..

# 3) API key: copy .env.example to .env and paste your OpenAI key
#    (the app also runs without a key, on the rule-based fallback engine)
```

### Option A — full-stack React UI (recommended)

Easiest: **double-click `run.ps1`** (opens both servers + the browser). Or run the two servers manually in two terminals:

```powershell
# terminal 1 - backend
.venv\Scripts\python.exe -m uvicorn api:app --port 8000
# terminal 2 - frontend
cd frontend; npm run dev
```

Open **http://localhost:5173**. Nav: Intake Form · Inbox · Approvals · Dashboard · AI vs Rules · Architecture.

### Option B — Streamlit (single-command backup)

```powershell
.venv\Scripts\python.exe -m streamlit run app.py
```

Opens at `http://localhost:8501`. Same pipeline, simpler UI — handy as a demo-day backup.

> **Corporate-network note:** this machine does SSL inspection, so plain HTTPS to
> OpenAI failed with "unable to get local issuer certificate". `truststore`
> (in requirements) fixes it by trusting the Windows cert store — no need to
> disable verification.

## 6. One end-to-end example per branch

| Input message | → Type / Urgency | → Actions & output |
|---------------|------------------|--------------------|
| "I've been charged twice for my broadband and no one is helping." | Complaint / High | Apology drafted, escalated to Senior Resolution Team, priority-logged, 2-hr reminder set |
| "What are your support hours on weekends?" | Enquiry / Low | AI answer generated, auto-sent, logged resolved |
| "I'd like to upgrade to the 1 Gbps fibre package." | Service Request / Medium | Routed to Provisioning Team, confirmation drafted, 24-hr SLA started |
| "THIRD time down this week — I want a manager NOW or I'm cancelling." | Escalation / Critical | Flagged for human, urgent ack drafted, supervisor notified, auto-resolution paused |
| "hmm not sure, just wanted to check something about my account" | Low confidence (40%) | Held → Human Triage Queue (override) |

## 7. Optional enhancements implemented

- ✅ **Classification accuracy evaluation** — `evaluate.py` grades the classifier against 15 labelled samples (currently **87% type accuracy**); also shown in the app's Accuracy tab with a confusion matrix
- ✅ **Real executed action** — each reply is genuinely written to an `outbox/` file (other steps are simulated and map to Salesforce/Twilio/email in production)
- ✅ **AI-chosen department routing** (Billing / Provisioning / Field / Network Ops), with keyword routing only as a fallback
- ✅ **Degraded-mode banner** — the UI flags when the rule-based fallback is active, so quality drops are never silent
- ✅ **Multi-source simulated inbox** (Email / Web Form / Shared Inbox / Chat)
- ✅ **Visible AI "reasoning" node** (a triage rationale + plan before routing)
- ✅ **Sentiment / emotion detection** (Angry / Frustrated / Neutral / Positive)
- ✅ **Human-in-the-loop approval queue** (Approve / Reject held cases)
- ✅ **AI-vs-rules comparison** (proves the AI catches sarcasm keywords miss)
- ✅ **KPI dashboard** (automation rate, avg confidence, priority queue) + charts by type / urgency / sentiment
- ✅ **Batch processing** (process the whole inbox at once)
- ✅ **Audit trail / case log** (SQLite, downloadable as CSV)
- ✅ **Escalation override** for low-confidence / uncertain cases
- ✅ **Graceful degradation** (rule-based fallback if the AI API is down)

## 8. Files

```
Backend (Python)
  api.py              FastAPI endpoints (wraps the pipeline)
  workflows.py        LangGraph state machine: classify -> reason -> branch
  classifier.py       AI classification + sentiment + department + fallback
  responder.py        AI reply generation + templates
  outbox.py           writes each reply to outbox/ (the real executed action)
  evaluate.py         classification-accuracy eval (accuracy % + confusion matrix)
  store.py            SQLite case log, approvals, KPIs
  llm.py              OpenAI client + truststore SSL + model config
  app.py              Streamlit backup UI
  sample_requests.csv 15 labelled multi-source sample messages
  requirements.txt    Python dependencies
  .env.example        API key template
  run.ps1             one-click launcher (both servers)

Frontend (React + TypeScript, in frontend/)
  src/App.tsx         layout + navigation
  src/api.ts          typed API client
  src/types.ts        shared types
  src/styles.css      design system
  src/components/     IntakeForm, Inbox, ResultCard, Approvals,
                      Dashboard, Compare, Architecture
```
