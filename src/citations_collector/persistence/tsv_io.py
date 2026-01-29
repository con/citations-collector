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
    "citation_source",
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

            # Convert None to empty string for TSV
            cleaned = {k: ("" if v is None else str(v)) for k, v in data.items()}

            writer.writerow(cleaned)
