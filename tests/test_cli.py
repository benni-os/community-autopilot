import re

from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from community_autopilot.cli import app
from community_autopilot.config import Settings

runner = CliRunner(env={"NO_COLOR": "1", "TERM": "dumb"})


def _clean(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text)


def test_scan_help() -> None:
    result = runner.invoke(app, ["scan", "--help"])
    assert result.exit_code == 0
    assert "dry-run" in _clean(result.stdout)


def test_run_help() -> None:
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "max" in _clean(result.stdout)


def test_serve_help() -> None:
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    assert "port" in _clean(result.stdout)


def test_approve_help() -> None:
    result = runner.invoke(app, ["approve", "--help"])
    assert result.exit_code == 0
    assert "issue" in _clean(result.stdout)


def test_health_command() -> None:
    result = runner.invoke(app, ["health"])
    assert result.exit_code == 0
    assert "System Health" in result.stdout


def test_scan_dry_run(settings: Settings, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"https://api.github.com/repos/{settings.github_org}/mcp-forge/issues?state=open&per_page=100&sort=updated&direction=desc",
        status_code=200,
        json=[],
    )
    httpx_mock.add_response(
        url=f"{settings.nemesis_url}/v1/events",
        status_code=200,
    )
    result = runner.invoke(app, ["scan", "--dry-run", "--repo", "mcp-forge"])
    assert result.exit_code == 0
    assert "Unanswered Issues (0)" in result.stdout


def test_run_dry_run(settings: Settings, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"https://api.github.com/repos/{settings.github_org}/mcp-forge/issues?state=open&per_page=100&sort=updated&direction=desc",
        status_code=200,
        json=[],
    )
    httpx_mock.add_response(
        url=f"{settings.nemesis_url}/v1/events",
        status_code=200,
    )
    httpx_mock.add_response(
        url=f"{settings.nemesis_url}/v1/snapshots",
        status_code=200,
    )
    if settings.slack_webhook_url:
        httpx_mock.add_response(
            url=settings.slack_webhook_url,
            status_code=200,
        )
    result = runner.invoke(app, ["run", "--dry-run", "--repo", "mcp-forge"])
    assert result.exit_code == 0
    assert "complete" in result.stdout


def test_approve_command(settings: Settings, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"https://api.github.com/repos/{settings.github_org}/mcp-forge/issues/42",
        status_code=200,
        json={
            "number": 42,
            "title": "Need help with API",
            "body": "How to call nexus?",
            "user": {"login": "dev1"},
            "labels": [],
            "created_at": "2026-08-01T00:00:00Z",
            "updated_at": "2026-08-01T00:00:00Z",
            "html_url": "https://github.com/benni-os/mcp-forge/issues/42",
            "assignees": [],
        },
    )
    httpx_mock.add_response(
        url=f"{settings.nemesis_url}/v1/nexus/inference",
        status_code=200,
        json={"choices": [{"message": {"content": "Here is how to call nexus."}}]},
    )
    httpx_mock.add_response(
        url=f"https://api.github.com/repos/{settings.github_org}/mcp-forge/issues/42/comments",
        status_code=201,
        json={"html_url": "https://github.com/benni-os/mcp-forge/issues/42#issuecomment-99"},
    )
    httpx_mock.add_response(
        url=f"{settings.nemesis_url}/v1/events",
        status_code=200,
    )
    if settings.slack_webhook_url:
        httpx_mock.add_response(
            url=settings.slack_webhook_url,
            status_code=200,
        )

    result = runner.invoke(app, ["approve", "--repo", "mcp-forge", "--issue", "42"])
    assert result.exit_code == 0
    assert "Comment posted successfully" in result.stdout


def test_scan_with_found_issues(settings: Settings, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"https://api.github.com/repos/{settings.github_org}/mcp-forge/issues?state=open&per_page=100&sort=updated&direction=desc",
        status_code=200,
        json=[
            {
                "number": 101,
                "title": "Bug in gateway",
                "body": "It crashed",
                "user": {"login": "reporter"},
                "labels": [{"name": "bug"}],
                "created_at": "2026-08-01T00:00:00Z",
                "updated_at": "2026-08-01T00:00:00Z",
                "html_url": "https://github.com/benni-os/mcp-forge/issues/101",
                "assignees": [],
            }
        ],
    )
    httpx_mock.add_response(
        url=f"https://api.github.com/repos/{settings.github_org}/mcp-forge/issues/101/comments?per_page=100",
        status_code=200,
        json=[],
    )
    httpx_mock.add_response(
        url=f"{settings.nemesis_url}/v1/nexus/inference",
        status_code=200,
        json={"choices": [{"message": {"content": "We are looking into this bug."}}]},
    )
    httpx_mock.add_response(
        url=f"{settings.nemesis_url}/v1/events",
        status_code=200,
    )

    result = runner.invoke(app, ["scan", "--dry-run", "--repo", "mcp-forge"])
    assert result.exit_code == 0
    assert "Unanswered Issues (1)" in result.stdout
    assert "Bug in gateway" in result.stdout


def test_run_with_issues_and_approval_skip(settings: Settings, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"https://api.github.com/repos/{settings.github_org}/mcp-forge/issues?state=open&per_page=100&sort=updated&direction=desc",
        status_code=200,
        json=[
            {
                "number": 102,
                "title": "Critical downtime",
                "body": "System unavailable",
                "user": {"login": "reporter2"},
                "labels": [{"name": "critical"}],
                "created_at": "2026-08-01T00:00:00Z",
                "updated_at": "2026-08-01T00:00:00Z",
                "html_url": "https://github.com/benni-os/mcp-forge/issues/102",
                "assignees": [],
            }
        ],
    )
    httpx_mock.add_response(
        url=f"https://api.github.com/repos/{settings.github_org}/mcp-forge/issues/102/comments?per_page=100",
        status_code=200,
        json=[],
    )
    httpx_mock.add_response(
        url=f"{settings.nemesis_url}/v1/nexus/inference",
        status_code=200,
        json={"choices": [{"message": {"content": "Investigating immediately."}}]},
    )
    httpx_mock.add_response(
        url=f"{settings.nemesis_url}/v1/events",
        status_code=200,
    )
    httpx_mock.add_response(
        url=f"{settings.nemesis_url}/v1/snapshots",
        status_code=200,
    )
    if settings.slack_webhook_url:
        httpx_mock.add_response(
            url=settings.slack_webhook_url,
            status_code=200,
        )
        httpx_mock.add_response(
            url=settings.slack_webhook_url,
            status_code=200,
        )

    # With dry_run=False and require_approval=True (default), it skips posting and notifies
    result = runner.invoke(app, ["run", "--max", "5", "--repo", "mcp-forge"])
    assert result.exit_code == 0
    assert "Approval required for #102" in result.stdout
    assert "Pending: 1" in result.stdout

