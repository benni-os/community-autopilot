"""Tests for NEMESIS client."""

from datetime import UTC, datetime

import pytest
from pytest_httpx import HTTPXMock

from community_autopilot.config import Settings
from community_autopilot.nemesis import NemesisClient, NemesisEvent


@pytest.mark.asyncio
async def test_new_trace_id(settings: Settings) -> None:
    client = NemesisClient(settings)
    trace_id = client.new_trace_id()
    assert trace_id.startswith("autopilot-")
    assert len(trace_id) == 22  # "autopilot-" (10 chars) + 12 hex chars = 22
    await client.close()


@pytest.mark.asyncio
async def test_emit_event(settings: Settings, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=f"{settings.nemesis_url}/v1/events", status_code=200)
    async with NemesisClient(settings) as client:
        event = NemesisEvent(
            trace_id="test-123",
            tenant_id=settings.tenant_id,
            event_type="test.event",
            objective="Test objective",
            cost_usd=0.001,
            evidence={"key": "value"},
            timestamp=datetime.now(UTC),
        )
        await client.emit(event)
    assert len(httpx_mock.get_requests()) == 1


@pytest.mark.asyncio
async def test_save_snapshot(settings: Settings, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=f"{settings.nemesis_url}/v1/snapshots", status_code=200)
    async with NemesisClient(settings) as client:
        await client.save_snapshot("completed", "test", "next")
    assert len(httpx_mock.get_requests()) == 1


@pytest.mark.asyncio
async def test_log_action(settings: Settings, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=f"{settings.nemesis_url}/v1/events", status_code=200)
    async with NemesisClient(settings) as client:
        tid = await client.log_action(
            event_type="test.action",
            objective="Perform test",
            cost_usd=0.01,
            evidence={"ok": True},
        )
        assert tid.startswith("autopilot-")
    assert len(httpx_mock.get_requests()) == 1


@pytest.mark.asyncio
async def test_emit_event_handles_network_error(settings: Settings, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(Exception("Connection refused"))
    async with NemesisClient(settings) as client:
        event = NemesisEvent(
            trace_id="test-err",
            tenant_id=settings.tenant_id,
            event_type="test.fail",
            objective="Fail gracefully",
            cost_usd=0.0,
            evidence={},
            timestamp=datetime.now(UTC),
        )
        # Should not raise exception
        await client.emit(event)
