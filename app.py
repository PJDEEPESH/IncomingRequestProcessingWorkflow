"""
Incoming Request Processing Workflow - Streamlit UI.

Tabs:
  Inbox        - simulated multi-source inbox (Email / Web Form / Shared Inbox / Chat)
  Process      - paste one message, watch it classify + reason + branch (live)
  Approvals    - human-in-the-loop queue: Approve / Reject held cases
  Case Log     - the SQLite audit trail
  Dashboard    - KPIs + volumes by type / urgency / sentiment + priority queue
  AI vs Rules  - proves the AI beats naive keyword matching
  Architecture - the live LangGraph flow diagram (for the deck)

Run:  streamlit run app.py
"""
import os
import time

import pandas as pd
import streamlit as st

from workflows import process_request, GRAPH_DOT, CONFIDENCE_THRESHOLD
from classifier import classify_both
import store

st.set_page_config(page_title="Request Processing Workflow", page_icon="📨", layout="wide")
store.init_db()

st.markdown("""
<style>
.badge {display:inline-block; padding:4px 12px; border-radius:14px; color:white;
        font-weight:600; font-size:0.85rem; margin-right:6px;}
.crit {background:#d64545;} .high {background:#e8833a;}
.med  {background:#3a7de8;} .low {background:#2e9e5b;}
.typebadge {background:#4b3fa7;} .sentbadge {background:#5a5a6e;}
.stepbox {padding:6px 10px; border-left:3px solid #2e9e5b; background:rgba(46,158,91,0.08);
          margin-bottom:6px; border-radius:4px;}
.notebox {padding:8px 12px; border-left:3px solid #7c6bd8; background:rgba(124,107,216,0.10);
          border-radius:4px; margin-bottom:8px;}
</style>
""", unsafe_allow_html=True)

URGENCY_CLASS = {"Critical": "crit", "High": "high", "Medium": "med", "Low": "low"}
SENTIMENT_EMOJI = {"Angry": "😡", "Frustrated": "😠", "Neutral": "😐", "Positive": "🙂"}
SOURCE_ICON = {"Email": "📧", "Web Form": "📝", "Shared Inbox": "📥", "Chat": "💬", "Manual": "⌨️"}

# --- sidebar ---------------------------------------------------------------
st.sidebar.title("⚙️ Settings")
default_key = os.getenv("OPENAI_API_KEY", "")
api_key = st.sidebar.text_input("OpenAI API key", value=default_key, type="password",
                                help="platform.openai.com/api-keys. Leave blank to use the fallback engine.")
if api_key:
    st.sidebar.success("AI engine active (OpenAI)")
else:
    st.sidebar.warning("No key → rule-based fallback")
st.sidebar.caption(f"Human-review threshold: confidence < {CONFIDENCE_THRESHOLD:.0%}")
if st.sidebar.button("🗑️ Clear case log"):
    store.clear_cases()
    st.sidebar.info("Case log cleared.")

st.title("📨 Incoming Request Processing Workflow")
st.caption("AI triage + branching remediation for a broadband/telecom support inbox — POC for Firstsource")

tabs = st.tabs(["📥 Inbox", "🔧 Process", "✅ Approvals", "📋 Case Log",
                "📊 Dashboard", "⚖️ AI vs Rules", "🗺️ Architecture"])
tab_inbox, tab_process, tab_appr, tab_log, tab_dash, tab_cmp, tab_arch = tabs


def sentiment_txt(res):
    emo = SENTIMENT_EMOJI.get(res.get("sentiment", "Neutral"), "😐")
    return f'{emo} {res.get("sentiment","")} {res.get("sentiment_score",0):.0%}'


def render_result(res, animate=False):
    uclass = URGENCY_CLASS.get(res.get("urgency", "Low"), "low")
    st.markdown(
        f'<span class="badge typebadge">{res.get("type","?")}</span>'
        f'<span class="badge {uclass}">{res.get("urgency","?")} urgency</span>'
        f'<span class="badge sentbadge">{sentiment_txt(res)}</span>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Confidence", f"{res.get('confidence',0):.0%}")
    c2.metric("Engine", res.get("engine", "-"))
    c3.metric("Routed to", res.get("routed_team", "-"))

    # the "thinking" step
    if animate:
        with st.spinner("🧠 Reasoning about the request..."):
            time.sleep(0.7)
    st.markdown("**🧠 AI reasoning / triage plan:**")
    st.markdown(f'<div class="notebox">{res.get("triage_note") or res.get("reasoning","")}</div>',
                unsafe_allow_html=True)

    st.markdown("**Remediation steps executed:**")
    steps = res.get("steps", [])
    if animate:
        ph = st.empty()
        html = ""
        for s in steps:
            html += f'<div class="stepbox">✅ <b>{s["name"]}</b> — {s["detail"]}</div>'
            ph.markdown(html, unsafe_allow_html=True)
            time.sleep(0.4)
    else:
        for s in steps:
            st.markdown(f'<div class="stepbox">✅ <b>{s["name"]}</b> — {s["detail"]}</div>',
                        unsafe_allow_html=True)

    st.markdown("**Generated reply to customer:**")
    st.info(res.get("reply", ""))

    d1, d2, d3 = st.columns(3)
    d1.markdown(f"**Status**\n\n{res.get('status','-')}")
    d2.markdown(f"**Follow-up**\n\n{res.get('follow_up','-')}")
    d3.markdown(f"**Flags**\n\n{', '.join(res.get('flags', [])) or '-'}")
    if res.get("approval") == "Pending":
        st.warning("⏳ This case needs **human approval** — see the Approvals tab.")


# --- Tab: Inbox ------------------------------------------------------------
with tab_inbox:
    st.subheader("Simulated inbox — requests arriving from multiple sources")
    st.caption("Just like the brief describes: email, web forms, a shared inbox, and live chat.")
    path = os.path.join(os.path.dirname(__file__), "sample_requests.csv")
    inbox = pd.read_csv(path)

    if st.button("⚡ Process entire inbox"):
        rows = []
        prog = st.progress(0.0)
        for i, r in inbox.iterrows():
            res = process_request(str(r["message"]), api_key or None,
                                  source=r.get("source", "Manual"),
                                  sender=r.get("sender", ""), subject=r.get("subject", ""))
            res["message"] = str(r["message"])
            store.save_case(res)
            rows.append({"source": r.get("source"), "sender": r.get("sender"),
                         "type": res["type"], "urgency": res["urgency"],
                         "sentiment": res["sentiment"], "routed_team": res["routed_team"],
                         "approval": res["approval"]})
            prog.progress((i + 1) / len(inbox))
        st.success(f"Processed all {len(rows)} inbox items (saved to the case log).")
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

    st.divider()
    for i, r in inbox.iterrows():
        icon = SOURCE_ICON.get(r.get("source", "Manual"), "⌨️")
        with st.expander(f"{icon} **{r.get('source','')}** · {r.get('sender','')} — {r.get('subject','')}"):
            st.write(r["message"])
            if st.button("▶️ Process this request", key=f"inbox_{i}"):
                with st.spinner("Running workflow..."):
                    res = process_request(str(r["message"]), api_key or None,
                                          source=r.get("source", "Manual"),
                                          sender=r.get("sender", ""), subject=r.get("subject", ""))
                    res["message"] = str(r["message"])
                    store.save_case(res)
                render_result(res, animate=True)


# --- Tab: Process single ---------------------------------------------------
with tab_process:
    st.subheader("Process a single incoming request")
    examples = {
        "— pick an example —": "",
        "Complaint (billing)": "I've been charged twice for my broadband this month and no one is helping me.",
        "Enquiry (hours)": "What are your customer support opening hours on weekends?",
        "Service request (upgrade)": "I'd like to upgrade my current plan to the 1 Gbps fibre package please.",
        "Escalation (angry)": "This is the THIRD time my internet has gone down this week. I want a manager NOW or I'm cancelling.",
        "Sarcasm test": "Oh great, no internet AGAIN. Wonderful service as always. Fix it.",
        "Low-confidence (vague)": "hmm not sure honestly, just wanted to check something about my account i think",
    }
    pick = st.selectbox("Quick examples", list(examples.keys()))
    message = st.text_area("Customer message", value=examples[pick], height=120,
                           placeholder="Paste or type an incoming customer message...")
    if st.button("▶️ Process request", type="primary"):
        if not message.strip():
            st.error("Please enter a message first.")
        else:
            res = process_request(message, api_key or None, source="Manual")
            res["message"] = message
            store.save_case(res)
            render_result(res, animate=True)


# --- Tab: Approvals (human-in-the-loop) ------------------------------------
with tab_appr:
    st.subheader("Human approval queue")
    st.caption("Escalations and low-confidence cases are held here for a human decision — "
               "this is the human-in-the-loop step.")
    pending = store.get_pending_df()
    if pending.empty:
        st.info("✅ No cases waiting for approval right now.")
    else:
        st.write(f"**{len(pending)} case(s)** awaiting a decision (most urgent first):")
        for _, row in pending.iterrows():
            uclass = URGENCY_CLASS.get(row["urgency"], "low")
            with st.container(border=True):
                st.markdown(
                    f'<span class="badge typebadge">{row["type"]}</span>'
                    f'<span class="badge {uclass}">{row["urgency"]}</span>'
                    f'&nbsp; <b>#{row["id"]}</b> · {SOURCE_ICON.get(row["source"],"")} {row["source"]} · {row["sender"]}',
                    unsafe_allow_html=True)
                st.write(f"_{row['message']}_")
                st.caption(f"🧠 {row['triage_note']}")
                a, b, _ = st.columns([1, 1, 4])
                if a.button("✅ Approve", key=f"appr_{row['id']}"):
                    store.update_approval(int(row["id"]), "Approved")
                    st.rerun()
                if b.button("❌ Reject", key=f"rej_{row['id']}"):
                    store.update_approval(int(row["id"]), "Rejected")
                    st.rerun()


# --- Tab: Case Log ---------------------------------------------------------
with tab_log:
    st.subheader("Case log (audit trail)")
    df = store.get_cases_df()
    if df.empty:
        st.info("No cases yet. Process a request to populate the log.")
    else:
        show = df[["id", "created_at", "source", "sender", "type", "urgency",
                   "sentiment", "confidence", "engine", "routed_team", "status", "approval"]]
        st.dataframe(show, use_container_width=True)
        st.download_button("⬇️ Download log as CSV", df.to_csv(index=False),
                           "case_log.csv", "text/csv")


# --- Tab: Dashboard --------------------------------------------------------
with tab_dash:
    st.subheader("Operations dashboard")
    kpis = store.get_kpis()
    if kpis["total"] == 0:
        st.info("No data yet. Process some requests first (try the Inbox tab).")
    else:
        m = st.columns(5)
        m[0].metric("Total requests", kpis["total"])
        m[1].metric("Automation rate", f"{kpis['automation_rate']}%",
                    help="% handled fully automatically (no human needed)")
        m[2].metric("Avg confidence", f"{kpis['avg_confidence']}%")
        m[3].metric("Awaiting approval", kpis["pending"])
        m[4].metric("Critical", kpis["critical"])

        stats = store.get_stats()
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**By type**")
            st.bar_chart(pd.Series(stats["by_type"]))
        with c2:
            st.markdown("**By urgency**")
            st.bar_chart(pd.Series(stats["by_urgency"]))
        with c3:
            st.markdown("**By sentiment**")
            st.bar_chart(pd.Series(stats["by_sentiment"]))

        st.markdown("**🚦 Priority queue (open cases, most urgent first)**")
        pq = store.get_priority_queue()
        if pq.empty:
            st.caption("No open cases — everything is resolved or approved.")
        else:
            st.dataframe(pq[["id", "urgency", "type", "sentiment", "source",
                             "routed_team", "status"]], use_container_width=True)


# --- Tab: AI vs Rules ------------------------------------------------------
with tab_cmp:
    st.subheader("AI vs rule-based — why the AI matters")
    st.caption("Run both engines on the same message. Watch the AI catch nuance/sarcasm that keywords miss.")
    demo = st.text_input("Message", value="Oh great, no internet AGAIN. Wonderful service as always.")
    if st.button("🔬 Compare engines"):
        out = classify_both(demo, api_key or None)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🤖 AI (OpenAI)")
            if out["ai"] is None:
                st.warning("No API key set — add one in the sidebar to see the AI result.")
            else:
                ai = out["ai"]
                st.markdown(f"**Type:** {ai['type']}  \n**Urgency:** {ai['urgency']}  \n"
                            f"**Sentiment:** {sentiment_txt(ai)}  \n**Confidence:** {ai['confidence']:.0%}")
                st.caption(ai.get("reasoning", ""))
        with col2:
            st.markdown("#### 📏 Rule-based")
            rb = out["rules"]
            st.markdown(f"**Type:** {rb['type']}  \n**Urgency:** {rb['urgency']}  \n"
                        f"**Sentiment:** {sentiment_txt(rb)}  \n**Confidence:** {rb['confidence']:.0%}")
            st.caption(rb.get("reasoning", ""))
        if out["ai"] and out["ai"]["type"] != out["rules"]["type"]:
            st.success(f"⚡ The engines disagree! AI said **{out['ai']['type']}**, "
                       f"rules said **{out['rules']['type']}**. This is exactly where AI adds value.")


# --- Tab: Architecture -----------------------------------------------------
with tab_arch:
    st.subheader("Solution architecture — LangGraph state machine")
    st.caption("The live branching graph the app runs. Screenshot this for Slide 2 of the deck.")
    st.graphviz_chart(GRAPH_DOT)
    st.markdown("""
**How it works**
1. **Intake** — a request arrives from Email, a Web Form, the Shared Inbox, or Chat.
2. **AI Classify** — type, urgency, **sentiment**, and confidence (rule-based fallback if the API is down).
3. **AI Reason / Triage** — a visible "thinking" node writes the rationale and the plan.
4. **Router (conditional edge)** — low confidence → **Human Review**; otherwise route by type.
5. **Branch remediation** — each branch runs its own multi-step workflow.
6. **Output + Case Log** — a reply, an audit-trail entry, and (for held cases) a **human approval** step.
""")
