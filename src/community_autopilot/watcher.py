"""GitHub issue watcher — polls all watched repos for unanswered activity."""

from datetime import datetime, timezone, timedelta

import httpx

from .config import Settings
from .models import Issue, Comment, IssueState
from .nemesis import NemesisClient


MAINTAINER_LOGINS = {"BenniAlencar", "benni-os", "benni-bot"}


class GitHubWatcher:
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

    async def scan_all(self) -> list[Issue]:
        all_issues: list[Issue] = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.settings.stale_threshold_hours)

        for repo in self.settings.watched_repos:
            issues = await self._fetch_open_issues(repo)
            for issue in issues:
                comments = await self._fetch_comments(repo, issue.number)
                issue.comments = comments
                if self._needs_attention(issue, cutoff):
                    all_issues.append(issue)

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
        return [
            Issue(
                number=item["number"],
                repo=repo,
                title=item["title"],
                body=item.get("body") or "",
                state=IssueState.OPEN,
                author=item["user"]["login"],
                labels=[lbl["name"] for lbl in item.get("labels", [])],
                comments=[],
                created_at=datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00")),
                html_url=item["html_url"],
                assignees=[a["login"] for a in item.get("assignees", [])],
            )
            for item in resp.json()
            if "pull_request" not in item
        ]

    async def _fetch_comments(self, repo: str, issue_number: int) -> list[Comment]:
        resp = await self.client.get(
            f"/repos/{self.settings.github_org}/{repo}/issues/{issue_number}/comments",
            params={"per_page": 100},
        )
        resp.raise_for_status()
        return [
            Comment(
                id=c["id"],
                author=c["user"]["login"],
                body=c["body"],
                created_at=datetime.fromisoformat(c["created_at"].replace("Z", "+00:00")),
                is_maintainer=c["user"]["login"] in MAINTAINER_LOGINS,
                html_url=c["html_url"],
            )
            for c in resp.json()
        ]

    def _needs_attention(self, issue: Issue, cutoff: datetime) -> bool:
        if not issue.comments:
            return issue.created_at < cutoff
        last = issue.comments[-1]
        return not last.is_maintainer and last.created_at < cutoff

    async def close(self) -> None:
        await self.client.aclose()
