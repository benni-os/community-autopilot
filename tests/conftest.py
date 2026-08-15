"""Pytest fixtures and mocks."""

import pytest
from datetime import datetime, timezone

from community_autopilot.config import Settings
from community_autopilot.models import Issue, Comment, IssueState, Priority


@pytest.fixture
def settings():
    return Settings(
        github_token="test_token",
        nemesis_api_key="test_key",
        dry_run=True,
    )


@pytest.fixture
def sample_issue():
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
                created_at=datetime.now(timezone.utc),
                is_maintainer=False,
                html_url="https://github.com/benni-os/mcp-forge/issues/34#issuecomment-1",
            )
        ],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        html_url="https://github.com/benni-os/mcp-forge/issues/34",
        assignees=[],
    )


@pytest.fixture
def stale_issue():
    from datetime import timedelta
    old = datetime.now(timezone.utc) - timedelta(hours=50)
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
