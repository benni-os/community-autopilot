"""Pytest fixtures and mocks."""

from datetime import UTC, datetime, timedelta

import pytest

from community_autopilot.config import Settings
from community_autopilot.models import Comment, Issue, IssueState


@pytest.fixture(autouse=True)
def set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "test_token")
    monkeypatch.setenv("NEMESIS_API_KEY", "test_key")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test")
    monkeypatch.setenv("WEBHOOK_SECRET", "test_secret")


@pytest.fixture
def settings() -> Settings:
    return Settings(
        github_token="test_token",
        nemesis_api_key="test_key",
        dry_run=True,
        slack_webhook_url="https://hooks.slack.com/services/test",
    )


@pytest.fixture
def sample_issue() -> Issue:
    now = datetime.now(UTC)
    return Issue(
        number=34,
        repo="mcp-forge",
        title="Add database contrib router",
        body="Add a database router...",
        state=IssueState.OPEN,
        author="contributor",
        labels=["enhancement", "good first issue"],
        comments=[
            Comment(
                id=1,
                author="contributor",
                body="I'd like to work on this.",
                created_at=now,
                is_maintainer=False,
                html_url="https://github.com/benni-os/mcp-forge/issues/34#issuecomment-1",
            )
        ],
        created_at=now,
        updated_at=now,
        html_url="https://github.com/benni-os/mcp-forge/issues/34",
        assignees=[],
    )


@pytest.fixture
def stale_issue() -> Issue:
    old = datetime.now(UTC) - timedelta(hours=50)
    return Issue(
        number=35,
        repo="mcp-forge",
        title="Stale issue",
        body="Old issue...",
        state=IssueState.OPEN,
        author="contributor",
        labels=[],
        comments=[
            Comment(
                id=2,
                author="contributor",
                body="Still waiting...",
                created_at=old,
                is_maintainer=False,
                html_url="https://github.com/benni-os/mcp-forge/issues/35#issuecomment-2",
            )
        ],
        created_at=old,
        updated_at=old,
        html_url="https://github.com/benni-os/mcp-forge/issues/35",
        assignees=[],
    )
