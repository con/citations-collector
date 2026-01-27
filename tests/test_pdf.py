"""Tests for PDF acquisition module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import responses

from citations_collector.models import CitationRecord
from citations_collector.pdf import PDFAcquirer
from citations_collector.unpaywall import UnpaywallResult


def _make_citation(**kwargs) -> CitationRecord:
    """Create a CitationRecord with sensible defaults."""
    defaults = {
        "item_id": "test-item",
        "item_flavor": "1.0",
        "citation_doi": "10.1234/test",
        "citation_title": "Test Paper",
        "citation_relationship": "Cites",
        "citation_source": "crossref",
        "citation_status": "active",
    }
    defaults.update(kwargs)
    return CitationRecord(**defaults)


@pytest.mark.ai_generated
@responses.activate
def test_acquire_for_citation_oa(tmp_path: Path) -> None:
    """OA citation gets PDF downloaded and fields set."""
    oa_result = UnpaywallResult(
        doi="10.1234/test",
        is_oa=True,
        oa_status="gold",
        best_oa_url="https://example.com/paper.pdf",
        license="cc-by",
    )

    # Mock unpaywall lookup
    with patch.object(PDFAcquirer, "_fetch_bibtex"):
        acquirer = PDFAcquirer(output_dir=tmp_path)
        acquirer.unpaywall = type("Mock", (), {"lookup": lambda self, doi: oa_result})()

        # Mock the PDF download
        responses.add(
            responses.GET,
            "https://example.com/paper.pdf",
            body=b"%PDF-1.4 fake content",
            status=200,
        )

        citation = _make_citation()
        result = acquirer.acquire_for_citation(citation)

    assert result is True
    assert citation.oa_status == "gold"
    assert citation.pdf_url == "https://example.com/paper.pdf"
    assert citation.pdf_path is not None
    assert (tmp_path / "10.1234" / "test" / "article.pdf").exists()


@pytest.mark.ai_generated
def test_acquire_for_citation_closed(tmp_path: Path) -> None:
    """Closed citation gets no download attempt."""
    closed_result = UnpaywallResult(
        doi="10.1234/closed",
        is_oa=False,
        oa_status="closed",
        best_oa_url=None,
        license=None,
    )

    acquirer = PDFAcquirer(output_dir=tmp_path)
    acquirer.unpaywall = type("Mock", (), {"lookup": lambda self, doi: closed_result})()

    citation = _make_citation(citation_doi="10.1234/closed")
    result = acquirer.acquire_for_citation(citation)

    assert result is False
    assert citation.oa_status == "closed"
    assert citation.pdf_url is None
    assert citation.pdf_path is None


@pytest.mark.ai_generated
def test_acquire_for_citation_dry_run(tmp_path: Path) -> None:
    """Dry run sets oa_status but does not download."""
    oa_result = UnpaywallResult(
        doi="10.1234/test",
        is_oa=True,
        oa_status="gold",
        best_oa_url="https://example.com/paper.pdf",
        license="cc-by",
    )

    acquirer = PDFAcquirer(output_dir=tmp_path)
    acquirer.unpaywall = type("Mock", (), {"lookup": lambda self, doi: oa_result})()

    citation = _make_citation()
    result = acquirer.acquire_for_citation(citation, dry_run=True)

    assert result is False
    assert citation.oa_status == "gold"
    assert citation.pdf_url == "https://example.com/paper.pdf"
    # No file should be created
    assert not (tmp_path / "10.1234" / "test" / "article.pdf").exists()


@pytest.mark.ai_generated
def test_acquire_all_deduplication(tmp_path: Path) -> None:
    """Same DOI in multiple citations triggers only one lookup."""
    lookup_count = 0

    def counting_lookup(self, doi):
        nonlocal lookup_count
        lookup_count += 1
        return UnpaywallResult(
            doi=doi, is_oa=False, oa_status="closed", best_oa_url=None, license=None
        )

    acquirer = PDFAcquirer(output_dir=tmp_path)
    acquirer.unpaywall = type("Mock", (), {"lookup": counting_lookup})()

    citations = [
        _make_citation(citation_doi="10.1234/same", item_flavor="v1"),
        _make_citation(citation_doi="10.1234/same", item_flavor="v2"),
        _make_citation(citation_doi="10.1234/same", item_flavor="v3"),
    ]
    acquirer.acquire_all(citations)

    assert lookup_count == 1
    # All citations should have oa_status propagated
    for c in citations:
        assert c.oa_status == "closed"


@pytest.mark.ai_generated
def test_doi_to_path(tmp_path: Path) -> None:
    """DOI converts to expected relative path."""
    acquirer = PDFAcquirer(output_dir=tmp_path)
    path = acquirer._doi_to_path("10.1038/s41597-023-02214-y")
    assert path == Path("10.1038/s41597-023-02214-y/article.pdf")


@pytest.mark.ai_generated
@responses.activate
def test_fetch_bibtex(tmp_path: Path) -> None:
    """BibTeX fetched via DOI content negotiation."""
    bibtex_content = "@article{test2024, title={Test Paper}, author={Doe, J}}"
    responses.add(
        responses.GET,
        "https://doi.org/10.1234/test",
        body=bibtex_content,
        status=200,
    )

    acquirer = PDFAcquirer(output_dir=tmp_path)
    dest = tmp_path / "article.bib"
    acquirer._fetch_bibtex("10.1234/test", dest)

    assert dest.exists()
    assert dest.read_text() == bibtex_content
