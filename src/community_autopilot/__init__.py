"""Benni OS Community Autopilot — autonomous GitHub issue responder with NEMESIS tracing."""

from .analyzer import Analyzer
from .config import Settings
from .models import AutopilotRun, Comment, DraftResponse, Issue, IssueState, Priority
from .nemesis import NemesisClient, NemesisEvent
from .responder import Responder
from .slack import SlackNotifier
from .watcher import GitHubWatcher

__version__ = "0.2.0"
__all__ = [
    "Analyzer",
    "AutopilotRun",
    "Comment",
    "DraftResponse",
    "GitHubWatcher",
    "Issue",
    "IssueState",
    "NemesisClient",
    "NemesisEvent",
    "Priority",
    "Responder",
    "Settings",
    "SlackNotifier",
    "__version__",
]
