import streamlit as st
from ui.components import log_card, remediation_card, jira_card, trace_bar
from config import SEVERITY_COLORS


def _build_solution_index(state: dict) -> dict:
    """Build reverse index: log entry index -> linked remediations, tickets, cookbook."""
    remediations = state.get("remediations", [])
    tickets = state.get("jira_tickets", [])
    cookbook = state.get("cookbook", "")

    # Map log entry index -> list of remediations
    entry_to_remediations = {}
    for rem in remediations:
        for idx in rem.get("linked_log_entries", []):
            entry_to_remediations.setdefault(idx, []).append(rem)

    # Map remediation issue_summary -> JIRA tickets (match by title containing summary)
    rem_to_tickets = {}
    for ticket in tickets:
        title = ticket.get("title", "").lower()
        for rem in remediations:
            summary = rem.get("issue_summary", "").lower()
            if summary and summary in title:
                rem_to_tickets.setdefault(rem["issue_summary"], []).append(ticket)

    return {
        "entry_to_remediations": entry_to_remediations,
        "rem_to_tickets": rem_to_tickets,
        "cookbook": cookbook,
    }


def _render_metrics_row(state: dict):
    """Render summary metric cards at the top of the analysis."""
    entries = state.get("classified_entries", [])
    remediations = state.get("remediations", [])
    traces = state.get("agent_trace", [])

    total_issues = len(entries)
    critical_count = sum(1 for e in entries if e.get("severity") in ("CRITICAL", "HIGH"))
    remediation_count = len(remediations)
    total_time = sum(t.get("end_time", 0) - t.get("start_time", 0) for t in traces)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f"""<div class="metric-card">
                <div class="metric-value" style="color:#e6edf3;">{total_issues}</div>
                <div class="metric-label">Total Issues</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""<div class="metric-card">
                <div class="metric-value" style="color:#ff7b72;">{critical_count}</div>
                <div class="metric-label">Critical / High</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""<div class="metric-card">
                <div class="metric-value" style="color:#58a6ff;">{remediation_count}</div>
                <div class="metric-label">Remediations</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            f"""<div class="metric-card">
                <div class="metric-value" style="color:#56d364;">{total_time:.1f}s</div>
                <div class="metric-label">Pipeline Time</div>
            </div>""",
            unsafe_allow_html=True,
        )


def render_analysis_tab(state: dict):
    entries = state.get("classified_entries", [])
    if not entries:
        st.info("No classified entries yet. Upload logs and run analysis.")
        return

    # Metrics row
    _render_metrics_row(state)
    st.markdown("")

    # Severity filter
    severities = sorted(set(e.get("severity", "LOW") for e in entries),
                        key=lambda s: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(s, 4))
    selected = st.multiselect("Filter by severity", severities, default=severities, key="sev_filter")

    filtered = [e for e in entries if e.get("severity") in selected]

    # Build solution index for cross-linking
    solution_idx = _build_solution_index(state)

    # Two columns: issues list + summary sidebar
    col_main, col_side = st.columns([3, 1])

    with col_main:
        st.markdown(f"**Showing {len(filtered)} of {len(entries)} log entries**")
        for entry in filtered:
            # Find original index in unfiltered list
            orig_index = entries.index(entry)
            log_card(entry, index=orig_index)

            # Inline solution drill-down
            linked_rems = solution_idx["entry_to_remediations"].get(orig_index, [])
            has_solution = bool(linked_rems)

            if has_solution:
                with st.expander(f"\U0001f4a1 View Solution ({len(linked_rems)} remediation{'s' if len(linked_rems) > 1 else ''})", expanded=False):
                    for rem in linked_rems:
                        # Remediation section
                        confidence = rem.get("confidence", 0)
                        pct = int(confidence * 100)
                        steps_html = "".join(f"<li>{step}</li>" for step in rem.get("fix_steps", []))
                        st.markdown(
                            f"""<div style="background:#111820; border:1px solid #2a3442; border-radius:8px; padding:16px; margin-bottom:12px;">
                                <div style="display:flex; align-items:center; gap:8px; margin-bottom:10px;">
                                    <span style="color:#58a6ff; font-size:13px; font-weight:600; text-transform:uppercase; letter-spacing:0.05em;">\U0001f527 Remediation</span>
                                    <span style="color:#6e7f90; font-size:12px;">Confidence: {pct}%</span>
                                </div>
                                <h4 style="color:#f0f6fc; margin:0 0 8px 0; font-size:15px;">{rem.get('issue_summary', '')}</h4>
                                <p style="color:#b0bec8; font-size:13px; margin-bottom:6px;"><strong style="color:#d0d8e0;">Root cause:</strong> {rem.get('root_cause', '')}</p>
                                <p style="color:#d0d8e0; font-size:13px; margin-bottom:4px;"><strong>Fix steps:</strong></p>
                                <ol style="color:#e6edf3; font-size:13px; line-height:1.8; padding-left:20px;">{steps_html}</ol>
                            </div>""",
                            unsafe_allow_html=True,
                        )

                        # Linked JIRA tickets
                        linked_tickets = solution_idx["rem_to_tickets"].get(rem.get("issue_summary", ""), [])
                        if linked_tickets:
                            for ticket in linked_tickets:
                                labels_html = "".join(
                                    f'<span class="jira-label">{label}</span>' for label in ticket.get("labels", [])
                                )
                                st.markdown(
                                    f"""<div style="background:#111820; border:1px solid #2a3442; border-left:4px solid #58a6ff; border-radius:8px; padding:14px; margin-bottom:12px;">
                                        <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                                            <span style="color:#58a6ff; font-size:13px; font-weight:600; text-transform:uppercase; letter-spacing:0.05em;">\U0001f3ab JIRA Ticket</span>
                                            <span style="color:#6e7f90; font-size:12px;">(mocked)</span>
                                        </div>
                                        <div style="display:flex; justify-content:space-between; align-items:center;">
                                            <span style="color:#f0f6fc; font-size:14px; font-weight:500;">{ticket.get('title', '')}</span>
                                            <span style="color:#e8b931; font-size:12px; font-weight:600;">{ticket.get('priority', '')}</span>
                                        </div>
                                        <div style="margin-top:6px;">{labels_html}</div>
                                    </div>""",
                                    unsafe_allow_html=True,
                                )

                    # Cookbook excerpt — search for relevant section
                    cookbook = solution_idx["cookbook"]
                    if cookbook and linked_rems:
                        # Try to find the section matching this remediation
                        first_summary = linked_rems[0].get("issue_summary", "")
                        cookbook_lines = cookbook.split("\n")
                        relevant_lines = []
                        capturing = False
                        for line in cookbook_lines:
                            if first_summary.lower() in line.lower():
                                capturing = True
                            if capturing:
                                relevant_lines.append(line)
                                if len(relevant_lines) > 1 and line.startswith("##"):
                                    relevant_lines.pop()  # don't include next section header
                                    break
                                if len(relevant_lines) >= 10:
                                    break

                        if relevant_lines:
                            cookbook_excerpt = "\n".join(relevant_lines)
                        else:
                            # Fallback: show first few cookbook lines
                            cookbook_excerpt = "\n".join(cookbook_lines[:8])
                            if len(cookbook_lines) > 8:
                                cookbook_excerpt += "\n..."

                        st.markdown(
                            f"""<div style="background:#111820; border:1px solid #2a3442; border-left:4px solid #56d364; border-radius:8px; padding:14px; margin-bottom:8px;">
                                <div style="margin-bottom:8px;">
                                    <span style="color:#56d364; font-size:13px; font-weight:600; text-transform:uppercase; letter-spacing:0.05em;">\U0001f4d6 Cookbook Steps</span>
                                </div>
                            </div>""",
                            unsafe_allow_html=True,
                        )
                        st.markdown(cookbook_excerpt)
            else:
                st.markdown(
                    '<div style="color:#6e7f90; font-size:12px; padding:4px 0 12px 0;">No linked remediation</div>',
                    unsafe_allow_html=True,
                )

    with col_side:
        # Category breakdown
        st.markdown("**Categories**")
        categories = {}
        for entry in entries:
            cat = entry.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            st.markdown(
                f'<div style="display:flex; justify-content:space-between; padding:6px 0; '
                f'border-bottom:1px solid #1c2430;">'
                f'<span style="color:#b0bec8; font-size:13px;">{cat}</span>'
                f'<span style="color:#e6edf3; font-weight:600;">{count}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown("")
        st.markdown("**Quick Navigation**")
        remediations = state.get("remediations", [])
        tickets = state.get("jira_tickets", [])
        slack = state.get("slack_notifications", [])

        nav_items = [
            (f"Remediations ({len(remediations)})", "Switch to the Remediations tab to see fix recommendations"),
            (f"JIRA Tickets ({len(tickets)})", "Switch to JIRA Tickets tab for generated tickets"),
            (f"Slack Alerts ({len(slack)})", "Switch to Slack Log tab for notification status"),
        ]
        for label, help_text in nav_items:
            st.markdown(
                f'<div style="background:#1c2430; padding:8px 12px; border-radius:6px; '
                f'margin-bottom:6px; border:1px solid #2a3442;">'
                f'<span style="color:#58a6ff; font-size:13px; font-weight:500;">{label}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


def render_remediations_tab(state: dict):
    remediations = state.get("remediations", [])
    if not remediations:
        st.info("No remediations generated yet.")
        return

    st.markdown(f"**{len(remediations)} remediations generated**")
    for rem in remediations:
        remediation_card(rem)


def render_cookbook_tab(state: dict):
    cookbook = state.get("cookbook", "")
    if not cookbook:
        st.info("No cookbook generated yet.")
        return

    st.markdown(cookbook)


def render_slack_tab(state: dict):
    notifications = state.get("slack_notifications", [])
    if not notifications:
        st.info("No Slack notifications sent yet.")
        return

    for notif in notifications:
        status_class = "status-sent" if notif["status"] == "sent" else "status-failed"
        status_label = "Sent" if notif["status"] == "sent" else "Failed"
        st.markdown(
            f"""<div style="background:#111820; border:1px solid #2a3442; border-radius:10px; padding:16px; margin-bottom:12px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="color:#e6edf3; font-weight:500; font-size:15px;">{notif['channel']}</span>
                    <span class="status-pill {status_class}">{status_label}</span>
                </div>
                <p style="color:#b0bec8; font-size:14px; margin-top:8px; line-height:1.5;">{notif['text']}</p>
            </div>""",
            unsafe_allow_html=True,
        )


def render_jira_tab(state: dict):
    tickets = state.get("jira_tickets", [])
    if not tickets:
        st.info("No JIRA tickets created.")
        return

    st.markdown(
        '<p style="color:#8b9ab0; font-size:13px; margin-bottom:14px;">'
        'These tickets are mocked \u2014 no real JIRA API calls were made.</p>',
        unsafe_allow_html=True,
    )
    for ticket in tickets:
        jira_card(ticket)


def render_trace_tab(state: dict):
    traces = state.get("agent_trace", [])
    if not traces:
        st.info("No agent trace data yet.")
        return

    # Timeline view
    st.subheader("Execution Timeline")
    trace_bar(traces)

    # Detail view
    st.subheader("Agent Details")
    for trace in traces:
        status_icon = {"completed": "\u2705", "running": "\u2699\ufe0f", "skipped": "\u26aa", "failed": "\u274c"}.get(
            trace["status"], "\u26aa"
        )
        duration = trace.get("end_time", 0) - trace.get("start_time", 0)
        with st.expander(f"{status_icon} {trace['agent_name']} \u2014 {duration:.1f}s"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Status:** {trace['status']}")
                st.markdown(f"**Duration:** {duration:.1f}s")
            with col2:
                st.markdown(f"**Input:** {trace.get('input_summary', 'N/A')}")
                st.markdown(f"**Output:** {trace.get('output_summary', 'N/A')}")
