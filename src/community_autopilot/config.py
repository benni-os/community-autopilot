"""Configuration module with Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # GitHub
    github_token: str
    github_org: str = "benni-os"
    watched_repos: list[str] = Field(default=["mcp-forge", "benni-nexus", "benni-os"])

    # NEMESIS
    nemesis_url: str = "https://nemesis.benni.os"
    nemesis_api_key: str
    tenant_id: str = "benni-os"

    # LLM (via NEMESIS Nexus)
    llm_model: str = "claude-sonnet-4-20250514"
    llm_max_tokens: int = 1024

    # Slack
    slack_webhook_url: str | None = None
    slack_channel: str = "#community"

    # Timing
    poll_interval_hours: int = 6
    stale_threshold_hours: int = 48
    first_response_sla_hours: int = 6

    # Safety
    dry_run: bool = False
    require_approval: bool = True
    max_comments_per_run: int = 10
