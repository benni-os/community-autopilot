"""Tests for GitHub watcher."""

from datetime import UTC, datetime, timedelta

import pytest
from pytest_httpx import HTTPXMock

from community_autopilot.config import Settings
from community_autopilot.models import Issue
from community_autopilot.watcher import GitHubWatcher


@pytest.mark.asyncio
async def test_needs_attention_no_comments(settings: Settings, sample_issue: Issue) -> None:
    watcher = GitHubWatcher(settings, None)
    sample_issue.comments = []
    cutoff = datetime.now(UTC) - timedelta(hours=48)
    sample_issue.created_at = cutoff - timedelta(hours=1)
    assert watcher._needs_attention(sample_issue, cutoff) is True
    await watcher.close()


@pytest.mark.asyncio
async def test_needs_attention_external_comment(settings: Settings, sample_issue: Issue) -> None:
    watcher = GitHubWatcher(settings, None)
    cutoff = datetime.now(UTC) - timedelta(hours=48)
    sample_issue.comments[-1].created_at = cutoff - timedelta(hours=1)
    sample_issue.comments[-1].is_maintainer = False
    assert watcher._needs_attention(sample_issue, cutoff) is True
    await watcher.close()


@pytest.mark.asyncio
async def test_needs_attention_maintainer_comment(settings: Settings, sample_issue: Issue) -> None:
    watcher = GitHubWatcher(settings, None)
    sample_issue.comments[-1].is_maintainer = True
    cutoff = datetime.now(UTC) - timedelta(hours=48)
    assert watcher._needs_attention(sample_issue, cutoff) is False
    await watcher.close()


@pytest.mark.asyncio
async def test_scan_all(settings: Settings, httpx_mock: HTTPXMock) -> None:
    settings.watched_repos = ["mcp-forge"]
    httpx_mock.add_response(
        url=f"https://api.github.com/repos/{settings.github_org}/mcp-forge/issues?state=open&per_page=100&sort=updated&direction=desc",
        status_code=200,
        json=[
            {
                "number": 10,
                "title": "Unanswered Bug",
                "body": "Something is broken",
                "user": {"login": "external-user"},
                "labels": [{"name": "bug"}],
                "created_at": "2026-08-01T12:00:00Z",
                "updated_at": "2026-08-01T12:00:00Z",
                "html_url": "https://github.com/benni-os/mcp-forge/issues/10",
                "assignees": [],
            }
        ],
    )
    httpx_mock.add_response(
        url=f"https://api.github.com/repos/{settings.github_org}/mcp-forge/issues/10/comments?per_page=100",
        status_code=200,
        json=[],
    )
    async with GitHubWatcher(settings, None) as watcher:
        issues = await watcher.scan_all()
        assert len(issues) == 1
        assert issues[0].number == 10
