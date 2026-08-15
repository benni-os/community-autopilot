"""Tests for NEMESIS client."""

import pytest
from community_autopilot.nemesis import NemesisClient, NemesisEvent
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_new_trace_id(settings):
    client = NemesisClient(settings)
    trace_id = client.new_trace_id()
    assert trace_id.startswith("autopilot-")
    assert len(trace_id) == 21  # "autopilot-" + 12 hex chars


@pytest.mark.asyncio
async def test_emit_event(settings, httpx_mock):
    httpx_mock.add_response(url=f"{settings.nemesis_url}/v1/events", status_code=200)
    client = NemesisClient(settings)
    event = NemesisEvent(
        trace_id="test-123",
        tenant_id=settings.tenant_id,
        event_type="test.event",
        objective="Test objective",
        cost_usd=0.001,
        evidence={"key": "value"},
        timestamp=datetime.now(timezone.utc),
    )
    await client.emit(event)
    assert httpx_mock.call_count == 1


@pytest.mark.asyncio
async def test_save_snapshot(settings, httpx_mock):
    httpx_mock.add_response(url=f"{settings.nemesis_url}/v1/snapshots", status_code=200)
    client = NemesisClient(settings)
    await client.save_snapshot("completed", "test", "next")
    assert httpx_mock.call_count == 1
