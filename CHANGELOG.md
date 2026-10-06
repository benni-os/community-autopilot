# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-10-06

### Added
- **Real-Time Webhook Server (`community_autopilot.webhook`)**:
  - FastAPI-based webhook receiver listening on port 8000 (`/health`, `/ready`, `/webhook`).
  - Cryptographic verification of GitHub HMAC-SHA256 signatures (`X-Hub-Signature-256`).
  - Auto-triage and instant draft generation for `issues` (`opened`, `reopened`) and `issue_comment` (`created`).
- **Slack Notification Integration (`community_autopilot.slack`)**:
  - Full Slack Incoming Webhook notifications for completed runs and pending draft reviews.
- **Enhanced CLI Commands**:
  - `autopilot serve`: Runs the Webhook server with host/port configuration.
  - `autopilot health`: Pre-flight diagnostics checking tokens, orgs, NEMESIS, and Slack.
  - `autopilot approve`: Interactive or direct approval of drafted issue responses.
- **Comprehensive Test Suite**:
  - Expanded from 14 tests to 43 tests with 93% code coverage.
  - 100% compliance with `mypy --strict` and `ruff check`.

### Changed
- Configured Hatchling build system in `pyproject.toml` with `src` layout support.
- Updated `docker/Dockerfile` layer caching and build order.
- Updated `k8s/deployment.yaml` with long-running webhook container and probes.
- Upgraded `models.py` to modern `enum.StrEnum`.

### Fixed
- Fixed critical packaging issue where `community_autopilot` was not discovered by editable installs.
- Fixed `docker/Dockerfile` build failure where `pip install .` was executed before `src/` was copied.
- Fixed `NameError: datetime` across `test_analyzer.py` and `test_watcher.py`.
- Fixed `AttributeError: NoneType` on `NemesisClient` when passed as `None`.
- Fixed trace ID length assertion calculation (`len(trace_id) == 22`).
- Fixed `pytest-httpx` assertion method incompatibilities.
- Fixed unhandled exceptions in `NemesisClient.save_snapshot` to guarantee crash resilience.

---

## [0.1.0] - 2026-08-15

### Added
- Initial release of Community Autopilot
- Core modules: config, models, nemesis, watcher, analyzer, responder, prompts, cli
- Docker + K8s manifests
- GitHub Actions workflows (watch, deploy, test)
- NEMESIS Event Bus integration
- Safety gates: dry-run, cost caps, approval requirements
