# 🤖 Benni OS Community Autopilot

[![CI Quality Gate](https://github.com/benni-os/community-autopilot/actions/workflows/test.yml/badge.svg)](https://github.com/benni-os/community-autopilot/actions/workflows/test.yml)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](docker/Dockerfile)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![Checked with mypy](https://img.shields.io/badge/mypy-strict-success.svg)](https://mypy-lang.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Benni OS Community Autopilot** is an autonomous GitHub issue triage and responder agent with **NEMESIS** tracing, multi-repo surveillance, safety gates, Slack operational notifications, and real-time webhook ingestion.

---

## 🌟 Key Features

- **⚡ Autonomous Issue & Comment Triage:** Continuously scans configured repositories for unanswered issues and pending contributor questions.
- **🧠 Contextual LLM Responses:** Drafts helpful, maintainer-voiced responses using NEMESIS Nexus or local LLM backends with smart SLA prioritization (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
- **🛡️ Multi-tier Safety Gates:**
  - Strict maintainer verification to prevent self-responding.
  - `--dry-run` simulation mode for zero-risk inspection.
  - Mandatory approval gate for high-priority or sensitive tickets.
  - Hard caps on comments and budget per execution cycle.
- **📡 Real-time GitHub Webhook Server:** Built-in FastAPI server with HMAC-SHA256 signature verification for instant issue reaction.
- **📊 NEMESIS Event Bus Integration:** Complete action provenance, cost attribution, and audit trail snapshots logged directly to NEMESIS.
- **💬 Slack Operations Notifications:** Real-time channel alerts for run summaries and drafts awaiting manual maintainer approval.

---

## 🏗️ Architecture

```
                       +-----------------------------+
                       |      GitHub Repositories    |
                       |  (mcp-forge, benni-nexus..) |
                       +--------------+--------------+
                                      |
                 Polling / Cron       |       Real-Time Webhooks
                       v              |               v
              +-----------------+     |     +--------------------+
              |  GitHubWatcher  |     |     |   Webhook Server   |
              +--------+--------+     |     |  (FastAPI: 8000)   |
                       |              |     +---------+----------+
                       +-------+      |               |
                               |      v               |
                               +---> [ Analyzer ] <---+
                                       |
                     +-----------------+-----------------+
                     |                                   |
                     v                                   v
             [ NEMESIS Nexus ]                   [ Safety Engine ]
             (LLM Reasoning)                     (Rate-limit, SLA,
                     |                            Approval Gate)
                     v                                   |
           +-------------------+                         v
           |   DraftResponse   | ----------------> [ Slack Alert ]
           +---------+---------+                 (Review Needed)
                     | (Approved or Low-risk)
                     v
           +-------------------+
           |     Responder     | ----> Post to GitHub Issue
           +---------+---------+
                     |
                     v
          +----------------------+
          |  NEMESIS Event Bus   | ----> Audit snapshot & trace
          +----------------------+
```

---

## 🚀 Quickstart

### Prerequisites

- Python `>= 3.12`
- [uv](https://docs.astral.sh/uv/) (recommended) or `pip`

### 1. Clone & Install

```bash
git clone https://github.com/benni-os/community-autopilot.git
cd community-autopilot

# Install dependencies and editable package
uv sync --all-extras
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```env
# GitHub
GITHUB_TOKEN=ghp_your_personal_access_token
GITHUB_ORG=benni-os

# NEMESIS
NEMESIS_URL=https://nemesis.benni.os
NEMESIS_API_KEY=your_nemesis_key
TENANT_ID=benni-os

# Slack (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx
SLACK_CHANNEL=#community

# Webhook Server
WEBHOOK_SECRET=your_github_webhook_secret
```

---

## 💻 CLI Usage

The package provides the `autopilot` command:

```bash
# 1. Pre-flight health and configuration check
autopilot health

# 2. Scan issues in dry-run mode (preview drafts without posting)
autopilot scan --dry-run

# 3. Scan a specific repository
autopilot scan --dry-run --repo mcp-forge

# 4. Execute a full triage run
autopilot run --max 10

# 5. Review & explicitly approve an issue draft
autopilot approve --repo mcp-forge --issue 42 --message "Thanks for raising! We are reviewing."

# 6. Launch the real-time GitHub Webhook server
autopilot serve --host 0.0.0.0 --port 8000
```

---

## 🐳 Docker & Kubernetes Deployment

### Run with Docker

```bash
# Build Docker image
docker build -t community-autopilot -f docker/Dockerfile .

# Run one-off scan
docker run --rm --env-file .env community-autopilot scan --dry-run

# Run webhook daemon
docker run -d -p 8000:8000 --env-file .env community-autopilot serve
```

### Kubernetes

Manifests are provided in `k8s/`:

```bash
# 1. Apply secrets
kubectl apply -f k8s/secret.yaml -n benni-os

# 2. Deploy Webhook Server (Continuous)
kubectl apply -f k8s/deployment.yaml -n benni-os
kubectl apply -f k8s/service.yaml -n benni-os

# 3. Or deploy as a Scheduled CronJob (Runs every 6 hours)
kubectl apply -f k8s/cronjob.yaml -n benni-os
```

---

## 🧪 Testing & Code Quality

The codebase enforces strict type safety and quality standards:

```bash
# Run tests with coverage (>90% required)
uv run pytest

# Run Ruff linter and formatter
uv run ruff check src/ tests/

# Run MyPy in strict mode
uv run mypy --strict src/ tests/
```

---

## 📄 License

MIT © [Benni OS](https://github.com/benni-os)
