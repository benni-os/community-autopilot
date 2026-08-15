"""NEMESIS Event Bus client — every action must have trace_id, tenant_id, objective, cost, evidence."""

import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from pydantic import BaseModel

from .config import Settings


class NemesisEvent(BaseModel):
    trace_id: str
    tenant_id: str
    event_type: str
    objective: str
    cost_usd: float
    evidence: dict[str, Any]
    timestamp: datetime
    metadata: dict[str, Any] = {}


class NemesisClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = httpx.AsyncClient(
            base_url=settings.nemesis_url,
            headers={"Authorization": f"Bearer {settings.nemesis_api_key}"},
            timeout=30.0,
        )

    def new_trace_id(self) -> str:
        return f"autopilot-{uuid.uuid4().hex[:12]}"

    async def emit(self, event: NemesisEvent) -> None:
        try:
            await self.client.post("/v1/events", json=event.model_dump(mode="json"))
        except Exception as exc:
            print(f"[NEMESIS] Failed to emit event: {exc}")

    async def log_action(
        self,
        *,
        event_type: str,
        objective: str,
        cost_usd: float,
        evidence: dict[str, Any],
        trace_id: str | None = None,
    ) -> str:
        tid = trace_id or self.new_trace_id()
        await self.emit(
            NemesisEvent(
                trace_id=tid,
                tenant_id=self.settings.tenant_id,
                event_type=event_type,
                objective=objective,
                cost_usd=cost_usd,
                evidence=evidence,
                timestamp=datetime.now(timezone.utc),
            )
        )
        return tid

    async def save_snapshot(self, status: str, last_completed: str, next_action: str) -> None:
        await self.client.post(
            "/v1/snapshots",
            json={
                "tenant_id": self.settings.tenant_id,
                "status": status,
                "last_completed": last_completed,
                "next_action": next_action,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def close(self) -> None:
        await self.client.aclose()
