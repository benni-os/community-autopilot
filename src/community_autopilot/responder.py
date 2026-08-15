"""Responder — posts approved drafts to GitHub issues."""

import httpx

from .config import Settings
from .models import DraftResponse
from .nemesis import NemesisClient


class Responder:
    def __init__(self, settings: Settings, nemesis: NemesisClient) -> None:
        self.settings = settings
        self.nemesis = nemesis
        self.client = httpx.AsyncClient(
            base_url="https://api.github.com",
            headers={
                "Authorization": f"Bearer {settings.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    async def post(self, draft: DraftResponse) -> str:
        if self.settings.dry_run:
            print(f"[DRY RUN] Would post to {draft.issue.html_url}:\n{draft.draft_body}")
            return "dry-run://skipped"

        resp = await self.client.post(
            f"/repos/{self.settings.github_org}/{draft.issue.repo}/issues/{draft.issue.number}/comments",
            json={"body": draft.draft_body},
        )
        resp.raise_for_status()
        comment_url = resp.json()["html_url"]

        await self.nemesis.log_action(
            event_type="responder.comment_posted",
            objective=f"Respond to issue #{draft.issue.number} in {draft.issue.repo}",
            cost_usd=0.01,
            evidence={
                "issue_url": draft.issue.html_url,
                "comment_url": comment_url,
                "priority": draft.priority.value,
            },
            trace_id=draft.trace_id,
        )
        return comment_url

    async def close(self) -> None:
        await self.client.aclose()
