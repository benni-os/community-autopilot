"""Tests for GitHub watcher."""

import pytest
from datetime import timedelta, timezone
from community_autopilot.watcher import GitHubWatcher, MAINTAINER_LOGINS


@pytest.mark.asyncio
async def test_needs_attention_no_comments(settings, sample_issue):
    watcher = GitHubWatcher(settings, None)
    sample_issue.comments = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    sample_issue.created_at = cutoff - timedelta(hours=1)
    assert watcher._needs_attention(sample_issue, cutoff) is True


@pytest.mark.asyncio
async def test_needs_attention_external_comment(settings, sample_issue):
    watcher = GitHubWatcher(settings, None)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    assert watcher._needs_attention(sample_issue, cutoff) is True


@pytest.mark.asyncio
async def test_needs_attention_maintainer_comment(settings, sample_issue):
    watcher = GitHubWatcher(settings, None)
    sample_issue.comments[-1].is_maintainer = True
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    assert watcher._needs_attention(sample_issue, cutoff) is False
