"""Typer CLI — entry point for local runs, GitHub Actions, and Webhook server."""

import asyncio
from datetime import UTC, datetime

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .analyzer import Analyzer
from .config import Settings
from .models import AutopilotRun, IssueState, Priority
from .nemesis import NemesisClient
from .responder import Responder
from .slack import SlackNotifier
from .watcher import GitHubWatcher

app = typer.Typer(name="autopilot", help="Benni OS Community Autopilot")
console = Console()


@app.command()
def scan(
    dry_run: bool = typer.Option(False, "--dry-run", help="Don't post, just print drafts"),
    repo: str | None = typer.Option(None, "--repo", help="Scan a single repo"),
) -> None:
    """Scan repositories for unanswered issues and generate drafts."""
    asyncio.run(_scan(dry_run=dry_run, repo=repo))


@app.command()
def run(
    dry_run: bool = typer.Option(False, "--dry-run", help="Run in simulation mode without posting"),
    max_comments: int = typer.Option(10, "--max", help="Maximum comments to post per run"),
    repo: str | None = typer.Option(None, "--repo", help="Filter run to a single repo"),
) -> None:
    """Execute autonomous triage run: scan, draft, post or hold for approval."""
    asyncio.run(_run(dry_run=dry_run, max_comments=max_comments, repo=repo))


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", help="Host interface to bind"),
    port: int = typer.Option(8000, "--port", help="Port to listen on"),
) -> None:
    """Run real-time GitHub Webhook server."""
    import uvicorn

    console.print(f"[bold green]Starting Community Autopilot Webhook on {host}:{port}...[/bold green]")
    uvicorn.run("community_autopilot.webhook:app", host=host, port=port, reload=False)


@app.command()
def health() -> None:
    """Validate system configuration, GitHub token, NEMESIS and Slack connectivity."""
    asyncio.run(_health())


@app.command()
def approve(
    repo: str = typer.Option(..., "--repo", help="Repository name"),
    issue_number: int = typer.Option(..., "--issue", help="Issue number"),
    message: str | None = typer.Option(None, "--message", help="Optional custom response text"),
) -> None:
    """Explicitly approve and post a response to an issue."""
    asyncio.run(_approve(repo=repo, issue_number=issue_number, message=message))


async def _scan(dry_run: bool, repo: str | None) -> None:
    settings = Settings()
    if dry_run:
        settings.dry_run = True
    if repo:
        settings.watched_repos = [repo]

    nemesis = NemesisClient(settings)
    watcher = GitHubWatcher(settings, nemesis)
    analyzer = Analyzer(settings, nemesis)

    try:
        issues = await watcher.scan_all()
        table = Table(title=f"Unanswered Issues ({len(issues)})")
        table.add_column("Repo", style="cyan")
        table.add_column("#", style="bold")
        table.add_column("Title")
        table.add_column("Priority")
        table.add_column("Last Author")

        for issue in issues:
            draft = await analyzer.analyze(issue)
            last_author = issue.comments[-1].author if issue.comments else "—"
            color = {
                "critical": "red",
                "high": "yellow",
                "medium": "cyan",
                "low": "dim",
            }[draft.priority.value]
            table.add_row(
                issue.repo,
                str(issue.number),
                issue.title[:50],
                f"[{color}]{draft.priority.value}[/{color}]",
                last_author,
            )
            console.print(f"\n[bold]Draft for #{issue.number} ({issue.repo}):[/bold]\n{draft.draft_body}\n")

        console.print(table)
    finally:
        await watcher.close()
        await nemesis.close()


async def _run(dry_run: bool, max_comments: int, repo: str | None = None) -> None:
    settings = Settings()
    settings.dry_run = dry_run
    settings.max_comments_per_run = max_comments
    if repo:
        settings.watched_repos = [repo]

    run_meta = AutopilotRun(
        run_id=f"run-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}",
        started_at=datetime.now(UTC),
    )

    nemesis = NemesisClient(settings)
    watcher = GitHubWatcher(settings, nemesis)
    analyzer = Analyzer(settings, nemesis)
    responder = Responder(settings, nemesis)
    slack = SlackNotifier(settings)

    try:
        issues = await watcher.scan_all()
        run_meta.issues_scanned = len(issues)

        drafts = []
        for issue in issues:
            try:
                draft = await analyzer.analyze(issue)
                drafts.append(draft)
            except Exception as exc:
                err_msg = f"Failed to analyze #{issue.number} ({issue.repo}): {exc}"
                console.print(f"[red]{err_msg}[/red]")
                run_meta.errors.append(err_msg)

        drafts.sort(key=lambda d: list(Priority).index(d.priority))

        posted = 0
        for draft in drafts:
            if posted >= max_comments:
                run_meta.drafts_pending += 1
                continue
            if draft.requires_approval and not dry_run:
                console.print(
                    f"[yellow]⚠ Approval required for #{draft.issue.number} ({draft.issue.repo}) — skipping[/yellow]"
                )
                await slack.notify_pending_draft(draft)
                run_meta.drafts_pending += 1
                continue

            try:
                url = await responder.post(draft)
                run_meta.comments_posted += 1
                run_meta.evidence.append(url)
                posted += 1
            except Exception as exc:
                err_msg = f"Failed to post to #{draft.issue.number}: {exc}"
                console.print(f"[red]{err_msg}[/red]")
                run_meta.errors.append(err_msg)

        run_meta.finished_at = datetime.now(UTC)
        run_meta.cost_usd = posted * 0.01 + run_meta.issues_scanned * 0.001

        await nemesis.save_snapshot(
            status="completed" if not run_meta.errors else "partial",
            last_completed=f"Posted {run_meta.comments_posted} comments, {run_meta.drafts_pending} pending approval",
            next_action="Wait for next cron cycle or manual scan",
        )

        await slack.notify_run_summary(run_meta)

        console.print(f"\n[green]✓ Run {run_meta.run_id} complete[/green]")
        console.print(
            f"  Scanned: {run_meta.issues_scanned} | Posted: {run_meta.comments_posted} | Pending: {run_meta.drafts_pending}"
        )
        if run_meta.errors:
            console.print(f"  [red]Errors ({len(run_meta.errors)}):[/red] {run_meta.errors[0]}")

    finally:
        await watcher.close()
        await responder.close()
        await nemesis.close()


async def _health() -> None:
    settings = Settings()
    table = Table(title="System Health & Pre-flight Diagnostics")
    table.add_column("Component", style="cyan")
    table.add_column("Configured", style="bold")
    table.add_column("Status / Details")

    # GitHub
    gh_configured = bool(settings.github_token)
    table.add_row(
        "GitHub Token",
        "[green]YES[/green]" if gh_configured else "[red]NO[/red]",
        f"Org: {settings.github_org} | Watched: {len(settings.watched_repos)} repos",
    )

    # NEMESIS
    nemesis_configured = bool(settings.nemesis_api_key)
    table.add_row(
        "NEMESIS Nexus",
        "[green]YES[/green]" if nemesis_configured else "[yellow]OFFLINE / FALLBACK[/yellow]",
        f"URL: {settings.nemesis_url} | Tenant: {settings.tenant_id}",
    )

    # Slack
    slack_configured = bool(settings.slack_webhook_url)
    table.add_row(
        "Slack Webhook",
        "[green]YES[/green]" if slack_configured else "[dim]DISABLED[/dim]",
        f"Channel: {settings.slack_channel}",
    )

    # Webhook Server
    table.add_row(
        "Webhook Receiver",
        "[green]READY[/green]",
        f"Host: {settings.webhook_host}:{settings.webhook_port} (Secret: {'SET' if settings.webhook_secret else 'NONE'})",
    )

    console.print(table)


async def _approve(repo: str, issue_number: int, message: str | None) -> None:
    settings = Settings()
    nemesis = NemesisClient(settings)
    analyzer = Analyzer(settings, nemesis)
    responder = Responder(settings, nemesis)

    try:
        headers = {
            "Authorization": f"Bearer {settings.github_token}",
            "Accept": "application/vnd.github+json",
        }
        async with httpx.AsyncClient(base_url="https://api.github.com", headers=headers, timeout=30.0) as client:
            resp = await client.get(f"/repos/{settings.github_org}/{repo}/issues/{issue_number}")
            resp.raise_for_status()
            data = resp.json()
        # Construct issue
        from .models import Issue
        parsed_issue = Issue(
            number=data["number"],
            repo=repo,
            title=data["title"],
            body=data.get("body") or "",
            state=IssueState.OPEN,
            author=data["user"]["login"],
            labels=[lbl["name"] for lbl in data.get("labels", [])],
            comments=[],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
            html_url=data["html_url"],
            assignees=[a["login"] for a in data.get("assignees", [])],
        )

        draft = await analyzer.analyze(parsed_issue)
        if message:
            draft.draft_body = message

        console.print(Panel(draft.draft_body, title=f"Posting Approved Comment to #{issue_number} ({repo})"))
        url = await responder.post(draft)
        console.print(f"[green]✓ Comment posted successfully: {url}[/green]")
    finally:
        await responder.close()
        await nemesis.close()


if __name__ == "__main__":
    app()
