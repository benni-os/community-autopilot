"""Priority analyzer — ranks issues by urgency and generates context for the LLM."""

from datetime import datetime, timezone, timedelta

from .config import Settings
from .models import Issue, Priority, DraftResponse
from .nemesis import NemesisClient
from .prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


class Analyzer:
    def __init__(self, settings: Settings, nemesis: NemesisClient) -> None:
        self.settings = settings
        self.nemesis = nemesis

    def prioritize(self, issue: Issue) -> Priority:
        now = datetime.now(timezone.utc)
        hours_since_update = (now - issue.updated_at).total_seconds() / 3600
        has_external_comment = any(not c.is_maintainer for c in issue.comments)
        is_good_first = "good first issue" in issue.labels

        if has_external_comment and hours_since_update > 48:
            return Priority.CRITICAL
        if has_external_comment and hours_since_update > self.settings.first_response_sla_hours:
            return Priority.HIGH
        if is_good_first and not issue.assignees and hours_since_update > 168:
            return Priority.MEDIUM
        return Priority.LOW

    def build_context(self, issue: Issue) -> str:
        comments_block = "\n".join(
            f"- @{c.author} ({'maintainer' if c.is_maintainer else 'contributor'}) "
            f"[{c.created_at.isoformat()}]: {c.body[:500]}"
            for c in issue.comments
        )
        return USER_PROMPT_TEMPLATE.format(
            repo=issue.repo,
            number=issue.number,
            title=issue.title,
            body=issue.body[:2000],
            labels=", ".join(issue.labels) or "none",
            author=issue.author,
            comments=comments_block or "(no comments yet)",
            url=issue.html_url,
        )

    async def analyze(self, issue: Issue) -> DraftResponse:
        priority = self.prioritize(issue)
        context = self.build_context(issue)
        trace_id = self.nemesis.new_trace_id()
        draft_body = await self._generate_draft(context, trace_id)

        return DraftResponse(
            issue=issue,
            priority=priority,
            draft_body=draft_body,
            reasoning=f"Priority={priority.value}, comments={len(issue.comments)}, "
                      f"last_author={issue.comments[-1].author if issue.comments else 'none'}",
            requires_approval=self.settings.require_approval or priority in {Priority.CRITICAL, Priority.HIGH},
            estimated_tokens=len(draft_body.split()) * 2,
            trace_id=trace_id,
        )

    async def _generate_draft(self, context: str, trace_id: str) -> str:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.settings.nemesis_url}/v1/nexus/inference",
                headers={"Authorization": f"Bearer {self.settings.nemesis_api_key}"},
                json={
                    "model": self.settings.llm_model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": context},
                    ],
                    "max_tokens": self.settings.llm_max_tokens,
                    "trace_id": trace_id,
                    "tenant_id": self.settings.tenant_id,
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
