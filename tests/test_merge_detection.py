"""Tests for merge detection (preprint -> published version)."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
import requests

from citations_collector.merge_detection import MergeDetector
from citations_collector.models.generated import CitationRecord


@pytest.fixture
def detector():
    """Create a MergeDetector instance."""
    return MergeDetector(email="test@example.com")


@pytest.fixture
def preprint_citation():
    """Create a sample preprint citation."""
    return CitationRecord(
        item_id="test_dataset",
        item_flavor="v1.0",
        citation_doi="10.1101/2023.01.01.123456",
        citation_title="A Study of Neural Networks",
        citation_relationship="Cites",
        citation_source="crossref",
        citation_status="active",
    )


@pytest.fixture
def published_citation():
    """Create a sample published citation."""
    return CitationRecord(
        item_id="test_dataset",
        item_flavor="v1.0",
        citation_doi="10.1234/journal.2023.001",
        citation_title="A Study of Neural Networks",
        citation_relationship="Cites",
        citation_source="crossref",
        citation_status="active",
    )


@pytest.mark.ai_generated
def test_is_preprint_server(detector):
    """Test identification of preprint server DOIs."""
    assert detector._is_preprint_server("10.1101/2023.01.01.123456")  # bioRxiv
    assert detector._is_preprint_server("10.31219/osf.io/abc123")  # OSF
    assert detector._is_preprint_server("10.48550/arXiv.2301.00001")  # arXiv
    assert not detector._is_preprint_server("10.1234/journal.2023.001")


@pytest.mark.ai_generated
def test_get_published_version_with_relationship(detector):
    """Test detecting published version via CrossRef is-preprint-of relationship."""
    crossref_response = {
        "message": {
            "DOI": "10.1101/2023.01.01.123456",
            "relation": {
                "is-preprint-of": [
                    {
                        "id": "10.1234/journal.2023.001",
                        "id-type": "doi",
                        "asserted-by": "object",
                    }
                ]
            },
        }
    }

    with patch.object(detector.session, "get") as mock_get:
        mock_response = Mock()
        mock_response.json.return_value = crossref_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = detector._get_published_version("10.1101/2023.01.01.123456")
        assert result == "10.1234/journal.2023.001"


@pytest.mark.ai_generated
def test_get_published_version_with_url_id(detector):
    """Test extracting DOI from full URL in CrossRef response."""
    crossref_response = {
        "message": {
            "DOI": "10.1101/2023.01.01.123456",
            "relation": {
                "is-preprint-of": [
                    {
                        "id": "https://doi.org/10.1234/journal.2023.001",
                        "id-type": "doi",
                    }
                ]
            },
        }
    }

    with patch.object(detector.session, "get") as mock_get:
        mock_response = Mock()
        mock_response.json.return_value = crossref_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = detector._get_published_version("10.1101/2023.01.01.123456")
        assert result == "10.1234/journal.2023.001"


@pytest.mark.ai_generated
def test_get_published_version_no_relationship(detector):
    """Test when no published version relationship exists."""
    crossref_response = {
        "message": {
            "DOI": "10.1101/2023.01.01.123456",
            "relation": {},
        }
    }

    with patch.object(detector.session, "get") as mock_get:
        mock_response = Mock()
        mock_response.json.return_value = crossref_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = detector._get_published_version("10.1101/2023.01.01.123456")
        assert result is None


@pytest.mark.ai_generated
def test_get_published_version_network_error(detector):
    """Test handling of network errors when querying CrossRef."""
    with patch.object(detector.session, "get") as mock_get:
        mock_get.side_effect = requests.RequestException("Network error")

        result = detector._get_published_version("10.1101/2023.01.01.123456")
        assert result is None


@pytest.mark.ai_generated
def test_verify_doi_exists_success(detector):
    """Test verifying that a DOI exists."""
    with patch.object(detector.session, "get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = detector._verify_doi_exists("10.1234/journal.2023.001")
        assert result is True


@pytest.mark.ai_generated
def test_verify_doi_exists_not_found(detector):
    """Test when DOI doesn't exist."""
    with patch.object(detector.session, "get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = detector._verify_doi_exists("10.1234/nonexistent")
        assert result is False


@pytest.mark.ai_generated
def test_detect_merged_pairs(detector, preprint_citation, published_citation):
    """Test detecting merged pairs in a citation list."""
    citations = [preprint_citation, published_citation]

    def mock_get_published_version(doi):
        # Only return published version for the preprint
        if doi == preprint_citation.citation_doi:
            return published_citation.citation_doi
        return None

    with (
        patch.object(detector, "_get_published_version", side_effect=mock_get_published_version),
        patch.object(detector, "_verify_doi_exists", return_value=True),
    ):
        merged_pairs = detector.detect_merged_pairs(citations)

        assert len(merged_pairs) == 1
        assert merged_pairs[preprint_citation.citation_doi] == published_citation.citation_doi


@pytest.mark.ai_generated
def test_detect_merged_pairs_published_not_in_dataset(detector, preprint_citation):
    """Test when published version exists but is not in our dataset."""
    citations = [preprint_citation]

    with (
        patch.object(detector, "_get_published_version", return_value="10.1234/external.001"),
        patch.object(detector, "_verify_doi_exists", return_value=True),
    ):
        merged_pairs = detector.detect_merged_pairs(citations)

        # Should still detect the merge since DOI exists
        assert len(merged_pairs) == 1
        assert merged_pairs[preprint_citation.citation_doi] == "10.1234/external.001"


@pytest.mark.ai_generated
def test_mark_merged_citations(detector, preprint_citation, published_citation):
    """Test marking citations as merged."""
    citations = [preprint_citation, published_citation]
    merged_pairs = {preprint_citation.citation_doi: published_citation.citation_doi}

    marked = detector.mark_merged_citations(citations, merged_pairs)

    assert marked == 1
    assert preprint_citation.citation_status == "merged"
    assert preprint_citation.citation_merged_into == published_citation.citation_doi
    # Published version should remain active
    assert published_citation.citation_status == "active"


@pytest.mark.ai_generated
def test_fuzzy_match_by_title(detector):
    """Test fuzzy title matching for potential merges."""
    preprint = CitationRecord(
        item_id="test_dataset",
        item_flavor="v1.0",
        citation_doi="10.1101/2023.01.01.123456",
        citation_title="A Study of Neural Networks in Brain Imaging",
        citation_relationship="Cites",
        citation_source="crossref",
        citation_status="active",
    )
    published = CitationRecord(
        item_id="test_dataset",
        item_flavor="v1.0",
        citation_doi="10.1234/journal.2023.001",
        citation_title="A Study of Neural Networks in Brain Imaging",
        citation_relationship="Cites",
        citation_source="crossref",
        citation_status="active",
    )
    unrelated = CitationRecord(
        item_id="test_dataset",
        item_flavor="v1.0",
        citation_doi="10.5678/other.2023.001",
        citation_title="Completely Different Topic",
        citation_relationship="Cites",
        citation_source="crossref",
        citation_status="active",
    )

    citations = [preprint, published, unrelated]
    potential_pairs = detector.fuzzy_match_by_title(citations, threshold=90)

    assert len(potential_pairs) == 1
    assert potential_pairs[preprint.citation_doi] == published.citation_doi


@pytest.mark.ai_generated
def test_fuzzy_match_no_matches_below_threshold(detector):
    """Test fuzzy matching when similarity is below threshold."""
    preprint = CitationRecord(
        item_id="test_dataset",
        item_flavor="v1.0",
        citation_doi="10.1101/2023.01.01.123456",
        citation_title="A Study of Neural Networks",
        citation_relationship="Cites",
        citation_source="crossref",
        citation_status="active",
    )
    published = CitationRecord(
        item_id="test_dataset",
        item_flavor="v1.0",
        citation_doi="10.1234/journal.2023.001",
        citation_title="Completely Different Research on Genomics",
        citation_relationship="Cites",
        citation_source="crossref",
        citation_status="active",
    )

    citations = [preprint, published]
    potential_pairs = detector.fuzzy_match_by_title(citations, threshold=90)

    assert len(potential_pairs) == 0


@pytest.mark.ai_generated
def test_fuzzy_match_handles_missing_titles(detector):
    """Test fuzzy matching gracefully handles missing titles."""
    preprint = CitationRecord(
        item_id="test_dataset",
        item_flavor="v1.0",
        citation_doi="10.1101/2023.01.01.123456",
        citation_title=None,
        citation_relationship="Cites",
        citation_source="crossref",
        citation_status="active",
    )
    published = CitationRecord(
        item_id="test_dataset",
        item_flavor="v1.0",
        citation_doi="10.1234/journal.2023.001",
        citation_title="Some Title",
        citation_relationship="Cites",
        citation_source="crossref",
        citation_status="active",
    )

    citations = [preprint, published]
    potential_pairs = detector.fuzzy_match_by_title(citations)

    assert len(potential_pairs) == 0
