"""Slack notifier module for Community Autopilot."""

import httpx

from .config import Settings
from .models import AutopilotRun, DraftResponse


class SlackNotifier:
    """Sends notifications to Slack via Incoming Webhooks."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def notify_run_summary(self, run: AutopilotRun) -> bool:
        """Sends an operational summary of an Autopilot run."""
        if not self.settings.slack_webhook_url:
            return False

        status_emoji = ":white_check_mark:" if not run.errors else ":warning:"
        text = (
            f"{status_emoji} *Autopilot Run Finished* (`{run.run_id}`)\n"
            f"• *Scanned:* {run.issues_scanned} issues\n"
            f"• *Posted:* {run.comments_posted} comments\n"
            f"• *Pending Approval:* {run.drafts_pending} drafts\n"
            f"• *Cost:* ${run.cost_usd:.4f} USD\n"
        )
        if run.errors:
            text += f"• *Errors:* {len(run.errors)} ({', '.join(run.errors[:3])})\n"

        payload = {
            "channel": self.settings.slack_channel,
            "text": text,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.post(self.settings.slack_webhook_url, json=payload)
                return resp.status_code == 200
        except Exception as exc:
            print(f"[SLACK] Failed to send run summary: {exc}")
            return False

    async def notify_pending_draft(self, draft: DraftResponse) -> bool:
        """Alerts maintainers that a draft requires review and approval."""
        if not self.settings.slack_webhook_url:
            return False

        priority_emoji = {
            "critical": ":rotating_light:",
            "high": ":warning:",
            "medium": ":information_source:",
            "low": ":speech_balloon:",
        }.get(draft.priority.value, ":speech_balloon:")

        text = (
            f"{priority_emoji} *Draft Requires Approval*\n"
            f"• *Repo:* `{draft.issue.repo}`\n"
            f"• *Issue:* <{draft.issue.html_url}|#{draft.issue.number} {draft.issue.title}>\n"
            f"• *Priority:* `{draft.priority.value.upper()}`\n"
            f"• *Author:* @{draft.issue.author}\n"
            f"• *Reasoning:* {draft.reasoning}\n\n"
            f"*Proposed Response:*\n```{draft.draft_body[:500]}```"
        )

        payload = {
            "channel": self.settings.slack_channel,
            "text": text,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.post(self.settings.slack_webhook_url, json=payload)
                return resp.status_code == 200
        except Exception as exc:
            print(f"[SLACK] Failed to send pending draft alert: {exc}")
            return False
