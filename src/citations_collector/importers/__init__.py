"""Reference expanders for converting ref types to DOIs."""

from __future__ import annotations

from citations_collector.importers.github import GitHubMapper
from citations_collector.importers.zenodo import ZenodoExpander

__all__ = [
    "GitHubMapper",
    "ZenodoExpander",
]
