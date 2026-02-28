"""Source adapters for the Obsidian researcher agent."""

from .arxiv_source import ArxivSource
from .vault_source import VaultSource, STOP_WORDS
from .reddit_source import RedditSource
from .web_page_source import WebPageSource
from .brainstorm_source import BrainstormSource
from .notebook_lm_source import NotebookLMSource
from .uspto_source import USPTOSource
from .github_source import GitHubSource

__all__ = [
    "ArxivSource",
    "VaultSource",
    "STOP_WORDS",
    "RedditSource",
    "WebPageSource",
    "BrainstormSource",
    "NotebookLMSource",
    "USPTOSource",
    "GitHubSource",
]
