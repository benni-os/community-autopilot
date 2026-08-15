"""Tests for CLI commands."""

import pytest
from typer.testing import CliRunner
from community_autopilot.cli import app

runner = CliRunner()


def test_scan_help():
    result = runner.invoke(app, ["scan", "--help"])
    assert result.exit_code == 0
    assert "--dry-run" in result.stdout


def test_run_help():
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "--max" in result.stdout


@pytest.mark.asyncio
async def test_scan_dry_run(settings, httpx_mock):
    httpx_mock.add_response(
        url=f"https://api.github.com/repos/{settings.github_org}/mcp-forge/issues",
        status_code=200,
        json=[],
    )
    result = runner.invoke(app, ["scan", "--dry-run"])
    assert result.exit_code == 0
