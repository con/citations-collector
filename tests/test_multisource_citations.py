"""Tests for multi-source citation handling."""

from __future__ import annotations

from pathlib import Path

import pytest

from citations_collector.discovery.utils import deduplicate_citations
from citations_collector.models import CitationRecord
from citations_collector.persistence import tsv_io


@pytest.mark.ai_generated
def test_deduplicate_merges_sources() -> None:
    """Test that deduplication merges sources for same citation."""
    # Create same citation found by 3 different sources
    citations = [
        CitationRecord(
            item_id="dandi.000003",
            item_flavor="0.210812.1448",
            citation_doi="10.1234/test",
            citation_title="Test Article",
            citation_relationship="Cites",
            citation_source="crossref",
            citation_status="active",
        ),
        CitationRecord(
            item_id="dandi.000003",
            item_flavor="0.210812.1448",
            citation_doi="10.1234/test",
            citation_title="Test Article",
            citation_relationship="Cites",
            citation_source="datacite",
            citation_status="active",
        ),
        CitationRecord(
            item_id="dandi.000003",
            item_flavor="0.210812.1448",
            citation_doi="10.1234/test",
            citation_title="Test Article",
            citation_relationship="Cites",
            citation_source="openalex",
            citation_status="active",
        ),
    ]

    # Deduplicate
    unique = deduplicate_citations(citations)

    # Should be one citation with 3 sources
    assert len(unique) == 1
    citation = unique[0]

    # Should have citation_sources list
    assert citation.citation_sources is not None
    assert len(citation.citation_sources) == 3
    assert set(citation.citation_sources) == {"crossref", "datacite", "openalex"}

    # citation_source should be first source (backward compat)
    assert citation.citation_source == "crossref"


@pytest.mark.ai_generated
def test_deduplicate_single_source() -> None:
    """Test that single-source citations still work."""
    citations = [
        CitationRecord(
            item_id="dandi.000003",
            item_flavor="0.210812.1448",
            citation_doi="10.1234/test",
            citation_title="Test Article",
            citation_relationship="Cites",
            citation_source="crossref",
            citation_status="active",
        ),
    ]

    unique = deduplicate_citations(citations)

    assert len(unique) == 1
    citation = unique[0]

    # Should still have citation_sources list (with one element)
    assert citation.citation_sources is not None
    assert citation.citation_sources == ["crossref"]
    assert citation.citation_source == "crossref"


@pytest.mark.ai_generated
def test_tsv_save_multisource(tmp_path: Path) -> None:
    """Test that TSV save serializes citation_sources correctly."""
    # Create citation with multiple sources
    citation = CitationRecord(
        item_id="dandi.000003",
        item_flavor="0.210812.1448",
        citation_doi="10.1234/test",
        citation_title="Test Article",
        citation_relationship="Cites",
        citation_source="crossref",  # Required field
        citation_sources=["crossref", "datacite", "openalex"],  # Actual sources
        citation_status="active",
    )

    # Save to TSV
    tsv_path = tmp_path / "test.tsv"
    tsv_io.save_citations([citation], tsv_path)

    # Read the TSV file and check citation_source column
    content = tsv_path.read_text()
    lines = content.strip().split("\n")

    # Header + 1 data row
    assert len(lines) == 2

    # Check that citation_source is comma-separated
    headers = lines[0].split("\t")
    values = lines[1].split("\t")

    citation_source_idx = headers.index("citation_source")
    citation_source_value = values[citation_source_idx]

    assert citation_source_value == "crossref, datacite, openalex"


@pytest.mark.ai_generated
def test_tsv_load_multisource(tmp_path: Path) -> None:
    """Test that TSV load parses comma-separated sources correctly."""
    # Create TSV with comma-separated sources
    headers = "\t".join(tsv_io.TSV_COLUMNS)
    values = [
        "dandi.000003",  # item_id
        "0.210812.1448",  # item_flavor
        "doi",  # item_ref_type
        "10.48324/dandi.000003/0.210812.1448",  # item_ref_value
        "Test",  # item_name
        "10.1234/test",  # citation_doi
        "",  # citation_pmid
        "",  # citation_arxiv
        "",  # citation_url
        "Test Article",  # citation_title
        "",  # citation_authors
        "",  # citation_year
        "",  # citation_journal
        "Cites",  # citation_relationship
        "",  # citation_type
        "crossref, datacite, openalex",  # citation_source (multi-source!)
        "",  # discovered_date
        "active",  # citation_status
        "",  # citation_merged_into
        "",  # citation_comment
        "",  # curated_by
        "",  # curated_date
        "",  # oa_status
        "",  # pdf_url
        "",  # pdf_path
    ]
    tsv_content = f"{headers}\n{chr(9).join(values)}\n"

    tsv_path = tmp_path / "test.tsv"
    tsv_path.write_text(tsv_content)

    # Load citations
    citations = tsv_io.load_citations(tsv_path)

    assert len(citations) == 1
    citation = citations[0]

    # Should parse comma-separated sources into list
    assert citation.citation_sources is not None
    assert len(citation.citation_sources) == 3
    assert set(citation.citation_sources) == {"crossref", "datacite", "openalex"}

    # citation_source should not be set (was removed during parsing)
    # Actually, the model requires citation_source, so it will use first from list
    # Let me check the load code...


@pytest.mark.ai_generated
def test_tsv_roundtrip_multisource(tmp_path: Path) -> None:
    """Test that multi-source citations survive save/load roundtrip."""
    # Create citation with multiple sources
    original = CitationRecord(
        item_id="dandi.000003",
        item_flavor="0.210812.1448",
        item_ref_type="doi",
        item_ref_value="10.48324/dandi.000003/0.210812.1448",
        citation_doi="10.1234/test",
        citation_title="Test Article",
        citation_relationship="Cites",
        citation_source="crossref",
        citation_sources=["crossref", "datacite", "openalex"],
        citation_status="active",
    )

    # Save
    tsv_path = tmp_path / "test.tsv"
    tsv_io.save_citations([original], tsv_path)

    # Load
    loaded = tsv_io.load_citations(tsv_path)

    assert len(loaded) == 1
    citation = loaded[0]

    # Verify sources preserved
    assert citation.citation_sources is not None
    assert set(citation.citation_sources) == {"crossref", "datacite", "openalex"}
