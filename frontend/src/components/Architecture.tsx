export default function Architecture() {
  return (
    <div className="card">
      <h3>Solution architecture — LangGraph state machine</h3>
      <div className="hint">The live branching graph the app runs. Screenshot this for Slide 2 of the deck.</div>
      <div className="flow">
        <div className="node intake">Incoming Request<small>Email · Web Form · Shared Inbox · Chat</small></div>
        <div className="arrow">↓</div>
        <div className="node classify">AI Classify<small>type · urgency · sentiment · confidence</small></div>
        <div className="arrow">↓</div>
        <div className="node reason">AI Reason / Triage<small>rationale + plan — the “thinking” step</small></div>
        <div className="arrow">↓</div>
        <div className="node router">Router<small>low confidence → human · otherwise route by type</small></div>
        <div className="arrow">↓</div>
        <div className="branches">
          <div className="branch b-comp">COMPLAINT<small>ack · escalate · log · remind</small></div>
          <div className="branch b-enq">ENQUIRY<small>topic · answer · send · resolve</small></div>
          <div className="branch b-serv">SERVICE<small>extract · route · confirm · SLA</small></div>
          <div className="branch b-esc">ESCALATION<small>flag · ack · supervisor · pause</small></div>
          <div className="branch b-hum">HUMAN REVIEW<small>held → approval queue</small></div>
        </div>
        <div className="arrow">↓</div>
        <div className="node output">Output + Case Log + Human Approval</div>
      </div>
    </div>
  )
}
