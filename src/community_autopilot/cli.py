"""Typer CLI — entry point for local runs and GitHub Actions."""

import asyncio
from datetime import datetime, timezone

import typer
from rich.console import Console
from rich.table import Table

from .config import Settings
from .models import AutopilotRun, Priority
from .nemesis import NemesisClient
from .watcher import GitHubWatcher
from .analyzer import Analyzer
from .responder import Responder

app = typer.Typer(name="autopilot", help="Benni OS Community Autopilot")
console = Console()


@app.command()
def scan(
    dry_run: bool = typer.Option(False, "--dry-run", help="Don't post, just print drafts"),
    repo: str | None = typer.Option(None, "--repo", help="Scan a single repo"),
) -> None:
    asyncio.run(_scan(dry_run=dry_run, repo=repo))


@app.command()
def run(
    dry_run: bool = typer.Option(False, "--dry-run"),
    max_comments: int = typer.Option(10, "--max"),
) -> None:
    asyncio.run(_run(dry_run=dry_run, max_comments=max_comments))


async def _scan(dry_run: bool, repo: str | None) -> None:
    settings = Settings()
    if dry_run:
        settings.dry_run = True
    if repo:
        settings.watched_repos = [repo]

    nemesis = NemesisClient(settings)
    watcher = GitHubWatcher(settings, nemesis)
    analyzer = Analyzer(settings, nemesis)

    issues = await watcher.scan_all()
    table = Table(title=f"Unanswered Issues ({len(issues)})")
    table.add_column("Repo")
    table.add_column("#")
    table.add_column("Title")
    table.add_column("Priority")
    table.add_column("Last Author")

    for issue in issues:
        draft = await analyzer.analyze(issue)
        last_author = issue.comments[-1].author if issue.comments else "—"
        color = {"critical": "red", "high": "yellow", "medium": "cyan", "low": "dim"}[draft.priority.value]
        table.add_row(issue.repo, str(issue.number), issue.title[:50], f"[{color}]{draft.priority.value}[/{color}]", last_author)
        console.print(f"\n[bold]Draft for #{issue.number}:[/bold]\n{draft.draft_body}\n")

    console.print(table)
    await watcher.close()
    await nemesis.close()


async def _run(dry_run: bool, max_comments: int) -> None:
    settings = Settings()
    settings.dry_run = dry_run
    settings.max_comments_per_run = max_comments

    run = AutopilotRun(
        run_id=f"run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        started_at=datetime.now(timezone.utc),
    )

    nemesis = NemesisClient(settings)
    watcher = GitHubWatcher(settings, nemesis)
    analyzer = Analyzer(settings, nemesis)
    responder = Responder(settings, nemesis)

    try:
        issues = await watcher.scan_all()
        run.issues_scanned = len(issues)

        drafts = []
        for issue in issues:
            draft = await analyzer.analyze(issue)
            drafts.append(draft)

        drafts.sort(key=lambda d: list(Priority).index(d.priority))

        posted = 0
        for draft in drafts:
            if posted >= max_comments:
                run.drafts_pending += 1
                continue
            if draft.requires_approval and not dry_run:
                console.print(f"[yellow]⚠ Approval required for #{draft.issue.number} — skipping (use --dry-run to preview)[/yellow]")
                run.drafts_pending += 1
                continue
            url = await responder.post(draft)
            run.comments_posted += 1
            run.evidence.append(url)
            posted += 1

        run.finished_at = datetime.now(timezone.utc)
        run.cost_usd = posted * 0.01 + run.issues_scanned * 0.001

        await nemesis.save_snapshot(
            status="completed" if not run.errors else "partial",
            last_completed=f"Posted {run.comments_posted} comments, {run.drafts_pending} pending approval",
            next_action="Wait for next cron cycle or manual scan",
        )

        console.print(f"\n[green]✓ Run {run.run_id} complete[/green]")
        console.print(f"  Scanned: {run.issues_scanned} | Posted: {run.comments_posted} | Pending: {run.drafts_pending}")

    finally:
        await watcher.close()
        await responder.close()
        await nemesis.close()


if __name__ == "__main__":
    app()
