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

    Args:
        citations: List of citation records

    Returns:
        Deduplicated list (preserves first occurrence)
    """
    seen = set()
    unique = []

    for citation in citations:
        key = (citation.item_id, citation.item_flavor, citation.citation_doi)
        if key not in seen:
            seen.add(key)
            unique.append(citation)

    return unique
