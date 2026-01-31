"""Utility functions for citation discovery."""

from __future__ import annotations

from citations_collector.models import CitationRecord


def build_doi_url(doi: str) -> str:
    """
    Build resolver URL for DOI.

    Args:
        doi: DOI string (without doi: prefix)

    Returns:
        Full DOI resolver URL
    """
    return f"https://doi.org/{doi}"


def deduplicate_citations(citations: list[CitationRecord]) -> list[CitationRecord]:
    """
    Deduplicate citations by unique key (item_id, item_flavor, citation_doi).

    When duplicates found across sources, collects all sources in citation_sources field.

    Args:
        citations: List of citation records

    Returns:
        Deduplicated list with sources merged
    """
    # Group citations by unique key
    grouped: dict[tuple[str, str, str | None], list[CitationRecord]] = {}

    for citation in citations:
        key = (citation.item_id, citation.item_flavor, citation.citation_doi)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(citation)

    # Build unique list, merging sources
    unique = []
    for _key, group in grouped.items():
        # Use first citation as base
        citation = group[0]

        # Collect all sources that found this citation
        sources = []
        for c in group:
            if c.citation_source and c.citation_source not in sources:
                sources.append(c.citation_source)

        # Always set citation_sources to the list (even if single source)
        if sources:
            citation.citation_sources = sources  # type: ignore[assignment]
            # Keep citation_source set to first source (required field, backward compat)
            citation.citation_source = sources[0]  # type: ignore[assignment]

        unique.append(citation)

    return unique
