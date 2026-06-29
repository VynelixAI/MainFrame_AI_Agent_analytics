"""Streamlit Dashboard for Mainframe AI Operations Copilot."""

from __future__ import annotations

import json
from datetime import datetime
from io import BytesIO

import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

API_BASE = "http://localhost:8000/api/v1"

st.set_page_config(
    page_title="Mainframe AI Copilot",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🖥️ Mainframe AI Operations Copilot")
st.caption("Autonomous incident investigation powered by LangGraph multi-agent AI")

with st.sidebar:
    st.header("Configuration")
    api_url = st.text_input("API URL", value=API_BASE)
    job_name = st.text_input("Job Name", value="CLMDAY01")
    application = st.text_input("Application", value="Claims Processing")
    description = st.text_area("Incident Description", height=100)

st.header("Upload Artifacts")
col1, col2, col3 = st.columns(3)
with col1:
    jes_file = st.file_uploader("JES Log", type=["log", "txt"])
    abend_file = st.file_uploader("ABEND Log", type=["log", "txt"])
    jcl_file = st.file_uploader("JCL", type=["jcl", "txt"])
with col2:
    cobol_file = st.file_uploader("COBOL Source", type=["cbl", "txt"])
    db2_file = st.file_uploader("DB2 Log", type=["log", "txt"])
    mq_file = st.file_uploader("MQ Log", type=["log", "txt"])
with col3:
    cics_file = st.file_uploader("CICS Log", type=["log", "txt"])
    scheduler_file = st.file_uploader("Scheduler Log", type=["log", "txt"])
    sysout_file = st.file_uploader("SYSOUT", type=["log", "txt"])


def read_upload(f) -> str:
    if f is None:
        return ""
    return f.read().decode("utf-8", errors="replace")


if st.button("🔍 Run AI Investigation", type="primary", use_container_width=True):
    payload = {
        "job_name": job_name,
        "application": application,
        "description": description,
        "jes_log": read_upload(jes_file),
        "sysout": read_upload(sysout_file),
        "abend_log": read_upload(abend_file),
        "jcl": read_upload(jcl_file),
        "cobol_source": read_upload(cobol_file),
        "db2_log": read_upload(db2_file),
        "mq_log": read_upload(mq_file),
        "cics_log": read_upload(cics_file),
        "scheduler_log": read_upload(scheduler_file),
    }

    with st.spinner("Running multi-agent investigation..."):
        try:
            response = httpx.post(f"{api_url}/investigate", json=payload, timeout=300.0)
            response.raise_for_status()
            result = response.json()
            st.session_state["investigation_result"] = result
            st.success(f"Investigation completed: {result.get('incident_id', 'N/A')}")
        except httpx.ConnectError:
            st.warning("API unavailable - running local investigation...")
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from graph.workflow import get_investigation_graph
            from models.incident import InvestigationRequest
            graph = get_investigation_graph()
            req = InvestigationRequest(**payload)
            local_result = graph.investigate(req)
            st.session_state["investigation_result"] = {
                "incident_id": local_result.get("incident_id"),
                "incident_report": local_result.get("incident_report", {}),
                "runbook": local_result.get("runbook", {}),
                "guardrail": local_result.get("guardrail_result", {}),
                "agent_results": local_result.get("agent_results", []),
            }
            st.success("Local investigation completed")
        except Exception as exc:
            st.error(f"Investigation failed: {exc}")

if "investigation_result" in st.session_state:
    result = st.session_state["investigation_result"]
    report_data = result.get("incident_report", {})
    analysis = report_data.get("analysis", report_data) if isinstance(report_data, dict) else {}

    st.header("Investigation Results")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Severity", analysis.get("severity", "N/A"))
    m2.metric("Confidence", f"{analysis.get('confidence_score', 0):.0%}")
    m3.metric("Affected Job", analysis.get("affected_job", "N/A"))
    m4.metric("Application", analysis.get("application", "N/A"))

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Root Cause", "Timeline", "Agents", "Runbook", "Report"]
    )

    with tab1:
        st.subheader("Root Cause Analysis")
        st.write(analysis.get("root_cause", "No root cause determined"))
        st.subheader("Business Impact")
        st.write(analysis.get("business_impact", ""))
        st.subheader("Recovery Actions")
        for action in analysis.get("recovery_actions", []):
            approval = "⚠️ Requires Approval" if action.get("requires_approval") else "✅"
            st.write(f"{approval} **{action.get('priority', '')}.** {action.get('action', '')}")

    with tab2:
        timeline = analysis.get("timeline", [])
        if timeline:
            df = pd.DataFrame(timeline)
            fig = px.timeline(
                df, x_start="timestamp", x_end="timestamp",
                y="source", color="event", title="Incident Timeline",
            )
            st.plotly_chart(fig, use_container_width=True)
        for event in timeline:
            st.write(f"**{event.get('source')}** - {event.get('event')}: {event.get('details')}")

    with tab3:
        agents = result.get("agent_results", [])
        if agents:
            agent_df = pd.DataFrame([
                {
                    "Agent": a.get("agent_name", ""),
                    "Success": a.get("success", False),
                    "Confidence": a.get("confidence", 0),
                    "Duration (ms)": a.get("duration_ms", 0),
                }
                for a in agents
            ])
            fig = go.Figure(data=[
                go.Bar(x=agent_df["Agent"], y=agent_df["Confidence"], name="Confidence"),
            ])
            fig.update_layout(title="Agent Confidence Scores", yaxis_range=[0, 1])
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(agent_df, use_container_width=True)

        guardrail = result.get("guardrail", {})
        guard_analysis = guardrail.get("analysis", guardrail) if isinstance(guardrail, dict) else {}
        if guard_analysis:
            st.subheader("Guardrail Status")
            st.write(f"Passed: {guard_analysis.get('passed', 'N/A')}")
            for warning in guard_analysis.get("warnings", []):
                st.warning(warning)

    with tab4:
        runbook = result.get("runbook", {})
        rb_analysis = runbook.get("analysis", runbook) if isinstance(runbook, dict) else {}
        st.subheader(rb_analysis.get("title", "Runbook"))
        st.write(f"Runbook ID: {rb_analysis.get('runbook_id', 'N/A')}")
        for step in rb_analysis.get("steps", []):
            st.write(f"- {step}")
        st.subheader("Commands")
        for cmd in rb_analysis.get("commands", []):
            st.code(cmd)

    with tab5:
        st.subheader("Executive Summary")
        st.write(analysis.get("executive_summary", ""))
        st.subheader("ServiceNow Summary")
        snow = analysis.get("servicenow_summary", "")
        if snow:
            try:
                st.json(json.loads(snow))
            except json.JSONDecodeError:
                st.write(snow)
        st.subheader("Preventive Measures")
        for measure in analysis.get("preventive_measures", []):
            st.write(f"- {measure}")

        report_json = json.dumps(analysis, indent=2, default=str)
        st.download_button(
            "📥 Download JSON Report",
            data=report_json,
            file_name=f"incident_{result.get('incident_id', 'report')}.json",
            mime="application/json",
        )

st.divider()
st.caption(f"Mainframe AI Copilot Dashboard | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
