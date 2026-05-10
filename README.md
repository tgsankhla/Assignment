# Multi-Agent DevOps Incident Analysis Suite

> Automatically classify ops logs by severity, generate actionable remediations, and push notifications to Slack and JIRA — all orchestrated by a LangGraph multi-agent pipeline with a live Streamlit dashboard.

### [Try the Live Demo](.......) | [Watch the Demo Video](......)

---

## Overview

The Multi-Agent DevOps Incident Analysis Suite ingests raw operational logs in any format (syslog, JSON, CSV, plain text), routes them through a chain of specialized AI agents, and surfaces structured findings in an interactive dashboard. A central LangGraph orchestrator drives the pipeline: it classifies every log entry by severity, generates root-cause remediations, and then fans out to downstream agents based on how critical the issues are. The result is a single-click workflow that takes unstructured noise and produces a prioritized incident runbook, Slack alerts, and JIRA-style tickets — in under a minute.

---

## Architecture

The system follows a **hub-and-spoke** pattern. The orchestrator owns the shared `IncidentState` and decides which agents to invoke after each step.

```
                       ┌───────────────────┐
                       │   Streamlit UI    │
                       │   (Dashboard)     │
                       └────────┬──────────┘
                                │  upload / paste logs
                                ▼
                       ┌───────────────────┐
                       │   Orchestrator    │
                       │   (LangGraph)     │
                       │                   │
                       │  Shared State:    │
                       │  IncidentState    │
                       └────────┬──────────┘
                                │
              ┌─────────────────▼──────────────────┐
              │           classifier node           │
              └─────────────────┬──────────────────┘
                                │
              ┌─────────────────▼──────────────────┐
              │          remediation node           │
              └──────┬──────────┬──────────┬───────┘
                     │          │          │
           ┌─────────▼──┐ ┌────▼────┐ ┌──▼──────────┐
           │  Cookbook  │ │  Slack  │ │ JIRA Ticket │
           │ Synthesizer│ │Notifier │ │    Agent    │
           └────────────┘ └─────────┘ └─────────────┘
```

### Routing Logic

After the Remediation Agent completes, the orchestrator inspects the highest severity found across all classified entries and fans out accordingly:

| Highest Severity | Agents Invoked |
|---|---|
| CRITICAL or HIGH | Cookbook Synthesizer + Slack Notifier + JIRA Ticket Agent |
| MEDIUM | Cookbook Synthesizer + Slack Notifier |
| LOW | Cookbook Synthesizer only |

All agents in the fan-out receive the full remediation list regardless of the trigger severity.

---

## Key Features

- **Multi-agent orchestration** via LangGraph with a shared `IncidentState` TypedDict that flows through every node
- **Severity-based conditional routing** — downstream agents are selected dynamically at runtime, not hardcoded
- **Multi-format log parsing** — handles syslog, JSON arrays, CSV, and plain-text log lines in a single LLM call using few-shot prompting
- **Real Slack integration** — formats Block Kit messages and posts to a configured channel via `slack-sdk`; send status is captured back to state
- **Mocked JIRA tickets** — generates structured ticket objects (title, priority, description, labels) displayed directly in the dashboard without requiring a live JIRA instance
- **Dark-theme Streamlit dashboard** — six-tab layout styled after New Relic / GitHub dark, with sidebar severity breakdown and category tags
- **Agent execution trace** — every node records start time, end time, input summary, and output summary; visualised as a trace bar and detailed table in the dashboard

---

## Tech Stack

| Component | Technology | Version |
|---|---|---|
| Orchestration | LangGraph | 0.4.1 |
| LLM framework | LangChain | 0.3.25 |
| LLM provider | OpenAI-compatible via OpenRouter (`langchain-openai`) | 0.3.12 |
| Dashboard | Streamlit | 1.45.1 |
| Slack integration | slack-sdk | 3.34.0 |
| Configuration | python-dotenv | 1.1.0 |
| Testing | pytest | 8.3.5 |

The application ships a thin `utils/llm.py` wrapper that maps `OPENROUTER_API_KEY` to the standard OpenAI environment variables, so any OpenRouter-hosted model (default: `openai/gpt-4o`) works without code changes.

---

## Project Structure

```
Group09/
├── app.py                        # Streamlit entry point — sidebar, tab layout, analysis loop
├── requirements.txt
├── .env.example                  # API key template
│
├── agents/
│   ├── classifier.py             # Log Classifier Agent — parses & classifies log entries
│   ├── remediation.py            # Remediation Agent — root-cause analysis & fix steps
│   ├── cookbook.py               # Cookbook Synthesizer — builds a markdown incident runbook
│   ├── slack_notifier.py         # Slack Notification Agent — posts Block Kit messages
│   └── jira_ticket.py            # JIRA Ticket Agent (mocked) — generates ticket objects
│
├── orchestrator/
│   ├── graph.py                  # LangGraph StateGraph definition & node wiring
│   ├── state.py                  # IncidentState TypedDict and all data models
│   └── router.py                 # Severity-based conditional routing logic
│
├── ui/
│   ├── components.py             # Reusable Streamlit components (trace bar, severity counts)
│   ├── tabs.py                   # Renderers for all six dashboard tabs
│   └── theme.css                 # Custom dark-theme CSS
│
├── utils/
│   ├── llm.py                    # LLM client factory (OpenRouter → OpenAI-compatible)
│   ├── log_parser.py             # File reading and format detection helpers
│   └── slack_client.py           # slack-sdk wrapper
│
├── tests/                        # pytest test suite (one file per agent/module)
│
├── sample_logs/
│   ├── mixed_incident.log        # Mixed-severity syslog-style incident
│   ├── k8s_crash.json            # Kubernetes crash events in JSON array format
│   ├── app_errors.csv            # Application errors in CSV format
│   └── system_logs_mixed_1000.log# 1 000-line mixed access + system log for load testing
│
└── docs/
    └── superpowers/specs/        # Design specifications
```

---

## Quick Start

1. **Clone the repository**

   ```bash
   git clone <repo-url>
   cd Group09
   ```

2. **Create and activate a virtual environment**

   ```bash
   python -m venv .venv
   # macOS/Linux
   source .venv/bin/activate
   # Windows
   .venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   ```bash
   cp .env.example .env
   ```

5. **Add your API keys to `.env`**

   ```dotenv
   OPENROUTER_API_KEY=openrouter-keys
   LLM_MODEL=llm-model
   SLACK_BOT_TOKEN=slack-bot-token (Ex - xoxb-......)
   SLACK_CHANNEL=slack-channel
   JIRA_INSTANCE_URL= jira-url (Ex. https://.......atlassian.net)
   JIRA_USER_EMAIL=jira-email
   JIRA_API_TOKEN=put-token-to-log-incident
   JIRA_PROJECT_KEY=workspace-or-project-token
   ```

   - Get an OpenRouter key at [openrouter.ai](https://openrouter.ai)
   - Create a Slack bot with `chat:write` scope and invite it to `SLACK_CHANNEL`
   - Log in to Jira and create a `Kanban` or `Scrum` Project. Look for Project Key to be used as `JIRA_PROJECT_KEY`.
   - Visit Atlassian security page and get API Token

6. **Run the dashboard**

   ```bash
   streamlit run app.py
   ```

   The app opens at `http://localhost:8501`.

---

## Usage

1. **Upload or paste logs** — use the sidebar file uploader (supports `.log`, `.txt`, `.json`, `.csv`) or paste raw log text directly into the text area
2. **Click "Analyze Logs"** — the multi-agent pipeline runs; a spinner shows progress
3. **Explore results across six tabs:**

   | Tab | Contents |
   |---|---|
   | Analysis | Classified log entries as severity-coded cards |
   | Remediations | Root-cause cards with numbered fix steps and confidence scores |
   | Cookbook | Rendered markdown incident runbook / checklist |
   | Slack Log | History of Slack messages sent with send status |
   | JIRA Tickets | Mocked ticket cards (title, priority, description, labels) |
   | Agent Trace | Full execution graph with per-node timing and I/O summaries |

4. The **sidebar** updates after analysis to show a severity breakdown counter and issue-category tags.

---

## Agents

### 1. Log Classifier Agent

**Input:** `raw_logs` (raw string from upload or paste)
**Output:** `classified_entries: list[LogEntry]`

Sends all log lines to the LLM in a single call using few-shot examples. Extracts timestamp, severity (`CRITICAL/HIGH/MEDIUM/LOW`), category (OOM, timeout, auth_failure, disk, network, …), source, and a one-line summary for every entry.

### 2. Remediation Agent

**Input:** `classified_entries`
**Output:** `remediations: list[Remediation]`

Groups related log entries into issue clusters, then reasons about root cause and generates ordered fix steps with a confidence score. Each remediation links back to the indices of the log entries that triggered it.

### 3. Cookbook Synthesizer Agent

**Input:** `remediations`
**Output:** `cookbook: str` (markdown)

Deduplicates and prioritises remediations by severity, then produces a structured incident-response runbook with grouped, numbered steps suitable for on-call engineers.

### 4. Slack Notification Agent

**Input:** `remediations` + severity context from state
**Output:** `slack_notifications: list[SlackMessage]`

Formats remediations into Slack Block Kit messages with severity badges and fix summaries, posts them to the configured channel via `slack-sdk`, and records each message's send status (`sent` / `failed`) back to state.

### 5. JIRA Ticket Agent (Mocked)

**Input:** `remediations` filtered to CRITICAL/HIGH severity
**Output:** `jira_tickets: list[JIRATicket]`

Converts critical issues into structured JIRA-style ticket objects with title, description, priority, assignee, and labels. No live JIRA API call is made — output is displayed directly in the dashboard.

---

## Testing

Run the full test suite with:

```bash
pytest tests/ -v
```

Tests cover all five agents, the orchestrator graph, the router, state initialisation, and log-parser utilities.

---

## Sample Logs

| File | Format | Contents |
|---|---|---|
| `sample_logs/logfile_15_incidents.log` | 15 incidents - Simple log file | CRITICAL/ERROR/WARN - issues related to permissions, timeout |
| `sample_logs/logfile_100_incidents.txt` | 100 incidents - Simple text file | CRITICAL/ERROR/WARN - issues related to pod crash, memory, connectivity |
| `sample_logs/pod_crash_6_incidents.json` | 06 incidents - JSON Format | ERROR/WARNING - issues related to kubernetes failures for pods, CrashLoopBackOff, back-off |
| `sample_logs/csv_incident_logs_8_incidents.csv` | 8 incidents - CSV File| ERROR/WARN - Application-layer errors — payment gateway timeouts, connection failures |
| `sample_logs/logfile_1000_lines.log` | 1000 lines - Simple log file | 1000-line dataset combining HTTP access logs and system events for load testing |

---

## Team

*Group 9 — AI Engineers Accelerated Program - C6*
--
Below team members worked together to complete the assignment for submission
 - Tushar
 - Kanishkar
 - Wikram
 - Vivek
 - Sachin
 - Ajay
 - Mayur
 - Shareena

---

## Inspired by Outskill Engineering Accelerator Team

- Sham
- Vidit
- Kartik
- Divij
- Ishan
- Dileep
- Siddharth

---
