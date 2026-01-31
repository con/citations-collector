"""Load and save TSV citation files."""

from __future__ import annotations

import csv
from contextlib import suppress
from pathlib import Path

from citations_collector.models import CitationRecord

# TSV column order matching examples/citations-example.tsv
TSV_COLUMNS = [
    "item_id",
    "item_flavor",
    "item_ref_type",
    "item_ref_value",
    "item_name",
    "citation_doi",
    "citation_pmid",
    "citation_arxiv",
    "citation_url",
    "citation_title",
    "citation_authors",
    "citation_year",
    "citation_journal",
    "citation_relationship",
    "citation_type",
    "citation_sources",  # Plural - can contain comma-separated values
    "discovered_date",
    "citation_status",
    "citation_merged_into",
    "citation_comment",
    "curated_by",
    "curated_date",
    "oa_status",
    "pdf_url",
    "pdf_path",
]


def load_citations(path: Path) -> list[CitationRecord]:
    """
    Load citations from TSV file.

    Args:
        path: Path to TSV file

    Returns:
        List of CitationRecord objects

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    citations = []

    with open(path, newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            # Remove empty string values (treat as None)
            cleaned = {k: (v if v != "" else None) for k, v in row.items()}

            # Convert year to int if present
            if cleaned.get("citation_year"):
                with suppress(ValueError):
                    cleaned["citation_year"] = int(cleaned["citation_year"])  # type: ignore[arg-type]

            # Parse citation_sources from TSV (comma-separated)
            # Support both old "citation_source" and new "citation_sources" columns
            sources_field = cleaned.get("citation_sources") or cleaned.get("citation_source")
            if sources_field and "," in str(sources_field):
                # Multiple sources - parse into list
                sources = [s.strip() for s in sources_field.split(",")]
                cleaned["citation_sources"] = sources
                # Set citation_source to first (required field, backward compat)
                cleaned["citation_source"] = sources[0]
            elif sources_field:
                # Single source - still create list for consistency
                cleaned["citation_sources"] = [sources_field]
                cleaned["citation_source"] = sources_field
            else:
                # No source field - set default for backward compatibility
                # This can happen with old TSV files or test data
                # Use "manual" as it's the appropriate enum value for unspecified sources
                cleaned["citation_source"] = "manual"
                cleaned["citation_sources"] = ["manual"]

            # Create CitationRecord, only including fields that are in the model
            citation = CitationRecord(**cleaned)  # type: ignore[arg-type]
            citations.append(citation)

    return citations


def save_citations(citations: list[CitationRecord], path: Path) -> None:
    """
    Save citations to TSV file.

    Args:
        citations: List of CitationRecord objects
        path: Path to output TSV file
    """
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TSV_COLUMNS, delimiter="\t", extrasaction="ignore")
        writer.writeheader()

        for citation in citations:
            # Convert to dict
            data = citation.model_dump(exclude_none=False, mode="python")

            # Serialize citation_sources list to comma-separated string
            if "citation_sources" in data and data["citation_sources"]:
                data["citation_sources"] = ", ".join(data["citation_sources"])
            # Remove citation_source (singular, deprecated field) from output
            if "citation_source" in data:
                del data["citation_source"]

            # Convert None to empty string for TSV
            cleaned = {k: ("" if v is None else str(v)) for k, v in data.items()}

            writer.writerow(cleaned)
