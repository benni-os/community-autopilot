"""Webhook server for real-time GitHub events."""

import hashlib
import hmac
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel

from .analyzer import Analyzer
from .config import Settings
from .models import Comment, Issue, IssueState
from .nemesis import NemesisClient
from .responder import Responder
from .slack import SlackNotifier

app = FastAPI(
    title="Benni OS Community Autopilot Webhook",
    description="Real-time GitHub Webhook receiver for autonomous issue triage",
    version="0.2.0",
)


def verify_signature(secret: str, body: bytes, signature_header: str | None) -> bool:
    """Verifies GitHub HMAC-SHA256 signature."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected_hash = signature_header[len("sha256=") :]
    mac = hmac.new(secret.encode(), msg=body, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), expected_hash)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service="community-autopilot",
        version="0.2.0",
        timestamp=datetime.now(UTC).isoformat(),
    )


@app.get("/ready")
async def readiness_check() -> dict[str, str]:
    return {"status": "ready"}


@app.post("/webhook")
async def handle_webhook(
    request: Request,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
) -> dict[str, Any]:
    body_bytes = await request.body()
    settings = Settings()

    # Verify signature if secret configured
    if settings.webhook_secret:
        if not verify_signature(settings.webhook_secret, body_bytes, x_hub_signature_256):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid GitHub webhook signature",
            )

    payload = await request.json()

    if x_github_event == "ping":
        return {
            "status": "ok",
            "message": "pong",
            "zen": payload.get("zen", ""),
            "hook_id": payload.get("hook_id"),
        }

    if x_github_event == "issues":
        action = payload.get("action")
        if action in {"opened", "reopened"}:
            return await _process_issue_event(payload, settings)
        return {"status": "ignored", "action": action, "reason": "unhandled issue action"}

    if x_github_event == "issue_comment":
        action = payload.get("action")
        if action == "created":
            return await _process_comment_event(payload, settings)
        return {"status": "ignored", "action": action, "reason": "unhandled comment action"}

    return {"status": "ignored", "event": x_github_event}


async def _process_issue_event(payload: dict[str, Any], settings: Settings) -> dict[str, Any]:
    issue_data = payload.get("issue", {})
    repo_data = payload.get("repository", {})
    repo_name = repo_data.get("name", "")
    author_login = issue_data.get("user", {}).get("login", "")

    if author_login in settings.maintainer_logins:
        return {"status": "skipped", "reason": "issue created by maintainer"}

    created_at = datetime.fromisoformat(
        issue_data.get("created_at", datetime.now(UTC).isoformat()).replace("Z", "+00:00")
    )
    issue = Issue(
        number=issue_data.get("number", 0),
        repo=repo_name,
        title=issue_data.get("title", ""),
        body=issue_data.get("body") or "",
        state=IssueState.OPEN,
        author=author_login,
        labels=[lbl.get("name", "") for lbl in issue_data.get("labels", [])],
        comments=[],
        created_at=created_at,
        updated_at=created_at,
        html_url=issue_data.get("html_url", ""),
        assignees=[a.get("login", "") for a in issue_data.get("assignees", [])],
    )

    nemesis = NemesisClient(settings)
    analyzer = Analyzer(settings, nemesis)
    responder = Responder(settings, nemesis)
    slack = SlackNotifier(settings)

    try:
        draft = await analyzer.analyze(issue)
        result: dict[str, Any] = {
            "status": "processed",
            "issue_number": issue.number,
            "repo": issue.repo,
            "priority": draft.priority.value,
            "trace_id": draft.trace_id,
        }

        if draft.requires_approval or settings.dry_run:
            await slack.notify_pending_draft(draft)
            result["action"] = "approval_pending"
            result["draft"] = draft.draft_body
        else:
            comment_url = await responder.post(draft)
            result["action"] = "comment_posted"
            result["comment_url"] = comment_url

        return result
    finally:
        await nemesis.close()
        await responder.close()


async def _process_comment_event(payload: dict[str, Any], settings: Settings) -> dict[str, Any]:
    comment_data = payload.get("comment", {})
    issue_data = payload.get("issue", {})
    repo_data = payload.get("repository", {})
    author_login = comment_data.get("user", {}).get("login", "")

    if author_login in settings.maintainer_logins:
        return {"status": "skipped", "reason": "comment from maintainer"}

    created_at = datetime.fromisoformat(
        issue_data.get("created_at", datetime.now(UTC).isoformat()).replace("Z", "+00:00")
    )
    comment_created = datetime.fromisoformat(
        comment_data.get("created_at", datetime.now(UTC).isoformat()).replace("Z", "+00:00")
    )

    comment = Comment(
        id=comment_data.get("id", 0),
        author=author_login,
        body=comment_data.get("body", ""),
        created_at=comment_created,
        is_maintainer=False,
        html_url=comment_data.get("html_url", ""),
    )

    issue = Issue(
        number=issue_data.get("number", 0),
        repo=repo_data.get("name", ""),
        title=issue_data.get("title", ""),
        body=issue_data.get("body") or "",
        state=IssueState.OPEN,
        author=issue_data.get("user", {}).get("login", ""),
        labels=[lbl.get("name", "") for lbl in issue_data.get("labels", [])],
        comments=[comment],
        created_at=created_at,
        updated_at=comment_created,
        html_url=issue_data.get("html_url", ""),
        assignees=[a.get("login", "") for a in issue_data.get("assignees", [])],
    )

    nemesis = NemesisClient(settings)
    analyzer = Analyzer(settings, nemesis)
    responder = Responder(settings, nemesis)
    slack = SlackNotifier(settings)

    try:
        draft = await analyzer.analyze(issue)
        result: dict[str, Any] = {
            "status": "processed",
            "issue_number": issue.number,
            "repo": issue.repo,
            "priority": draft.priority.value,
            "trace_id": draft.trace_id,
        }

        if draft.requires_approval or settings.dry_run:
            await slack.notify_pending_draft(draft)
            result["action"] = "approval_pending"
        else:
            comment_url = await responder.post(draft)
            result["action"] = "comment_posted"
            result["comment_url"] = comment_url

        return result
    finally:
        await nemesis.close()
        await responder.close()
