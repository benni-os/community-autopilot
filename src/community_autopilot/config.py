"""Configuration module with Pydantic Settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # GitHub
    github_token: str = Field(default="")
    github_org: str = "benni-os"
    watched_repos: list[str] = Field(
        default_factory=lambda: ["mcp-forge", "benni-nexus", "benni-os"]
    )
    maintainer_logins: list[str] = Field(
        default_factory=lambda: ["BenniAlencar", "benni-os", "benni-bot"]
    )

    # NEMESIS
    nemesis_url: str = "https://nemesis.benni.os"
    nemesis_api_key: str = Field(default="")
    tenant_id: str = "benni-os"

    # LLM (via NEMESIS Nexus)
    llm_model: str = "claude-sonnet-4-20250514"
    llm_max_tokens: int = 1024

    # Slack
    slack_webhook_url: str | None = None
    slack_channel: str = "#community"

    # Webhook server
    webhook_host: str = "0.0.0.0"
    webhook_port: int = 8000
    webhook_secret: str | None = None

    # Timing
    poll_interval_hours: int = 6
    stale_threshold_hours: int = 48
    first_response_sla_hours: int = 6

    # Safety
    dry_run: bool = False
    require_approval: bool = True
    max_comments_per_run: int = 10
