"""Domain models for Issues, Comments, and Autopilot runs."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueState(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class Comment(BaseModel):
    id: int
    author: str
    body: str
    created_at: datetime
    is_maintainer: bool
    html_url: str


class Issue(BaseModel):
    number: int
    repo: str
    title: str
    body: str
    state: IssueState
    author: str
    labels: list[str]
    comments: list[Comment]
    created_at: datetime
    updated_at: datetime
    html_url: str
    assignees: list[str]


class DraftResponse(BaseModel):
    issue: Issue
    priority: Priority
    draft_body: str
    reasoning: str
    requires_approval: bool
    estimated_tokens: int
    trace_id: str


class AutopilotRun(BaseModel):
    run_id: str
    started_at: datetime
    finished_at: datetime | None = None
    issues_scanned: int = 0
    comments_posted: int = 0
    drafts_pending: int = 0
    errors: list[str] = Field(default_factory=list)
    cost_usd: float = 0.0
    evidence: list[str] = Field(default_factory=list)
