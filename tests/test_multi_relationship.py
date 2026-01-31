"""Tests for multi-relationship citation support."""

from __future__ import annotations

from pathlib import Path

import pytest

from citations_collector.models import CitationRecord, CitationRelationship
from citations_collector.persistence import tsv_io


@pytest.mark.ai_generated
def test_single_relationship_backward_compat(tmp_path: Path) -> None:
    """Test that single relationship (old format) still works."""
    citation = CitationRecord(
        item_id="test-item",
        item_flavor="1.0.0",
        citation_relationship=CitationRelationship.Cites,
        citation_source="manual",
    )

    # Should auto-populate citation_relationships from citation_relationship
    assert citation.citation_relationships == [CitationRelationship.Cites]
    assert citation.citation_relationship == CitationRelationship.Cites


@pytest.mark.ai_generated
def test_multiple_relationships() -> None:
    """Test that multiple relationships can be specified."""
    citation = CitationRecord(
        item_id="test-item",
        item_flavor="1.0.0",
        citation_relationship=CitationRelationship.Cites,
        citation_relationships=[CitationRelationship.Cites, CitationRelationship.Uses],
        citation_source="manual",
    )

    # Should have both relationships
    assert citation.citation_relationships == [
        CitationRelationship.Cites,
        CitationRelationship.Uses,
    ]
    # Singular should match first
    assert citation.citation_relationship == CitationRelationship.Cites


@pytest.mark.ai_generated
def test_relationships_coherence_validation() -> None:
    """Test that citation_relationship must match first element of citation_relationships."""
    with pytest.raises(ValueError, match="must match first element"):
        CitationRecord(
            item_id="test-item",
            item_flavor="1.0.0",
            citation_relationship=CitationRelationship.Cites,
            citation_relationships=[CitationRelationship.Uses],  # Mismatch!
            citation_source="manual",
        )


@pytest.mark.ai_generated
def test_tsv_save_multiple_relationships(tmp_path: Path) -> None:
    """Test saving citation with multiple relationships to TSV."""
    citation = CitationRecord(
        item_id="test-item",
        item_flavor="1.0.0",
        citation_relationship=CitationRelationship.Cites,
        citation_relationships=[CitationRelationship.Cites, CitationRelationship.Uses],
        citation_source="manual",
    )

    tsv_file = tmp_path / "multi_rel.tsv"
    tsv_io.save_citations([citation], tsv_file)

    # Read raw TSV to check format
    with open(tsv_file) as f:
        lines = f.readlines()

    header = lines[0].strip().split("\t")
    data = lines[1].strip().split("\t")

    # Should have citation_relationships column (not citation_relationship)
    assert "citation_relationships" in header
    assert "citation_relationship" not in header

    # Find the relationships value
    rel_idx = header.index("citation_relationships")
    rel_value = data[rel_idx]

    # Should be comma-separated
    assert rel_value == "Cites, Uses"


@pytest.mark.ai_generated
def test_tsv_load_multiple_relationships(tmp_path: Path) -> None:
    """Test loading citation with multiple relationships from TSV."""
    # Create TSV with multiple relationships
    tsv_file = tmp_path / "multi_rel.tsv"
    with open(tsv_file, "w") as f:
        f.write("item_id\titem_flavor\tcitation_relationships\tcitation_sources\n")
        f.write("test-item\t1.0.0\tCites, Uses\tmanual\n")

    citations = tsv_io.load_citations(tsv_file)

    assert len(citations) == 1
    citation = citations[0]

    # Should parse into list
    assert citation.citation_relationships == [
        CitationRelationship.Cites,
        CitationRelationship.Uses,
    ]
    # Singular should be first
    assert citation.citation_relationship == CitationRelationship.Cites


@pytest.mark.ai_generated
def test_tsv_load_old_column_name(tmp_path: Path) -> None:
    """Test loading from old TSV with citation_relationship (singular) column."""
    # Create TSV with old column name
    tsv_file = tmp_path / "old_format.tsv"
    with open(tsv_file, "w") as f:
        f.write("item_id\titem_flavor\tcitation_relationship\tcitation_source\n")
        f.write("test-item\t1.0.0\tCites\tmanual\n")

    citations = tsv_io.load_citations(tsv_file)

    assert len(citations) == 1
    citation = citations[0]

    # Should migrate to new format
    assert citation.citation_relationships == [CitationRelationship.Cites]
    assert citation.citation_relationship == CitationRelationship.Cites


@pytest.mark.ai_generated
def test_tsv_roundtrip_multiple_relationships(tmp_path: Path) -> None:
    """Test that multiple relationships survive save/load cycle."""
    original = CitationRecord(
        item_id="test-item",
        item_flavor="1.0.0",
        citation_relationship=CitationRelationship.References,
        citation_relationships=[
            CitationRelationship.References,
            CitationRelationship.IsDerivedFrom,
        ],
        citation_source="manual",
    )

    tsv_file = tmp_path / "roundtrip.tsv"

    # Save
    tsv_io.save_citations([original], tsv_file)

    # Load
    loaded = tsv_io.load_citations(tsv_file)

    assert len(loaded) == 1
    citation = loaded[0]

    # Should preserve both relationships
    assert citation.citation_relationships == [
        CitationRelationship.References,
        CitationRelationship.IsDerivedFrom,
    ]
    assert citation.citation_relationship == CitationRelationship.References


@pytest.mark.ai_generated
def test_common_relationship_combinations() -> None:
    """Test common multi-relationship combinations mentioned in schema."""
    # Cites + Uses (paper that cites and uses data from a dataset)
    citation1 = CitationRecord(
        item_id="dataset-123",
        item_flavor="1.0.0",
        citation_relationship=CitationRelationship.Cites,
        citation_relationships=[CitationRelationship.Cites, CitationRelationship.Uses],
        citation_source="crossref",
    )
    assert len(citation1.citation_relationships) == 2

    # IsDocumentedBy + Describes (documentation that also describes methodology)
    citation2 = CitationRecord(
        item_id="tool-456",
        item_flavor="2.0.0",
        citation_relationship=CitationRelationship.IsDocumentedBy,
        citation_relationships=[
            CitationRelationship.IsDocumentedBy,
            CitationRelationship.Describes,
        ],
        citation_source="datacite",
    )
    assert len(citation2.citation_relationships) == 2

    # References + IsDerivedFrom (work that references and is derived from)
    citation3 = CitationRecord(
        item_id="software-789",
        item_flavor="3.1.0",
        citation_relationship=CitationRelationship.References,
        citation_relationships=[
            CitationRelationship.References,
            CitationRelationship.IsDerivedFrom,
        ],
        citation_source="openalex",
    )
    assert len(citation3.citation_relationships) == 2
