"""Tests for Webhook server."""

import hashlib
import hmac
import json

from pytest_httpx import HTTPXMock
from starlette.testclient import TestClient

from community_autopilot.config import Settings
from community_autopilot.webhook import app, verify_signature

client = TestClient(app)


def test_verify_signature() -> None:
    secret = "secret123"
    body = b'{"hello": "world"}'
    valid_hash = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    assert verify_signature(secret, body, f"sha256={valid_hash}") is True
    assert verify_signature(secret, body, "sha256=invalid") is False
    assert verify_signature(secret, body, None) is False


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "community-autopilot"


def test_readiness_endpoint() -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_webhook_ping() -> None:
    payload = {"zen": "Keep it logically awesome.", "hook_id": 12345}
    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(b"test_secret", body, hashlib.sha256).hexdigest()

    response = client.post(
        "/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "ping",
            "X-Hub-Signature-256": signature,
        },
    )
    assert response.status_code == 200
    assert response.json()["message"] == "pong"


def test_webhook_invalid_signature() -> None:
    response = client.post(
        "/webhook",
        json={"zen": "fail"},
        headers={
            "X-GitHub-Event": "ping",
            "X-Hub-Signature-256": "sha256=bad_sig",
        },
    )
    assert response.status_code == 401


def test_webhook_unhandled_event() -> None:
    payload = {"action": "created"}
    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(b"test_secret", body, hashlib.sha256).hexdigest()

    response = client.post(
        "/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "push",
            "X-Hub-Signature-256": signature,
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


def test_webhook_issue_maintainer(settings: Settings) -> None:
    payload = {
        "action": "opened",
        "repository": {"name": "mcp-forge"},
        "issue": {
            "number": 55,
            "title": "Maintainer issue",
            "user": {"login": "benni-bot"},
        },
    }
    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(b"test_secret", body, hashlib.sha256).hexdigest()

    response = client.post(
        "/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": signature,
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "skipped"


def test_webhook_issue_external_draft(settings: Settings, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{settings.nemesis_url}/v1/nexus/inference",
        status_code=200,
        json={"choices": [{"message": {"content": "We will check this shortly."}}]},
    )
    if settings.slack_webhook_url:
        httpx_mock.add_response(url=settings.slack_webhook_url, status_code=200)

    payload = {
        "action": "opened",
        "repository": {"name": "mcp-forge"},
        "issue": {
            "number": 56,
            "title": "External contribution issue",
            "body": "How do I configure this?",
            "user": {"login": "new-contributor"},
            "labels": [{"name": "question"}],
            "html_url": "https://github.com/benni-os/mcp-forge/issues/56",
            "created_at": "2026-08-15T10:00:00Z",
            "assignees": [],
        },
    }
    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(b"test_secret", body, hashlib.sha256).hexdigest()

    response = client.post(
        "/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": signature,
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    assert response.json()["action"] == "approval_pending"


def test_webhook_comment_external(settings: Settings, httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=f"{settings.nemesis_url}/v1/nexus/inference",
        status_code=200,
        json={"choices": [{"message": {"content": "Thank you for the update!"}}]},
    )
    if settings.slack_webhook_url:
        httpx_mock.add_response(url=settings.slack_webhook_url, status_code=200)

    payload = {
        "action": "created",
        "repository": {"name": "mcp-forge"},
        "issue": {
            "number": 57,
            "title": "Issue with comment",
            "body": "Issue description",
            "user": {"login": "someone"},
            "labels": [],
            "html_url": "https://github.com/benni-os/mcp-forge/issues/57",
            "created_at": "2026-08-15T10:00:00Z",
            "assignees": [],
        },
        "comment": {
            "id": 888,
            "body": "Here is more info",
            "user": {"login": "external-contributor"},
            "html_url": "https://github.com/benni-os/mcp-forge/issues/57#issuecomment-888",
            "created_at": "2026-08-15T11:00:00Z",
        },
    }
    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(b"test_secret", body, hashlib.sha256).hexdigest()

    response = client.post(
        "/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "issue_comment",
            "X-Hub-Signature-256": signature,
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "processed"


def test_webhook_comment_maintainer(settings: Settings) -> None:
    payload = {
        "action": "created",
        "repository": {"name": "mcp-forge"},
        "issue": {"number": 58, "user": {"login": "user1"}},
        "comment": {"id": 889, "body": "maintainer note", "user": {"login": "BenniAlencar"}},
    }
    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(b"test_secret", body, hashlib.sha256).hexdigest()

    response = client.post(
        "/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "issue_comment",
            "X-Hub-Signature-256": signature,
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "skipped"
