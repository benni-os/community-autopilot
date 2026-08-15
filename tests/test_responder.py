"""Tests for responder module."""

import pytest
from community_autopilot.responder import Responder
from community_autopilot.models import DraftResponse, Priority, Issue, Comment, IssueState
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_post_dry_run(settings, sample_issue):
    nemesis = None
    responder = Responder(settings, nemesis)
    draft = DraftResponse(
        issue=sample_issue,
        priority=Priority.HIGH,
        draft_body="Test response",
        reasoning="test",
        requires_approval=False,
        estimated_tokens=10,
        trace_id="test-123",
    )
    url = await responder.post(draft)
    assert url == "dry-run://skipped"


@pytest.mark.asyncio
async def test_post_live(settings, sample_issue, httpx_mock):
    settings.dry_run = False
    httpx_mock.add_response(
        url=f"https://api.github.com/repos/{settings.github_org}/{sample_issue.repo}/issues/{sample_issue.number}/comments",
        status_code=201,
        json={"html_url": "https://github.com/benni-os/mcp-forge/issues/34#issuecomment-test"},
    )
    nemesis = None
    responder = Responder(settings, nemesis)
    draft = DraftResponse(
        issue=sample_issue,
        priority=Priority.HIGH,
        draft_body="Test response",
        reasoning="test",
        requires_approval=False,
        estimated_tokens=10,
        trace_id="test-123",
    )
    url = await responder.post(draft)
    assert "issuecomment-test" in url
