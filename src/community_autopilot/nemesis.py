"""NEMESIS Event Bus client — every action must have trace_id, tenant_id, objective, cost, evidence."""

import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field

from .config import Settings


class NemesisEvent(BaseModel):
    trace_id: str
    tenant_id: str
    event_type: str
    objective: str
    cost_usd: float
    evidence: dict[str, Any]
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class NemesisClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        headers: dict[str, str] = {}
        if settings.nemesis_api_key:
            headers["Authorization"] = f"Bearer {settings.nemesis_api_key}"

        self.client = httpx.AsyncClient(
            base_url=settings.nemesis_url,
            headers=headers,
            timeout=30.0,
            follow_redirects=True,
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
                timestamp=datetime.now(UTC),
            )
        )
        return tid

    async def save_snapshot(self, status: str, last_completed: str, next_action: str) -> None:
        try:
            await self.client.post(
                "/v1/snapshots",
                json={
                    "tenant_id": self.settings.tenant_id,
                    "status": status,
                    "last_completed": last_completed,
                    "next_action": next_action,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            )
        except Exception as exc:
            print(f"[NEMESIS] Failed to save snapshot: {exc}")

    async def close(self) -> None:
        await self.client.aclose()

    async def __aenter__(self) -> "NemesisClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()
