"""Tests for SlackNotifier."""

from datetime import UTC, datetime

import pytest
from pytest_httpx import HTTPXMock

from community_autopilot.config import Settings
from community_autopilot.models import AutopilotRun, DraftResponse, Issue, Priority
from community_autopilot.slack import SlackNotifier


@pytest.mark.asyncio
async def test_notify_run_summary(settings: Settings, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://hooks.slack.com/services/test", status_code=200)
    notifier = SlackNotifier(settings)
    run = AutopilotRun(
        run_id="run-1",
        started_at=datetime.now(UTC),
        issues_scanned=5,
        comments_posted=2,
        drafts_pending=1,
        cost_usd=0.025,
        errors=["Error 1"],
    )
    success = await notifier.notify_run_summary(run)
    assert success is True
    assert len(httpx_mock.get_requests()) == 1


@pytest.mark.asyncio
async def test_notify_run_summary_disabled() -> None:
    settings = Settings(slack_webhook_url=None)
    notifier = SlackNotifier(settings)
    run = AutopilotRun(
        run_id="run-2",
        started_at=datetime.now(UTC),
    )
    success = await notifier.notify_run_summary(run)
    assert success is False


@pytest.mark.asyncio
async def test_notify_run_summary_network_error(settings: Settings, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(Exception("Network error"))
    notifier = SlackNotifier(settings)
    run = AutopilotRun(
        run_id="run-err",
        started_at=datetime.now(UTC),
    )
    success = await notifier.notify_run_summary(run)
    assert success is False


@pytest.mark.asyncio
async def test_notify_pending_draft(
    settings: Settings, sample_issue: Issue, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(url="https://hooks.slack.com/services/test", status_code=200)
    notifier = SlackNotifier(settings)
    draft = DraftResponse(
        issue=sample_issue,
        priority=Priority.CRITICAL,
        draft_body="Critical notification draft",
        reasoning="urgent attention needed",
        requires_approval=True,
        estimated_tokens=50,
        trace_id="trace-crit-99",
    )
    success = await notifier.notify_pending_draft(draft)
    assert success is True
    assert len(httpx_mock.get_requests()) == 1


@pytest.mark.asyncio
async def test_notify_pending_draft_disabled(sample_issue: Issue) -> None:
    settings = Settings(slack_webhook_url=None)
    notifier = SlackNotifier(settings)
    draft = DraftResponse(
        issue=sample_issue,
        priority=Priority.LOW,
        draft_body="Draft",
        reasoning="low",
        requires_approval=False,
        estimated_tokens=10,
        trace_id="trace-low",
    )
    success = await notifier.notify_pending_draft(draft)
    assert success is False


@pytest.mark.asyncio
async def test_notify_pending_draft_network_error(
    settings: Settings, sample_issue: Issue, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_exception(Exception("Connection timeout"))
    notifier = SlackNotifier(settings)
    draft = DraftResponse(
        issue=sample_issue,
        priority=Priority.HIGH,
        draft_body="Draft",
        reasoning="high",
        requires_approval=True,
        estimated_tokens=10,
        trace_id="trace-hi",
    )
    success = await notifier.notify_pending_draft(draft)
    assert success is False
