"""Tests for priority analyzer."""

from datetime import UTC, datetime, timedelta

import pytest

from community_autopilot.analyzer import Analyzer
from community_autopilot.config import Settings
from community_autopilot.models import Issue, Priority


@pytest.mark.asyncio
async def test_prioritize_critical(stale_issue: Issue, settings: Settings) -> None:
    analyzer = Analyzer(settings, None)
    priority = analyzer.prioritize(stale_issue)
    assert priority == Priority.CRITICAL


@pytest.mark.asyncio
async def test_prioritize_high(settings: Settings, sample_issue: Issue) -> None:
    sample_issue.updated_at = datetime.now(UTC) - timedelta(hours=8)
    analyzer = Analyzer(settings, None)
    priority = analyzer.prioritize(sample_issue)
    assert priority == Priority.HIGH


@pytest.mark.asyncio
async def test_prioritize_medium(settings: Settings, sample_issue: Issue) -> None:
    sample_issue.labels = ["good first issue"]
    sample_issue.assignees = []
    sample_issue.updated_at = datetime.now(UTC) - timedelta(hours=200)
    sample_issue.comments = []
    analyzer = Analyzer(settings, None)
    priority = analyzer.prioritize(sample_issue)
    assert priority == Priority.MEDIUM


@pytest.mark.asyncio
async def test_prioritize_low(settings: Settings, sample_issue: Issue) -> None:
    # Maintainer commented, no external pending comment
    sample_issue.comments[0].is_maintainer = True
    analyzer = Analyzer(settings, None)
    priority = analyzer.prioritize(sample_issue)
    assert priority == Priority.LOW


@pytest.mark.asyncio
async def test_build_context_and_analyze(settings: Settings, sample_issue: Issue) -> None:
    sample_issue.updated_at = datetime.now(UTC) - timedelta(hours=10)
    analyzer = Analyzer(settings, None)
    context = analyzer.build_context(sample_issue)
    assert "mcp-forge" in context
    assert "#34" in context

    # Test analyze with fallback draft generation
    draft = await analyzer.analyze(sample_issue)
    assert draft.issue.number == 34
    assert draft.priority == Priority.HIGH
    assert len(draft.draft_body) > 0
    assert draft.trace_id.startswith("autopilot-")
