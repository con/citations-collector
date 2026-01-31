"""Tests for dataset-specific citation relationships."""

from __future__ import annotations

from pathlib import Path

import pytest

from citations_collector.models import CitationRecord, CitationRelationship
from citations_collector.persistence import tsv_io


@pytest.mark.ai_generated
def test_cites_as_data_source() -> None:
    """Test CitesAsDataSource relationship type."""
    citation = CitationRecord(
        item_id="dandi:000003",
        item_flavor="0.210812.1448",
        citation_relationship=CitationRelationship.CitesAsDataSource,
        citation_source="crossref",
    )

    assert citation.citation_relationship == CitationRelationship.CitesAsDataSource
    assert citation.citation_relationships == [CitationRelationship.CitesAsDataSource]


@pytest.mark.ai_generated
def test_reviews_relationship() -> None:
    """Test Reviews relationship type."""
    citation = CitationRecord(
        item_id="dandi:000003",
        item_flavor="latest",
        citation_relationship=CitationRelationship.Reviews,
        citation_source="manual",
    )

    assert citation.citation_relationship == CitationRelationship.Reviews


@pytest.mark.ai_generated
def test_cites_as_evidence() -> None:
    """Test CitesAsEvidence relationship type."""
    citation = CitationRecord(
        item_id="dandi:000020",
        item_flavor="1.0.0",
        citation_relationship=CitationRelationship.CitesAsEvidence,
        citation_source="datacite",
    )

    assert citation.citation_relationship == CitationRelationship.CitesAsEvidence


@pytest.mark.ai_generated
def test_compiles_relationship() -> None:
    """Test Compiles relationship type for meta-analyses."""
    citation = CitationRecord(
        item_id="dandi:000003",
        item_flavor="1.0.0",
        citation_relationship=CitationRelationship.Compiles,
        citation_comment="Meta-analysis combining DANDI:000003, 000020, 000055",
        citation_source="manual",
    )

    assert citation.citation_relationship == CitationRelationship.Compiles
    assert "000020" in citation.citation_comment


@pytest.mark.ai_generated
def test_cites_for_information() -> None:
    """Test CitesForInformation relationship type."""
    citation = CitationRecord(
        item_id="dandi:000003",
        item_flavor="latest",
        citation_relationship=CitationRelationship.CitesForInformation,
        citation_source="manual",
    )

    assert citation.citation_relationship == CitationRelationship.CitesForInformation


@pytest.mark.ai_generated
def test_multiple_dataset_citations_same_paper(tmp_path: Path) -> None:
    """Test pattern: one paper citing multiple datasets (meta-analysis)."""
    # Simulate a paper citing 3 datasets
    citations = [
        CitationRecord(
            item_id="dandi:000003",
            item_flavor="1.0.0",
            citation_doi="10.1234/meta-analysis",
            citation_relationship=CitationRelationship.Compiles,
            citation_comment="Combined with DANDI:000020, 000055",
            citation_source="manual",
        ),
        CitationRecord(
            item_id="dandi:000020",
            item_flavor="1.0.0",
            citation_doi="10.1234/meta-analysis",
            citation_relationship=CitationRelationship.Compiles,
            citation_comment="Combined with DANDI:000003, 000055",
            citation_source="manual",
        ),
        CitationRecord(
            item_id="dandi:000055",
            item_flavor="1.0.0",
            citation_doi="10.1234/meta-analysis",
            citation_relationship=CitationRelationship.Compiles,
            citation_comment="Combined with DANDI:000003, 000020",
            citation_source="manual",
        ),
    ]

    # Save and reload
    tsv_file = tmp_path / "multi_dataset.tsv"
    tsv_io.save_citations(citations, tsv_file)
    loaded = tsv_io.load_citations(tsv_file)

    assert len(loaded) == 3
    # All should have same DOI (same paper)
    assert all(c.citation_doi == "10.1234/meta-analysis" for c in loaded)
    # All should have Compiles relationship
    assert all(c.citation_relationship == CitationRelationship.Compiles for c in loaded)
    # Each should reference the others in comments
    assert all("000020" in c.citation_comment or c.item_id == "dandi:000020" for c in loaded)


@pytest.mark.ai_generated
def test_new_relationships_tsv_roundtrip(tmp_path: Path) -> None:
    """Test that new relationship types survive TSV save/load cycle."""
    citations = [
        CitationRecord(
            item_id="test-1",
            item_flavor="1.0",
            citation_relationship=CitationRelationship.CitesAsDataSource,
            citation_source="crossref",
        ),
        CitationRecord(
            item_id="test-2",
            item_flavor="1.0",
            citation_relationship=CitationRelationship.Reviews,
            citation_source="manual",
        ),
        CitationRecord(
            item_id="test-3",
            item_flavor="1.0",
            citation_relationship=CitationRelationship.CitesAsEvidence,
            citation_source="datacite",
        ),
        CitationRecord(
            item_id="test-4",
            item_flavor="1.0",
            citation_relationship=CitationRelationship.Compiles,
            citation_source="manual",
        ),
        CitationRecord(
            item_id="test-5",
            item_flavor="1.0",
            citation_relationship=CitationRelationship.CitesForInformation,
            citation_source="manual",
        ),
    ]

    tsv_file = tmp_path / "new_relationships.tsv"
    tsv_io.save_citations(citations, tsv_file)
    loaded = tsv_io.load_citations(tsv_file)

    assert len(loaded) == 5
    assert loaded[0].citation_relationship == CitationRelationship.CitesAsDataSource
    assert loaded[1].citation_relationship == CitationRelationship.Reviews
    assert loaded[2].citation_relationship == CitationRelationship.CitesAsEvidence
    assert loaded[3].citation_relationship == CitationRelationship.Compiles
    assert loaded[4].citation_relationship == CitationRelationship.CitesForInformation


@pytest.mark.ai_generated
def test_mixed_relationships_on_same_citation() -> None:
    """Test a citation with multiple relationship types."""
    # Paper that both uses data AND reviews the dataset
    citation = CitationRecord(
        item_id="dandi:000003",
        item_flavor="1.0.0",
        citation_relationship=CitationRelationship.Uses,
        citation_relationships=[
            CitationRelationship.Uses,
            CitationRelationship.Reviews,
        ],
        citation_source="crossref",
    )

    assert len(citation.citation_relationships) == 2
    assert CitationRelationship.Uses in citation.citation_relationships
    assert CitationRelationship.Reviews in citation.citation_relationships


@pytest.mark.ai_generated
def test_data_descriptor_pattern() -> None:
    """Test pattern: data descriptor paper citing/documenting a dataset."""
    # Scientific Data paper describing a dataset
    citation = CitationRecord(
        item_id="dandi:000108",
        item_flavor="1.0.0",
        citation_doi="10.1038/s41597-024-12345-6",
        citation_journal="Scientific Data",
        citation_relationship=CitationRelationship.IsDocumentedBy,
        citation_type="Publication",
        citation_source="crossref",
    )

    assert citation.citation_relationship == CitationRelationship.IsDocumentedBy
    assert citation.citation_journal == "Scientific Data"


@pytest.mark.ai_generated
def test_validation_study_pattern() -> None:
    """Test pattern: method paper validating on a dataset."""
    # Method paper benchmarking algorithm on dataset
    citation = CitationRecord(
        item_id="dandi:000003",
        item_flavor="latest",
        citation_doi="10.1038/s41592-024-54321-1",
        citation_journal="Nature Methods",
        citation_relationship=CitationRelationship.CitesAsEvidence,
        citation_type="Publication",
        citation_source="crossref",
    )

    assert citation.citation_relationship == CitationRelationship.CitesAsEvidence
    assert citation.citation_journal == "Nature Methods"
