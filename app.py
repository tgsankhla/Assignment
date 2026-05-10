import os
import warnings
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

# Suppress langgraph deprecation warning
warnings.filterwarnings("ignore", message=".*allowed_objects.*")

# Load .env for local dev; on Streamlit Cloud, secrets come from dashboard
load_dotenv(Path(__file__).resolve().parent / ".env")

# Support both local .env and Streamlit Cloud secrets
def _get_secret(key: str, default: str = "") -> str:
    """Read from env vars first (local .env), fall back to st.secrets (Cloud)."""
    val = os.environ.get(key, "")
    if not val:
        try:
            val = st.secrets.get(key, default)
        except Exception:
            val = default
    return val

# Map OpenRouter credentials to OpenAI env vars before any LLM imports
_key = _get_secret("OPENROUTER_API_KEY")
if not _key:
    st.error("OPENROUTER_API_KEY not found. Add it to .env (local) or Streamlit secrets (Cloud).")
    st.stop()
os.environ["OPENAI_API_KEY"] = _key
os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"
os.environ["LLM_MODEL"] = _get_secret("LLM_MODEL", "openai/gpt-4o")
os.environ["SLACK_BOT_TOKEN"] = _get_secret("SLACK_BOT_TOKEN")
os.environ["SLACK_CHANNEL"] = _get_secret("SLACK_CHANNEL", "#incident-alerts")
os.environ["JIRA_INSTANCE_URL"] = _get_secret("JIRA_INSTANCE_URL")
os.environ["JIRA_USER_EMAIL"] = _get_secret("JIRA_USER_EMAIL")
os.environ["JIRA_API_TOKEN"] = _get_secret("JIRA_API_TOKEN")
os.environ["JIRA_PROJECT_KEY"] = _get_secret("JIRA_PROJECT_KEY")

from orchestrator.graph import build_graph
from orchestrator.state import make_initial_state
from utils.log_parser import read_uploaded_file
from ui.components import inject_theme, severity_summary, category_tags, trace_bar
from ui.tabs import (
    render_analysis_tab,
    render_remediations_tab,
    render_cookbook_tab,
    render_slack_tab,
    render_jira_tab,
    render_trace_tab,
)

st.set_page_config(
    page_title="DevOps Incident Analyzer",
    page_icon="\U0001f6e1\ufe0f",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme()

# Initialize session state
if "analysis_state" not in st.session_state:
    st.session_state.analysis_state = None
if "is_running" not in st.session_state:
    st.session_state.is_running = False

# --- Sidebar ---
with st.sidebar:
    st.markdown("### \U0001f6e1\ufe0f Incident Analyzer")
    st.markdown('<span style="color:#8b949e; font-size:12px;">Multi-Agent DevOps Suite</span>', unsafe_allow_html=True)
    st.divider()

    # Log input section
    st.markdown("**Log Input**")
    uploaded_file = st.file_uploader(
        "Upload log file",
        type=["log", "txt", "json", "csv"],
        help="Supports .log, .txt, .json, .csv formats",
    )

    pasted_logs = st.text_area(
        "Or paste logs here",
        height=150,
        placeholder="Paste log content...",
    )

    analyze_button = st.button(
        "\u25b6\ufe0f Analyze Logs",
        use_container_width=True,
        disabled=st.session_state.is_running,
    )

    # Severity summary (after analysis)
    if st.session_state.analysis_state:
        st.divider()
        st.markdown("**Severity Breakdown**")
        severity_summary(st.session_state.analysis_state.get("classified_entries", []))

        st.divider()
        st.markdown("**Issue Categories**")
        category_tags(st.session_state.analysis_state.get("classified_entries", []))

# --- Main Content ---
st.markdown(
    '<h1 style="color:#58a6ff; margin-bottom:0;">\U0001f6e1\ufe0f DevOps Incident Analyzer</h1>'
    '<p style="color:#8b949e;">Multi-Agent Analysis Suite</p>',
    unsafe_allow_html=True,
)

# Handle analysis
if analyze_button:
    raw_logs = ""
    if uploaded_file is not None:
        raw_logs = read_uploaded_file(uploaded_file)
    elif pasted_logs.strip():
        raw_logs = pasted_logs.strip()

    if not raw_logs:
        st.error("Please upload a file or paste log content.")
    else:
        st.session_state.is_running = True

        # Agent display names and descriptions
        agent_info = {
            "classifier": ("Log Classifier", "Parsing and classifying log entries by severity..."),
            "remediation": ("Remediation Engine", "Analyzing root causes and generating fixes..."),
            "cookbook": ("Cookbook Synthesizer", "Building incident response runbook..."),
            "slack_notifier": ("Slack Notifier", "Sending alerts to Slack channel..."),
            "jira_ticket": ("JIRA Ticket Creator", "Generating JIRA tickets for critical issues..."),
        }

        graph = build_graph()
        initial_state = make_initial_state(raw_logs)
        result = initial_state

        with st.status("Running multi-agent analysis pipeline...", expanded=True) as status:
            st.write(f"Loaded **{len(raw_logs.splitlines())}** lines of logs")

            for event in graph.stream(initial_state):
                for node_name, node_output in event.items():
                    display_name, description = agent_info.get(node_name, (node_name, "Processing..."))

                    # Get timing from trace
                    traces = node_output.get("agent_trace", [])
                    duration = ""
                    if traces:
                        t = traces[-1]
                        d = t.get("end_time", 0) - t.get("start_time", 0)
                        duration = f" ({d:.1f}s)"
                        node_status = t.get("status", "completed")
                    else:
                        node_status = "completed"

                    icon = {"completed": "\u2705", "skipped": "\u26aa", "failed": "\u274c"}.get(node_status, "\u2705")

                    # Show what this agent produced
                    summary_parts = []
                    if "classified_entries" in node_output:
                        summary_parts.append(f"{len(node_output['classified_entries'])} entries classified")
                    if "remediations" in node_output:
                        summary_parts.append(f"{len(node_output['remediations'])} remediations generated")
                    if "cookbook" in node_output and node_output["cookbook"]:
                        summary_parts.append("Runbook generated")
                    if "slack_notifications" in node_output:
                        sent = sum(1 for n in node_output["slack_notifications"] if n["status"] == "sent")
                        failed = sum(1 for n in node_output["slack_notifications"] if n["status"] == "failed")
                        if sent:
                            summary_parts.append(f"{sent} Slack message(s) sent")
                        if failed:
                            summary_parts.append(f"{failed} Slack message(s) failed")
                    if "jira_tickets" in node_output:
                        summary_parts.append(f"{len(node_output['jira_tickets'])} JIRA tickets created")

                    summary_text = " | ".join(summary_parts) if summary_parts else "Done"
                    st.write(f"{icon} **{display_name}**{duration} \u2014 {summary_text}")

                    # Merge into result
                    result = {**result, **node_output}
                    # Accumulate trace entries
                    if "agent_trace" in node_output:
                        existing_trace = result.get("_all_traces", [])
                        existing_trace.extend(node_output["agent_trace"])
                        result["_all_traces"] = existing_trace

            # Finalize trace
            if "_all_traces" in result:
                result["agent_trace"] = result.pop("_all_traces")

            status.update(label="Analysis complete!", state="complete", expanded=False)

        st.session_state.analysis_state = result
        st.session_state.is_running = False
        st.rerun()

# Display results
if st.session_state.analysis_state:
    # Agent trace bar at top
    st.markdown("---")
    st.markdown("**Agent Execution Trace**")
    trace_bar(st.session_state.analysis_state.get("agent_trace", []))
    st.markdown("---")

    # Tabs
    tab_analysis, tab_remediations, tab_cookbook, tab_slack, tab_jira, tab_trace = st.tabs(
        [
            "\U0001f50d Analysis",
            "\U0001f527 Remediations",
            "\U0001f4d6 Cookbook",
            "\U0001f4ac Slack Log",
            "\U0001f3ab JIRA Tickets",
            "\U0001f500 Agent Trace",
        ]
    )

    with tab_analysis:
        render_analysis_tab(st.session_state.analysis_state)
    with tab_remediations:
        render_remediations_tab(st.session_state.analysis_state)
    with tab_cookbook:
        render_cookbook_tab(st.session_state.analysis_state)
    with tab_slack:
        render_slack_tab(st.session_state.analysis_state)
    with tab_jira:
        render_jira_tab(st.session_state.analysis_state)
    with tab_trace:
        render_trace_tab(st.session_state.analysis_state)
else:
    st.markdown(
        """<div style="display:flex; align-items:center; justify-content:center; min-height:400px;">
            <div style="text-align:center;">
                <p style="font-size:48px; margin-bottom:8px;">\U0001f4cb</p>
                <h3 style="color:#c9d1d9;">Upload or paste ops logs to get started</h3>
                <p style="color:#8b949e;">The multi-agent pipeline will classify issues, generate remediations, and push notifications.</p>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )
