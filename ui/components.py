import streamlit as st
from pathlib import Path
from config import SEVERITY_COLORS, SEVERITY_EMOJI


def inject_theme():
    css_path = Path(__file__).parent / "theme.css"
    css = css_path.read_text()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def severity_badge(severity: str) -> str:
    color, _ = SEVERITY_COLORS.get(severity, ("#8b949e", "low"))
    return (
        f'<span style="background:{color}22; color:{color}; '
        f'padding:3px 10px; border-radius:12px; font-size:12px; '
        f'font-weight:600; letter-spacing:0.03em; '
        f'border:1px solid {color}44;">{severity}</span>'
    )


def log_card(entry: dict, index: int = 0):
    severity = entry.get("severity", "LOW")
    _, css_class = SEVERITY_COLORS.get(severity, ("#8b949e", "low"))
    color, _ = SEVERITY_COLORS.get(severity, ("#8b949e", "low"))
    category = entry.get("category", "unknown")
    st.markdown(
        f"""<div class="severity-{css_class}">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <div style="display:flex; align-items:center; gap:8px;">
                    {severity_badge(severity)}
                    <span style="color:#b0bec8; font-size:13px; font-weight:500;">{category}</span>
                </div>
                <span style="color:#6e7f90; font-size:12px; font-family:'Fira Code',monospace;">{entry.get('timestamp', '')}</span>
            </div>
            <div style="color:#e6edf3; font-size:14px; margin-bottom:8px; line-height:1.6;">
                {entry.get('summary', '')}
            </div>
            <code style="font-family:'Fira Code',monospace;">{entry.get('raw_line', '')}</code>
        </div>""",
        unsafe_allow_html=True,
    )


def remediation_card(rem: dict):
    confidence = rem.get("confidence", 0)
    pct = int(confidence * 100)
    steps_html = "".join(f"<li>{step}</li>" for step in rem.get("fix_steps", []))
    st.markdown(
        f"""<div class="remediation-card">
            <h4 style="color:#c9d1d9; margin:0 0 8px 0;">{rem.get('issue_summary', '')}</h4>
            <p style="color:#8b949e; font-size:13px;"><strong>Root cause:</strong> {rem.get('root_cause', '')}</p>
            <p style="color:#8b949e; font-size:13px;"><strong>Rationale:</strong> {rem.get('rationale', '')}</p>
            <p style="color:#c9d1d9; font-size:13px;"><strong>Fix steps:</strong></p>
            <ol style="color:#c9d1d9; font-size:13px;">{steps_html}</ol>
            <div style="display:flex; align-items:center; gap:8px; margin-top:8px;">
                <span style="color:#8b949e; font-size:12px;">Confidence: {pct}%</span>
                <div class="confidence-bar" style="flex:1;">
                    <div class="confidence-fill" style="width:{pct}%;"></div>
                </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


def jira_card(ticket: dict):
    labels_html = "".join(
        f'<span class="jira-label">{label}</span>' for label in ticket.get("labels", [])
    )
    st.markdown(
        f"""<div class="jira-card">
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <h4 style="color:#c9d1d9; margin:0;">{ticket.get('title', '')}</h4>
                <span style="color:#58a6ff; font-size:12px;">{ticket.get('priority', '')}</span>
            </div>
            <p style="color:#8b949e; font-size:13px;">{ticket.get('description', '')}</p>
            <div style="margin-top:8px;">
                <span style="color:#8b949e; font-size:11px;">Assignee: {ticket.get('assignee', 'Unassigned')}</span>
            </div>
            <div style="margin-top:6px;">{labels_html}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def trace_bar(trace_entries: list[dict]):
    if not trace_entries:
        st.info("No agent trace data yet.")
        return

    nodes_html = ""
    for i, entry in enumerate(trace_entries):
        status = entry.get("status", "pending")
        css_class = f"trace-node-{status}" if status in ("completed", "running", "skipped") else "trace-node-skipped"
        duration = entry.get("end_time", 0) - entry.get("start_time", 0)
        icon = {"completed": "\u2705", "running": "\u2699\ufe0f", "skipped": "\u26aa", "failed": "\u274c"}.get(status, "\u26aa")

        nodes_html += f'<div class="trace-node {css_class}">{icon} {entry["agent_name"]}<br><span style="font-size:10px; opacity:0.7;">{duration:.1f}s</span></div>'
        if i < len(trace_entries) - 1:
            nodes_html += '<div class="trace-arrow">\u27a1</div>'

    st.markdown(f'<div class="trace-bar">{nodes_html}</div>', unsafe_allow_html=True)


def severity_summary(entries: list[dict]):
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for entry in entries:
        sev = entry.get("severity", "LOW")
        if sev in counts:
            counts[sev] += 1

    for sev, count in counts.items():
        emoji = SEVERITY_EMOJI[sev]
        color, _ = SEVERITY_COLORS[sev]
        st.markdown(
            f'<div style="display:flex; justify-content:space-between; padding:4px 0;">'
            f'<span>{emoji} <span style="color:#c9d1d9;">{sev.title()}</span></span>'
            f'<span style="color:{color}; font-weight:bold; font-size:16px;">{count}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


def category_tags(entries: list[dict]):
    categories = {}
    for entry in entries:
        cat = entry.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    tags_html = ""
    for cat, count in categories.items():
        tags_html += f'<span class="category-tag" style="background:#30363d; color:#c9d1d9;">{cat} ({count})</span>'

    st.markdown(f'<div>{tags_html}</div>', unsafe_allow_html=True)
