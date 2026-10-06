"""Tests for responder module."""

import pytest
from pytest_httpx import HTTPXMock

from community_autopilot.config import Settings
from community_autopilot.models import DraftResponse, Issue, Priority
from community_autopilot.nemesis import NemesisClient
from community_autopilot.responder import Responder


@pytest.mark.asyncio
async def test_post_dry_run(settings: Settings, sample_issue: Issue) -> None:
    responder = Responder(settings, None)
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
    await responder.close()


@pytest.mark.asyncio
async def test_post_live(settings: Settings, sample_issue: Issue, httpx_mock: HTTPXMock) -> None:
    settings.dry_run = False
    comment_target = (
        f"https://api.github.com/repos/{settings.github_org}/{sample_issue.repo}/issues/"
        f"{sample_issue.number}/comments"
    )
    httpx_mock.add_response(
        url=comment_target,
        status_code=201,
        json={"html_url": "https://github.com/benni-os/mcp-forge/issues/34#issuecomment-test"},
    )
    if settings.slack_webhook_url:
        httpx_mock.add_response(
            url=settings.slack_webhook_url,
            status_code=200,
        )

    responder = Responder(settings, None)
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
    await responder.close()


@pytest.mark.asyncio
async def test_post_live_with_nemesis(
    settings: Settings, sample_issue: Issue, httpx_mock: HTTPXMock
) -> None:
    settings.dry_run = False
    comment_target = (
        f"https://api.github.com/repos/{settings.github_org}/{sample_issue.repo}/issues/"
        f"{sample_issue.number}/comments"
    )
    httpx_mock.add_response(
        url=comment_target,
        status_code=201,
        json={"html_url": "https://github.com/benni-os/mcp-forge/issues/34#issuecomment-test"},
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

    async with NemesisClient(settings) as nemesis, Responder(settings, nemesis) as responder:
        draft = DraftResponse(
            issue=sample_issue,
            priority=Priority.CRITICAL,
            draft_body="Critical fix response",
            reasoning="critical test",
            requires_approval=False,
            estimated_tokens=20,
            trace_id="test-crit-123",
        )
        url = await responder.post(draft)
        assert "issuecomment-test" in url
