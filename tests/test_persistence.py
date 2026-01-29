"""Tests for YAML and TSV persistence."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from citations_collector.persistence import tsv_io, yaml_io


@pytest.mark.ai_generated
def test_load_yaml_round_trip(collections_dir: Path, tmp_path: Path) -> None:
    """Test loading and saving YAML collection preserves structure."""
    input_file = collections_dir / "simple.yaml"
    output_file = tmp_path / "output.yaml"

    # Load collection
    collection = yaml_io.load_collection(input_file)

    # Verify structure
    assert collection.name == "Simple Test Collection"
    assert len(collection.items) == 1
    assert collection.items[0].item_id == "test-item"
    assert len(collection.items[0].flavors) == 1
    assert collection.items[0].flavors[0].flavor_id == "1.0.0"
    assert len(collection.items[0].flavors[0].refs) == 1

    # Save and reload
    yaml_io.save_collection(collection, output_file)
    reloaded = yaml_io.load_collection(output_file)

    # Verify round-trip
    assert reloaded.name == collection.name
    assert len(reloaded.items) == len(collection.items)
    assert reloaded.items[0].item_id == collection.items[0].item_id


@pytest.mark.ai_generated
def test_load_tsv_round_trip(tsv_dir: Path, tmp_path: Path) -> None:
    """Test loading and saving TSV citations preserves data."""
    input_file = tsv_dir / "simple.tsv"
    output_file = tmp_path / "output.tsv"

    # Load citations
    citations = tsv_io.load_citations(input_file)

    # Verify structure
    assert len(citations) == 1
    assert citations[0].item_id == "test-item"
    assert citations[0].item_flavor == "1.0.0"
    assert citations[0].citation_doi == "10.1234/citing.paper"
    assert citations[0].citation_status == "active"

    # Save and reload
    tsv_io.save_citations(citations, output_file)
    reloaded = tsv_io.load_citations(output_file)

    # Verify round-trip
    assert len(reloaded) == len(citations)
    assert reloaded[0].item_id == citations[0].item_id
    assert reloaded[0].citation_doi == citations[0].citation_doi


@pytest.mark.ai_generated
def test_missing_optional_fields(tmp_path: Path) -> None:
    """Test handling of missing optional fields in TSV."""
    tsv_file = tmp_path / "minimal.tsv"

    # Create minimal TSV with only required fields
    tsv_file.write_text(
        "item_id\titem_flavor\tcitation_doi\tcitation_relationship\tcitation_source\tcitation_status\n"
        "item1\tver1\t10.1234/paper\tCites\tcrossref\tactive\n"
    )

    # Should load without errors
    citations = tsv_io.load_citations(tsv_file)
    assert len(citations) == 1
    assert citations[0].citation_title is None
    assert citations[0].citation_authors is None
    assert citations[0].citation_year is None


@pytest.mark.ai_generated
def test_validation_errors(tmp_path: Path) -> None:
    """Test validation errors for malformed YAML."""
    yaml_file = tmp_path / "invalid.yaml"

    # Create YAML without required fields
    yaml_file.write_text(
        """
name: Invalid Collection
items:
  - item_id: test
    # Missing required flavors field
"""
    )

    # Should raise validation error
    with pytest.raises(ValidationError):
        yaml_io.load_collection(yaml_file)


@pytest.mark.ai_generated
def test_load_complex_collection(collections_dir: Path) -> None:
    """Test loading complex collection with multiple items and versions."""
    collection = yaml_io.load_collection(collections_dir / "repronim-tools.yaml")

    # Verify loaded correctly
    assert collection.name == "ReproNim Tools"
    assert len(collection.items) > 5  # Has multiple tools
    assert collection.maintainers == ["ReproNim Team"]

    # Check a specific item (datalad)
    datalad = next((item for item in collection.items if item.item_id == "datalad"), None)
    assert datalad is not None
    assert datalad.name == "DataLad"
    assert len(datalad.flavors) > 0
    assert len(datalad.flavors[0].refs) >= 2  # Has multiple ref types


@pytest.mark.ai_generated
def test_load_citations_example(tsv_dir: Path) -> None:
    """Test loading example citations TSV with curation fields."""
    citations = tsv_io.load_citations(tsv_dir / "citations-example.tsv")

    # Verify loaded
    assert len(citations) > 0

    # Check for citations with different statuses
    statuses = {c.citation_status for c in citations}
    assert "active" in statuses

    # Check for merged citation
    merged = [c for c in citations if c.citation_status == "merged"]
    if merged:
        assert merged[0].citation_merged_into is not None


@pytest.mark.ai_generated
def test_tsv_round_trip_oa_fields(tmp_path: Path) -> None:
    """TSV round-trip preserves oa_status, pdf_url, and pdf_path columns."""
    from citations_collector.models import CitationRecord

    citation = CitationRecord(
        item_id="test-item",
        item_flavor="1.0",
        citation_doi="10.1234/oa-paper",
        citation_relationship="Cites",
        citation_source="crossref",
        citation_status="active",
        oa_status="gold",
        pdf_url="https://example.com/paper.pdf",
        pdf_path="pdfs/10.1234/oa-paper/article.pdf",
    )

    tsv_file = tmp_path / "oa_fields.tsv"
    tsv_io.save_citations([citation], tsv_file)
    reloaded = tsv_io.load_citations(tsv_file)

    assert len(reloaded) == 1
    assert reloaded[0].oa_status == "gold"
    assert reloaded[0].pdf_url == "https://example.com/paper.pdf"
    assert reloaded[0].pdf_path == "pdfs/10.1234/oa-paper/article.pdf"
