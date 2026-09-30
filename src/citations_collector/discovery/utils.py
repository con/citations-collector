"""Utility functions for citation discovery."""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from citations_collector.models import CitationRecord

# Metadata trust rank (lower is better): registry-backed sources return the same
# doi.org metadata; OpenAlex normalizes names (drops diacritics), so ranks below.
SOURCE_RANK: dict[str, int] = {
    "crossref": 0,
    "datacite": 0,
    "opencitations": 0,
    "openalex": 1,
}
UNKNOWN_SOURCE_RANK = max(SOURCE_RANK.values()) + 1

METADATA_FIELDS: tuple[str, ...] = (
    "citation_title",
    "citation_authors",
    "citation_year",
    "citation_journal",
    "citation_type",
)

CitationKey = tuple[str, str, str | None]


def source_rank(source: str | None) -> int:
    """Return metadata trust rank of a source (lower is more trusted)."""
    return SOURCE_RANK.get(str(source), UNKNOWN_SOURCE_RANK)


class _CappedRetry(Retry):
    """Retry that caps server-requested Retry-After waits."""

    def parse_retry_after(self, retry_after: str) -> float:
        return min(super().parse_retry_after(retry_after), 120)


def make_retrying_session(
    total: int = 5,
    backoff_factor: float = 2.0,
    user_agent: str | None = None,
) -> requests.Session:
    """Create a Session retrying 429/5xx responses with backoff (honoring Retry-After)."""
    session = requests.Session()
    if user_agent:
        session.headers["User-Agent"] = user_agent
    retry = _CappedRetry(
        total=total,
        read=False,  # do not multiply slow queries' read timeouts
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def build_doi_url(doi: str) -> str:
    """
    Build resolver URL for DOI.

    Args:
        doi: DOI string (without doi: prefix)

    Returns:
        Full DOI resolver URL
    """
    return f"https://doi.org/{doi}"


def deduplicate_citations(
    citations: list[CitationRecord],
    field_ranks: dict[CitationKey, dict[str, int]] | None = None,
) -> list[CitationRecord]:
    """
    Deduplicate citations by unique key (item_id, item_flavor, citation_doi).

    Sources are collected in citation_sources, and each metadata field is taken
    from the most trusted source providing it (see SOURCE_RANK).

    Args:
        citations: List of citation records
        field_ranks: Optional dict to fill with, per citation key, the rank of
            the source that provided each metadata field.

    Returns:
        Deduplicated list with sources merged
    """
    # Group citations by unique key
    grouped: dict[CitationKey, list[CitationRecord]] = {}

    for citation in citations:
        key = (citation.item_id, citation.item_flavor, citation.citation_doi)
        grouped.setdefault(key, []).append(citation)

    unique = []
    for key, group in grouped.items():
        group = sorted(group, key=lambda c: source_rank(c.citation_source))
        citation = group[0]

        ranks: dict[str, int] = {}
        for field in METADATA_FIELDS:
            for c in group:
                value = getattr(c, field)
                if value:
                    setattr(citation, field, value)
                    ranks[field] = source_rank(c.citation_source)
                    break

        sources = list(dict.fromkeys(str(c.citation_source) for c in group if c.citation_source))
        if sources:
            citation.citation_sources = sources  # type: ignore[assignment]
            # Keep citation_source set to first source (required field, backward compat)
            citation.citation_source = sources[0]  # type: ignore[assignment]

        if field_ranks is not None:
            field_ranks[key] = ranks
        unique.append(citation)

    return unique
