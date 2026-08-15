"""Tests for priority analyzer."""

import pytest
from community_autopilot.analyzer import Analyzer
from community_autopilot.models import Priority


@pytest.mark.asyncio
async def test_prioritize_critical(stale_issue, settings):
    analyzer = Analyzer(settings, None)
    priority = analyzer.prioritize(stale_issue)
    assert priority == Priority.CRITICAL


@pytest.mark.asyncio
async def test_prioritize_high(settings, sample_issue):
    from datetime import timedelta, timezone
    sample_issue.updated_at = datetime.now(timezone.utc) - timedelta(hours=8)
    analyzer = Analyzer(settings, None)
    priority = analyzer.prioritize(sample_issue)
    assert priority == Priority.HIGH


@pytest.mark.asyncio
async def test_prioritize_medium(settings, sample_issue):
    from datetime import timedelta, timezone
    sample_issue.labels = ["good first issue"]
    sample_issue.assignees = []
    sample_issue.updated_at = datetime.now(timezone.utc) - timedelta(hours=200)
    analyzer = Analyzer(settings, None)
    priority = analyzer.prioritize(sample_issue)
    assert priority == Priority.MEDIUM


@pytest.mark.asyncio
async def test_prioritize_low(settings, sample_issue):
    analyzer = Analyzer(settings, None)
    priority = analyzer.prioritize(sample_issue)
    assert priority == Priority.LOW
