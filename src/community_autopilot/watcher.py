"""GitHub issue watcher — polls all watched repos for unanswered activity."""

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from .config import Settings
from .models import Comment, Issue, IssueState
from .nemesis import NemesisClient

MAINTAINER_LOGINS = {"BenniAlencar", "benni-os", "benni-bot"}


class GitHubWatcher:
    def __init__(self, settings: Settings, nemesis: NemesisClient | None = None) -> None:
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

    async def scan_all(self) -> list[Issue]:
        all_issues: list[Issue] = []
        cutoff = datetime.now(UTC) - timedelta(hours=self.settings.stale_threshold_hours)

        for repo in self.settings.watched_repos:
            issues = await self._fetch_open_issues(repo)
            for issue in issues:
                comments = await self._fetch_comments(repo, issue.number)
                issue.comments = comments
                if self._needs_attention(issue, cutoff):
                    all_issues.append(issue)

        if self.nemesis:
            await self.nemesis.log_action(
                event_type="watcher.scan_complete",
                objective="Scan all repos for unanswered issues",
                cost_usd=0.001,
                evidence={"repos": self.settings.watched_repos, "issues_found": len(all_issues)},
            )
        return all_issues

    async def _fetch_open_issues(self, repo: str) -> list[Issue]:
        resp = await self.client.get(
            f"/repos/{self.settings.github_org}/{repo}/issues",
            params={"state": "open", "per_page": 100, "sort": "updated", "direction": "desc"},
        )
        resp.raise_for_status()
        items = resp.json()
        if not isinstance(items, list):
            return []

        return [
            Issue(
                number=item["number"],
                repo=repo,
                title=item["title"],
                body=item.get("body") or "",
                state=IssueState.OPEN,
                author=item["user"]["login"],
                labels=[
                    lbl["name"] if isinstance(lbl, dict) else str(lbl)
                    for lbl in item.get("labels", [])
                ],
                comments=[],
                created_at=datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00")),
                html_url=item["html_url"],
                assignees=[
                    a["login"] if isinstance(a, dict) else str(a)
                    for a in item.get("assignees", [])
                ],
            )
            for item in items
            if "pull_request" not in item
        ]

    async def _fetch_comments(self, repo: str, issue_number: int) -> list[Comment]:
        resp = await self.client.get(
            f"/repos/{self.settings.github_org}/{repo}/issues/{issue_number}/comments",
            params={"per_page": 100},
        )
        resp.raise_for_status()
        items = resp.json()
        if not isinstance(items, list):
            return []

        maintainers = set(self.settings.maintainer_logins).union(MAINTAINER_LOGINS)
        return [
            Comment(
                id=c["id"],
                author=c["user"]["login"],
                body=c["body"],
                created_at=datetime.fromisoformat(c["created_at"].replace("Z", "+00:00")),
                is_maintainer=c["user"]["login"] in maintainers,
                html_url=c["html_url"],
            )
            for c in items
        ]

    def _needs_attention(self, issue: Issue, cutoff: datetime) -> bool:
        if not issue.comments:
            return issue.created_at < cutoff
        last = issue.comments[-1]
        return not last.is_maintainer and last.created_at < cutoff

    async def close(self) -> None:
        await self.client.aclose()

    async def __aenter__(self) -> "GitHubWatcher":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()
