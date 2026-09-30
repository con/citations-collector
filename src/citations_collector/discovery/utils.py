"""Utility functions for citation discovery."""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from citations_collector.models import CitationRecord

# Canonical precedence of discovery sources, used to pick metadata
# deterministically when the same citation is found by several sources.
# Registry-backed sources (metadata from doi.org content negotiation, i.e.
# CrossRef/DataCite records) come first; OpenAlex normalizes names (drops
# diacritics, abbreviates) so it only fills gaps.
SOURCE_PRECEDENCE: tuple[str, ...] = ("crossref", "datacite", "opencitations", "openalex")

# Metadata trust rank per source (lower is better).  Registry-backed sources
# share a rank since they return the same doi.org metadata.  Unknown sources
# (e.g. "manual") get the worst rank so they never block updates.
SOURCE_RANK: dict[str, int] = {
    "crossref": 0,
    "datacite": 0,
    "opencitations": 0,
    "openalex": 1,
}
UNKNOWN_SOURCE_RANK = max(SOURCE_RANK.values()) + 1

# Metadata fields merged across sources
METADATA_FIELDS: tuple[str, ...] = (
    "citation_title",
    "citation_authors",
    "citation_year",
    "citation_journal",
)

CitationKey = tuple[str, str, str | None]


def source_rank(source: str | None) -> int:
    """Return metadata trust rank of a source (lower is more trusted)."""
    return SOURCE_RANK.get(str(source), UNKNOWN_SOURCE_RANK) if source else UNKNOWN_SOURCE_RANK


def sort_sources(sources: list[str]) -> list[str]:
    """Order sources canonically (by SOURCE_PRECEDENCE, unknown ones last, stable)."""
    order = {s: i for i, s in enumerate(SOURCE_PRECEDENCE)}
    return sorted(dict.fromkeys(sources), key=lambda s: order.get(s, len(order)))


def make_retrying_session(
    total: int = 5,
    backoff_factor: float = 2.0,
    user_agent: str | None = None,
) -> requests.Session:
    """
    Create a requests Session that retries rate-limited and failed requests.

    Retries on 429 and 5xx with exponential backoff, honoring the server's
    Retry-After header.  Without it, a 429 from DataCite/OpenAlex silently
    drops that source for the ref, which makes results (and the metadata that
    wins deduplication) depend on the day's rate limiting.
    """
    session = requests.Session()
    if user_agent:
        session.headers["User-Agent"] = user_agent
    retry = Retry(
        total=total,
        backoff_factor=backoff_factor,
        backoff_max=120,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        respect_retry_after_header=True,
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

    When duplicates are found across sources, all sources are collected in
    ``citation_sources`` (in canonical SOURCE_PRECEDENCE order) and each
    metadata field is taken from the highest-precedence source providing a
    value.  The result therefore does not depend on the order in which
    sources answered or on which of them happened to fail.

    Args:
        citations: List of citation records
        field_ranks: Optional dict filled with, per citation key, the source
            rank (see ``source_rank``) that provided each metadata field.

    Returns:
        Deduplicated list with sources merged
    """
    # Group citations by unique key
    grouped: dict[CitationKey, list[CitationRecord]] = {}

    for citation in citations:
        key = (citation.item_id, citation.item_flavor, citation.citation_doi)
        grouped.setdefault(key, []).append(citation)

    order = {s: i for i, s in enumerate(SOURCE_PRECEDENCE)}

    unique = []
    for key, group in grouped.items():
        # Stable sort by canonical source precedence
        group = sorted(group, key=lambda c: order.get(str(c.citation_source), len(order)))
        citation = group[0]

        ranks: dict[str, int] = {}
        for field in METADATA_FIELDS:
            for c in group:
                value = getattr(c, field)
                if value:
                    if value != getattr(citation, field):
                        setattr(citation, field, value)
                    ranks[field] = source_rank(c.citation_source)
                    break
        # Fill other empty fields (e.g. citation_type from OpenAlex)
        for c in group[1:]:
            for field in ("citation_type", "citation_pmid", "citation_arxiv", "citation_url"):
                if not getattr(citation, field) and getattr(c, field):
                    setattr(citation, field, getattr(c, field))

        sources = sort_sources([str(c.citation_source) for c in group if c.citation_source])
        if sources:
            citation.citation_sources = sources  # type: ignore[assignment]
            # Keep citation_source set to first source (required field, backward compat)
            citation.citation_source = sources[0]  # type: ignore[assignment]

        if field_ranks is not None:
            field_ranks[key] = ranks
        unique.append(citation)

    return unique
