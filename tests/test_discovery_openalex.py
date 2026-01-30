"""Tests for OpenAlex citation discovery."""

from __future__ import annotations

import pytest
import responses

from citations_collector.discovery.openalex import OpenAlexDiscoverer
from citations_collector.models import ItemRef


def _mock_doi_resolution(doi: str, openalex_id: str = "W123456789") -> None:
    """Helper to mock DOI resolution to OpenAlex ID."""
    responses.add(
        responses.GET,
        f"https://api.openalex.org/works/https://doi.org/{doi}",
        json={
            "id": f"https://openalex.org/{openalex_id}",
            "doi": f"https://doi.org/{doi}",
            "title": "Test Work",
        },
        status=200,
    )


@pytest.mark.ai_generated
@responses.activate
def test_openalex_success() -> None:
    """Test successful citation discovery from OpenAlex."""
    discoverer = OpenAlexDiscoverer(email="test@example.com")

    # Mock DOI resolution
    _mock_doi_resolution("10.12345/example-doi", "W123456789")

    # Mock OpenAlex response with 2 citing works
    responses.add(
        responses.GET,
        "https://api.openalex.org/works",
        json={
            "results": [
                {
                    "doi": "https://doi.org/10.1234/citing-paper-1",
                    "title": "A Study Using the Dataset",
                    "publication_year": 2023,
                    "authorships": [
                        {"author": {"display_name": "Alice Smith"}},
                        {"author": {"display_name": "Bob Jones"}},
                    ],
                    "primary_location": {"source": {"display_name": "Nature Neuroscience"}},
                    "type": "article",
                },
                {
                    "doi": "https://doi.org/10.5678/citing-paper-2",
                    "title": "Another Study",
                    "publication_year": 2024,
                    "authorships": [{"author": {"display_name": "Carol White"}}],
                    "primary_location": {"source": {"display_name": "Journal of Neuroscience"}},
                    "type": "article",
                },
            ],
            "meta": {"next_cursor": None},  # No more pages
        },
        status=200,
    )

    item_ref = ItemRef(ref_type="doi", ref_value="10.12345/example-doi")
    citations = discoverer.discover(item_ref)

    assert len(citations) == 2

    # Check first citation
    assert citations[0].citation_doi == "10.1234/citing-paper-1"
    assert citations[0].citation_title == "A Study Using the Dataset"
    assert citations[0].citation_year == 2023
    assert citations[0].citation_authors == "Alice Smith; Bob Jones"
    assert citations[0].citation_journal == "Nature Neuroscience"
    assert citations[0].citation_type == "Publication"
    assert citations[0].citation_source == "openalex"
    assert citations[0].citation_relationship == "Cites"

    # Check second citation
    assert citations[1].citation_doi == "10.5678/citing-paper-2"
    assert citations[1].citation_title == "Another Study"
    assert citations[1].citation_authors == "Carol White"


@pytest.mark.ai_generated
@responses.activate
def test_openalex_empty_results() -> None:
    """Test OpenAlex with no citations found."""
    discoverer = OpenAlexDiscoverer()

    # Mock DOI resolution
    _mock_doi_resolution("10.12345/no-citations", "W987654321")

    responses.add(
        responses.GET,
        "https://api.openalex.org/works",
        json={"results": [], "meta": {"next_cursor": None}},
        status=200,
    )

    item_ref = ItemRef(ref_type="doi", ref_value="10.12345/no-citations")
    citations = discoverer.discover(item_ref)

    assert len(citations) == 0


@pytest.mark.ai_generated
@responses.activate
def test_openalex_network_error() -> None:
    """Test handling of network errors."""
    discoverer = OpenAlexDiscoverer()

    # Mock DOI resolution
    _mock_doi_resolution("10.12345/error", "WERROR")

    responses.add(
        responses.GET,
        "https://api.openalex.org/works",
        body="Internal Server Error",
        status=500,
    )

    item_ref = ItemRef(ref_type="doi", ref_value="10.12345/error")
    citations = discoverer.discover(item_ref)

    # Should return empty list on error, not raise
    assert len(citations) == 0


@pytest.mark.ai_generated
def test_openalex_non_doi_ref() -> None:
    """Test that non-DOI refs are rejected."""
    discoverer = OpenAlexDiscoverer()

    item_ref = ItemRef(ref_type="rrid", ref_value="SCR_016216")
    citations = discoverer.discover(item_ref)

    assert len(citations) == 0


@pytest.mark.ai_generated
@responses.activate
def test_openalex_pagination() -> None:
    """Test cursor-based pagination."""
    discoverer = OpenAlexDiscoverer()

    # Mock DOI resolution
    _mock_doi_resolution("10.12345/paginated", "WPAGINATED")

    # First page
    responses.add(
        responses.GET,
        "https://api.openalex.org/works",
        json={
            "results": [
                {
                    "doi": "https://doi.org/10.1234/page1",
                    "title": "Page 1 Paper",
                    "publication_year": 2023,
                    "authorships": [{"author": {"display_name": "Author 1"}}],
                    "primary_location": {"source": {"display_name": "Journal 1"}},
                    "type": "article",
                }
            ],
            "meta": {"next_cursor": "cursor-page-2"},  # More pages
        },
        status=200,
    )

    # Second page
    responses.add(
        responses.GET,
        "https://api.openalex.org/works",
        json={
            "results": [
                {
                    "doi": "https://doi.org/10.5678/page2",
                    "title": "Page 2 Paper",
                    "publication_year": 2024,
                    "authorships": [{"author": {"display_name": "Author 2"}}],
                    "primary_location": {"source": {"display_name": "Journal 2"}},
                    "type": "article",
                }
            ],
            "meta": {"next_cursor": None},  # Last page
        },
        status=200,
    )

    item_ref = ItemRef(ref_type="doi", ref_value="10.12345/paginated")
    citations = discoverer.discover(item_ref)

    # Should have fetched both pages
    assert len(citations) == 2
    assert citations[0].citation_doi == "10.1234/page1"
    assert citations[1].citation_doi == "10.5678/page2"


@pytest.mark.ai_generated
@responses.activate
def test_openalex_work_type_mapping() -> None:
    """Test mapping of OpenAlex work types to CitationType."""
    discoverer = OpenAlexDiscoverer()

    # Mock DOI resolution
    _mock_doi_resolution("10.12345/test", "WTEST")

    responses.add(
        responses.GET,
        "https://api.openalex.org/works",
        json={
            "results": [
                {
                    "doi": "https://doi.org/10.1234/preprint",
                    "title": "A Preprint",
                    "publication_year": 2023,
                    "authorships": [{"author": {"display_name": "Author"}}],
                    "primary_location": {"source": {"display_name": "bioRxiv"}},
                    "type": "preprint",  # Should map to "Preprint"
                },
                {
                    "doi": "https://doi.org/10.5678/dataset",
                    "title": "A Dataset",
                    "publication_year": 2023,
                    "authorships": [{"author": {"display_name": "Author"}}],
                    "primary_location": {"source": {"display_name": "Zenodo"}},
                    "type": "dataset",  # Should map to "Dataset"
                },
                {
                    "doi": "https://doi.org/10.9012/thesis",
                    "title": "A Thesis",
                    "publication_year": 2023,
                    "authorships": [{"author": {"display_name": "Author"}}],
                    "primary_location": {"source": {"display_name": "University"}},
                    "type": "dissertation",  # Should map to "Thesis"
                },
            ],
            "meta": {"next_cursor": None},
        },
        status=200,
    )

    item_ref = ItemRef(ref_type="doi", ref_value="10.12345/test")
    citations = discoverer.discover(item_ref)

    assert len(citations) == 3
    assert citations[0].citation_type == "Preprint"
    assert citations[1].citation_type == "Dataset"
    assert citations[2].citation_type == "Thesis"


@pytest.mark.ai_generated
@responses.activate
def test_openalex_missing_doi() -> None:
    """Test handling of works without DOI."""
    discoverer = OpenAlexDiscoverer()

    # Mock DOI resolution
    _mock_doi_resolution("10.12345/test", "WTEST2")

    responses.add(
        responses.GET,
        "https://api.openalex.org/works",
        json={
            "results": [
                {
                    "doi": None,  # Missing DOI
                    "title": "Work Without DOI",
                    "publication_year": 2023,
                    "authorships": [{"author": {"display_name": "Author"}}],
                    "primary_location": {"source": {"display_name": "Journal"}},
                    "type": "article",
                }
            ],
            "meta": {"next_cursor": None},
        },
        status=200,
    )

    item_ref = ItemRef(ref_type="doi", ref_value="10.12345/test")
    citations = discoverer.discover(item_ref)

    # Should skip work without DOI
    assert len(citations) == 0


@pytest.mark.ai_generated
@responses.activate
def test_openalex_doi_resolution_failure() -> None:
    """Test handling when DOI cannot be resolved to OpenAlex ID."""
    discoverer = OpenAlexDiscoverer()

    # Mock failed DOI resolution
    responses.add(
        responses.GET,
        "https://api.openalex.org/works/https://doi.org/10.12345/unknown",
        json={"error": "Work not found"},
        status=404,
    )

    item_ref = ItemRef(ref_type="doi", ref_value="10.12345/unknown")
    citations = discoverer.discover(item_ref)

    # Should return empty list when DOI can't be resolved
    assert len(citations) == 0


@pytest.mark.ai_generated
def test_openalex_rate_limiting(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that rate limiting is applied."""
    discoverer = OpenAlexDiscoverer()

    # Mock time.time() to track sleep calls
    sleep_calls = []

    def mock_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    import time

    monkeypatch.setattr(time, "sleep", mock_sleep)

    # Call rate limit twice quickly
    discoverer._last_request_time = 0.0
    import time as time_module

    monkeypatch.setattr(time_module, "time", lambda: 0.05)  # 0.05s elapsed
    discoverer._rate_limit()

    # Should have slept for remaining time (0.1 - 0.05 = 0.05)
    assert len(sleep_calls) == 1
    assert sleep_calls[0] >= 0.04  # Allow small floating point error
