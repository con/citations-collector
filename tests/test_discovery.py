"""Tests for citation discovery APIs."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest
import responses

from citations_collector.discovery import CrossRefDiscoverer, OpenCitationsDiscoverer
from citations_collector.discovery.utils import deduplicate_citations
from citations_collector.models import ItemRef


@pytest.mark.ai_generated
@responses.activate
def test_crossref_success(responses_dir: Path) -> None:
    """Test successful citation discovery from CrossRef."""
    # Load mock response
    with open(responses_dir / "crossref_success.json") as f:
        mock_data = json.load(f)

    # Mock CrossRef API
    responses.add(
        responses.GET,
        "https://api.crossref.org/works/10.1234/test.dataset",
        json=mock_data,
        status=200,
    )

    # Create discoverer and item ref
    discoverer = CrossRefDiscoverer(email="test@example.org")
    item_ref = ItemRef(ref_type="doi", ref_value="10.1234/test.dataset")

    # Discover citations
    citations = discoverer.discover(item_ref)

    # Verify results
    assert len(citations) == 2
    assert citations[0].citation_doi == "10.1234/citing.paper1"
    assert citations[0].citation_source == "crossref"
    assert citations[0].citation_title == "First paper citing our dataset"
    assert citations[0].citation_year == 2024
    assert citations[1].citation_doi == "10.1234/citing.paper2"


@pytest.mark.ai_generated
@responses.activate
def test_crossref_empty_results(responses_dir: Path) -> None:
    """Test CrossRef with no citations."""
    # Load mock response
    with open(responses_dir / "crossref_empty.json") as f:
        mock_data = json.load(f)

    # Mock CrossRef API
    responses.add(
        responses.GET,
        "https://api.crossref.org/works/10.1234/test.dataset",
        json=mock_data,
        status=200,
    )

    # Create discoverer
    discoverer = CrossRefDiscoverer()
    item_ref = ItemRef(ref_type="doi", ref_value="10.1234/test.dataset")

    # Discover citations
    citations = discoverer.discover(item_ref)

    # Should return empty list, not error
    assert citations == []


@pytest.mark.ai_generated
@responses.activate
def test_crossref_network_error() -> None:
    """Test CrossRef graceful degradation on network error."""
    # Mock network error
    responses.add(
        responses.GET,
        "https://api.crossref.org/works/10.1234/test.dataset",
        status=500,
    )

    # Create discoverer
    discoverer = CrossRefDiscoverer()
    item_ref = ItemRef(ref_type="doi", ref_value="10.1234/test.dataset")

    # Should return empty list, not raise
    citations = discoverer.discover(item_ref)
    assert citations == []


@pytest.mark.ai_generated
@responses.activate
def test_opencitations_discovery(responses_dir: Path) -> None:
    """Test OpenCitations citation discovery."""
    # Load mock response
    with open(responses_dir / "opencitations_success.json") as f:
        mock_data = json.load(f)

    # Mock OpenCitations API
    responses.add(
        responses.GET,
        "https://opencitations.net/index/api/v2/citations/10.1234/test.dataset",
        json=mock_data,
        status=200,
    )

    # Create discoverer
    discoverer = OpenCitationsDiscoverer()
    item_ref = ItemRef(ref_type="doi", ref_value="10.1234/test.dataset")

    # Discover citations
    citations = discoverer.discover(item_ref)

    # Verify results
    assert len(citations) == 1
    assert citations[0].citation_doi == "10.1234/citing.paper3"
    assert citations[0].citation_source == "opencitations"


@pytest.mark.ai_generated
@responses.activate
def test_incremental_date_filtering() -> None:
    """Test incremental discovery using date filters."""
    # Mock CrossRef API with date filter
    responses.add(
        responses.GET,
        "https://api.crossref.org/works/10.1234/test.dataset?filter=from-index-date:2024-01-01",
        json={"message": {"reference": []}},
        status=200,
    )

    # Create discoverer
    discoverer = CrossRefDiscoverer()
    item_ref = ItemRef(ref_type="doi", ref_value="10.1234/test.dataset")

    # Discover with since parameter
    since = datetime(2024, 1, 1)
    discoverer.discover(item_ref, since=since)

    # Should have called API with date filter
    assert len(responses.calls) == 1
    assert "from-index-date:2024-01-01" in responses.calls[0].request.url


@pytest.mark.ai_generated
def test_deduplication_across_sources() -> None:
    """Test deduplication of citations from multiple sources."""
    from citations_collector.models import CitationRecord

    # Create duplicate citations (same item+flavor+doi)
    citations = [
        CitationRecord(
            item_id="test",
            item_flavor="1.0",
            citation_doi="10.1234/paper",
            citation_relationship="Cites",
            citation_source="crossref",
            citation_status="active",
        ),
        CitationRecord(
            item_id="test",
            item_flavor="1.0",
            citation_doi="10.1234/paper",
            citation_relationship="Cites",
            citation_source="opencitations",
            citation_status="active",
        ),
        CitationRecord(
            item_id="test",
            item_flavor="1.0",
            citation_doi="10.1234/different",
            citation_relationship="Cites",
            citation_source="crossref",
            citation_status="active",
        ),
    ]

    # Deduplicate
    unique = deduplicate_citations(citations)

    # Should keep only unique (item_id, item_flavor, citation_doi)
    assert len(unique) == 2
    dois = {c.citation_doi for c in unique}
    assert dois == {"10.1234/paper", "10.1234/different"}
