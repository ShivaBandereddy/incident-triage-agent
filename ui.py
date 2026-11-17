# ui.py  (Streamlit front end for the Incident Triage Agent)
# Run: PYTHONPATH=. streamlit run ui.py
# Uses build_graph() only, so the measured pipeline is untouched.
import json
import uuid
from pathlib import Path

import streamlit as st
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.graph import build_graph

st.set_page_config(page_title="Incident Triage Agent", page_icon="🛰️", layout="wide")

CSS = """
<style>
.block-container {padding-top: 2rem; max-width: 1200px;}
.hero h1 {font-size: 2.1rem; margin-bottom: 0;}
.hero p {color: #8b949e; margin-top: .2rem;}
.stages {display: flex; gap: 8px; flex-wrap: wrap; margin: 1rem 0 1.2rem 0;}
.stage {padding: 6px 14px; border-radius: 999px; font-size: .85rem;
        border: 1px solid #30363d; color: #8b949e;}
.stage.done {border-color: #238636; color: #3fb950;}
.stage.now {border-color: #d29922; color: #d29922; font-weight: 600;}
.card {border: 1px solid #30363d; border-radius: 12px; padding: 14px 18px;
       margin-bottom: 12px; background: rgba(139,148,158,.06);}
.card h4 {margin: 0 0 6px 0;}
.bar {height: 8px; border-radius: 6px; background: #30363d; overflow: hidden;}
.bar > div {height: 100%;}
.tag {display: inline-block; padding: 2px 10px; border-radius: 6px; font-size: .78rem;
      background: rgba(88,166,255,.15); color: #58a6ff; margin-right: 6px;}
.warn {border-left: 4px solid #d29922; padding: 10px 14px; border-radius: 6px;
       background: rgba(210,153,34,.12); margin-bottom: 12px;}
.small {color: #8b949e; font-size: .85rem;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

STAGES = ["Intake", "Analyze logs", "Search runbooks", "Hypothesize", "Human review", "Report"]


@st.cache_resource
def get_graph():
    # in-memory checkpointer: pending approvals are lost when the app restarts
    return build_graph(checkpointer=MemorySaver())


@st.cache_data
def load_dev():
    p = Path("data/incidents_dev.json")
    return json.loads(p.read_text()) if p.exists() else []


def init_state():
    for k, v in {"tid": None, "out": None, "inc": None, "error": None}.items():
        st.session_state.setdefault(k, v)


def cfg():
    return {"configurable": {"thread_id": st.session_state.tid}}


def start(alert, logs, inc=None):
    st.session_state.tid = str(uuid.uuid4())
    st.session_state.inc = inc
    st.session_state.error = None
    try:
        with st.spinner("Agent is reading logs, searching runbooks, ranking causes..."):
            st.session_state.out = get_graph().invoke(
                {"alert_text": alert, "log_snippet": logs}, cfg())
    except Exception as e:  # quota errors etc.
        st.session_state.out = None
        st.session_state.error = f"{type(e).__name__}: {e}"


def resume(approved, feedback=""):
    try:
        with st.spinner("Working..."):
            st.session_state.out = get_graph().invoke(
                Command(resume={"approved": approved, "feedback": feedback}), cfg())
    except Exception as e:
        st.session_state.error = f"{type(e).__name__}: {e}"


def conf_color(c):
    return "#3fb950" if c >= 0.7 else "#d29922" if c >= 0.5 else "#f85149"


def stages_html(current):
    parts = []
    for i, s in enumerate(STAGES):
        cls = "done" if i < current else "now" if i == current else ""
        parts.append(f'<span class="stage {cls}">{i + 1}. {s}</span>')
    return '<div class="stages">' + "".join(parts) + "</div>"


def show_hypotheses(hyps):
    for i, h in enumerate(hyps, 1):
        c = float(h.get("confidence", 0))
        st.markdown(
            f'<div class="card"><h4>#{i} {h["cause"]}</h4>'
            f'<span class="tag">confidence {c:.0%}</span>'
            f'<span class="tag">runbook: {h.get("runbook") or "none"}</span>'
            f'<div class="bar" style="margin-top:10px"><div style="width:{c * 100:.0f}%;'
            f'background:{conf_color(c)}"></div></div></div>',
            unsafe_allow_html=True)
        for e in h.get("evidence", []):
            st.code(e, language=None)


init_state()

st.markdown('<div class="hero"><h1>🛰️ Incident Triage Agent</h1>'
            '<p>Alert + logs in. Ranked root causes with evidence and runbook citations out. '
            'A human reviews and approves. The agent never runs commands.</p></div>',
            unsafe_allow_html=True)

# ---------------- sidebar: input ----------------
with st.sidebar:
    st.header("Input")
    mode = st.radio("Source", ["Dev example", "Upload log file", "Paste"], label_visibility="collapsed")
    alert, logs, inc = "", "", None

    if mode == "Dev example":
        dev = load_dev()
        if not dev:
            st.warning("data/incidents_dev.json not found.")
        else:
            labels = [f'{i["id"]} ({i["difficulty"]})' for i in dev]
            pick = st.selectbox("Incident", labels)
            inc = dev[labels.index(pick)]
            alert, logs = inc["alert_text"], inc["log_snippet"]
            st.text_area("Alert", alert, height=80, disabled=True)
            st.caption(f"{len(logs.splitlines())} log lines")
    elif mode == "Upload log file":
        alert = st.text_input("Alert text", "ALERT: host reporting degraded health")
        up = st.file_uploader("Log file", type=["log", "txt"])
        if up:
            logs = up.read().decode("utf-8", errors="replace")
            st.caption(f"{len(logs.splitlines())} log lines loaded")
    else:
        alert = st.text_input("Alert text")
        logs = st.text_area("Logs", height=240)

    go = st.button("Run triage", type="primary", use_container_width=True,
                   disabled=not (alert and logs))
    st.divider()
    st.caption("Synthetic demo data only. Do not paste real customer or company logs "
               "(free-tier Gemini may use prompts to improve Google products).")

if go:
    start(alert, logs, inc)

# ---------------- main: results ----------------
out = st.session_state.out

if st.session_state.error:
    st.error(st.session_state.error)
    st.info("If this is a 429 / RESOURCE_EXHAUSTED error, the free daily quota is used up. Try later.")

if not out:
    st.markdown(stages_html(-1), unsafe_allow_html=True)
    st.info("Pick an incident (or upload logs) in the sidebar and click **Run triage**.")
    st.stop()

pending = out["__interrupt__"][0].value if "__interrupt__" in out else None
finished = bool(out.get("report"))
st.markdown(stages_html(4 if pending else 5 if finished else 3), unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
c1.metric("Service", out.get("service", "-"))
c2.metric("Severity", out.get("severity", "-"))
c3.metric("Runbook match", "none" if out.get("retrieval_failed") else f'{len(out.get("runbook_matches", []))} found')

if out.get("security_flags"):
    st.markdown('<div class="warn"><b>Security flags</b><br>' + "<br>".join(out["security_flags"]) + "</div>",
                unsafe_allow_html=True)

tab1, tab2 = st.tabs(["Triage result", "How the agent got here"])

with tab2:
    st.subheader("Log findings")
    for f in out.get("log_findings", []) or ["(nothing abnormal found)"]:
        st.markdown(f"- {f}")
    with st.expander("Filtered logs sent to the model"):
        st.code(out.get("filtered_logs", ""), language=None)
    with st.expander("Retrieved runbooks"):
        for m in out.get("runbook_matches", []):
            st.markdown(f'**{m["runbook"]}** (distance {m.get("distance")})')
    inc = st.session_state.inc
    if inc:
        with st.expander("Ground truth (dev only, for demo)"):
            st.write(f'True cause: **{inc["true_root_cause"]}**, runbook: {inc["correct_runbook"]}')

with tab1:
    hyps = (pending or {}).get("hypotheses") or out.get("hypotheses", [])
    if pending and pending.get("escalated"):
        st.markdown('<div class="warn"><b>Low confidence or unknown cause.</b> '
                    'Agent recommends human investigation.</div>', unsafe_allow_html=True)
    st.subheader("Root cause hypotheses")
    show_hypotheses(hyps)
    st.subheader("Proposed steps (suggestions only, never auto-run)")
    st.markdown((pending or {}).get("proposed_fix") or out.get("proposed_fix", "-"))

    if pending:
        st.divider()
        st.subheader("Your review")
        with st.form("review"):
            fb = st.text_input("Feedback (needed only if you reject)")
            a, b = st.columns(2)
            ok = a.form_submit_button("Approve", type="primary", use_container_width=True)
            no = b.form_submit_button("Reject and retry", use_container_width=True)
        if ok:
            resume(True)
            st.rerun()
        if no:
            resume(False, fb)
            st.rerun()
    elif finished:
        st.divider()
        st.subheader("Report")
        st.markdown(out["report"])
        st.download_button("Download report (.md)", out["report"],
                           file_name="incident_report.md", mime="text/markdown")
