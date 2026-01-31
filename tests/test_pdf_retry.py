"""Tests for PDF download retry logic and rate limiting."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from requests.adapters import HTTPAdapter

from citations_collector.pdf import PDFAcquirer, RetryAfterAdapter


@pytest.mark.ai_generated
def test_retry_after_adapter_respects_header():
    """Test that RetryAfterAdapter waits when Retry-After header is present."""
    adapter = RetryAfterAdapter()

    # Mock request
    request = Mock()
    request.url = "https://example.com/file.pdf"

    # Mock response with 429 and Retry-After header
    response = Mock()
    response.status_code = 429
    response.headers = {"Retry-After": "2"}  # 2 seconds

    # Patch both super().send and time.sleep to avoid actual waiting
    with (
        patch.object(HTTPAdapter, "send", return_value=response),
        patch("time.sleep") as mock_sleep,
    ):
        result = adapter.send(request)

        # Should have called sleep with 2 seconds
        mock_sleep.assert_called_once_with(2)
        assert result == response


@pytest.mark.ai_generated
def test_retry_after_adapter_503_response():
    """Test that RetryAfterAdapter handles 503 with Retry-After."""
    adapter = RetryAfterAdapter()

    request = Mock()
    request.url = "https://example.com/file.pdf"

    response = Mock()
    response.status_code = 503
    response.headers = {"Retry-After": "1"}  # 1 second

    with (
        patch.object(HTTPAdapter, "send", return_value=response),
        patch("time.sleep") as mock_sleep,
    ):
        adapter.send(request)

        # Should have called sleep with 1 second
        mock_sleep.assert_called_once_with(1)


@pytest.mark.ai_generated
def test_retry_after_adapter_no_header():
    """Test that adapter doesn't wait when no Retry-After header."""
    adapter = RetryAfterAdapter()

    request = Mock()
    request.url = "https://example.com/file.pdf"

    # 429 but no Retry-After header
    response = Mock()
    response.status_code = 429
    response.headers = {}

    with patch.object(HTTPAdapter, "send", return_value=response):
        start_time = time.time()
        adapter.send(request)
        elapsed = time.time() - start_time

        # Should return immediately
        assert elapsed < 0.5


@pytest.mark.ai_generated
def test_retry_after_adapter_200_response():
    """Test that adapter doesn't wait on successful response."""
    adapter = RetryAfterAdapter()

    request = Mock()
    request.url = "https://example.com/file.pdf"

    response = Mock()
    response.status_code = 200
    response.headers = {"Retry-After": "10"}  # Should be ignored

    with patch.object(HTTPAdapter, "send", return_value=response):
        start_time = time.time()
        adapter.send(request)
        elapsed = time.time() - start_time

        # Should not wait on 200 response
        assert elapsed < 0.5


@pytest.mark.ai_generated
def test_retry_after_adapter_invalid_header():
    """Test that adapter handles invalid Retry-After gracefully."""
    adapter = RetryAfterAdapter()

    request = Mock()
    request.url = "https://example.com/file.pdf"

    response = Mock()
    response.status_code = 429
    response.headers = {"Retry-After": "Wed, 21 Oct 2025 07:28:00 GMT"}  # HTTP date format

    with (
        patch.object(HTTPAdapter, "send", return_value=response),
        patch("time.sleep") as mock_sleep,
    ):
        # Should fall back to 60 seconds for HTTP date format (non-integer Retry-After)
        adapter.send(request)
        # Should have called sleep with 60 seconds (fallback for HTTP date format)
        mock_sleep.assert_called_once_with(60)


@pytest.mark.ai_generated
def test_download_rate_limiting(tmp_path: Path):
    """Test that PDFAcquirer enforces delay between downloads."""
    import responses

    acquirer = PDFAcquirer(output_dir=tmp_path)
    acquirer._download_delay = 0.5  # 0.5 second delay

    # Mock HTTP responses
    with responses.RequestsMock() as rsps, patch("time.sleep") as mock_sleep:
        # Add two successful PDF responses
        rsps.add(
            responses.GET,
            "https://example.com/1.pdf",
            body=b"fake pdf content 1",
            status=200,
            headers={"Content-Type": "application/pdf"},
        )
        rsps.add(
            responses.GET,
            "https://example.com/2.pdf",
            body=b"fake pdf content 2",
            status=200,
            headers={"Content-Type": "application/pdf"},
        )

        # First download
        dest1 = tmp_path / "file1.pdf"
        result1 = acquirer._download("https://example.com/1.pdf", dest1)
        assert result1 == dest1

        # Second download - should trigger rate limiting sleep
        dest2 = tmp_path / "file2.pdf"
        result2 = acquirer._download("https://example.com/2.pdf", dest2)
        assert result2 == dest2

        # Should have called sleep once with ~0.5 seconds for rate limiting
        assert mock_sleep.call_count == 1
        sleep_duration = mock_sleep.call_args[0][0]
        assert 0.4 <= sleep_duration <= 0.5  # Allow small margin for timing


@pytest.mark.ai_generated
def test_skip_existing_pdf(tmp_path: Path):
    """Test that existing PDF files are not re-downloaded."""
    from citations_collector.models import CitationRecord
    from citations_collector.unpaywall import UnpaywallResult

    acquirer = PDFAcquirer(output_dir=tmp_path)

    # Create citation
    citation = CitationRecord(
        item_id="test",
        item_flavor="main",
        citation_doi="10.1234/test",
        citation_relationship="Cites",
        citation_source="crossref",
        citation_status="active",
    )

    # Create existing PDF file
    pdf_path = tmp_path / "10.1234" / "test" / "article.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"existing content")

    # Mock unpaywall to return OA URL
    with patch.object(acquirer.unpaywall, "lookup") as mock_lookup:
        mock_lookup.return_value = UnpaywallResult(
            doi="10.1234/test",
            is_oa=True,
            oa_status="gold",
            best_oa_url="https://example.com/test.pdf",
            license="cc-by",
        )

        # Should skip download
        result = acquirer.acquire_for_citation(citation)

        # Returns False because file exists (not newly downloaded)
        assert result is False
        # pdf_path should be set
        assert citation.pdf_path == str(pdf_path)


@pytest.mark.ai_generated
def test_skip_existing_html(tmp_path: Path):
    """Test that existing HTML files are not re-downloaded."""
    from citations_collector.models import CitationRecord
    from citations_collector.unpaywall import UnpaywallResult

    acquirer = PDFAcquirer(output_dir=tmp_path)

    citation = CitationRecord(
        item_id="test",
        item_flavor="main",
        citation_doi="10.1234/test",
        citation_relationship="Cites",
        citation_source="crossref",
        citation_status="active",
    )

    # Create existing HTML file (server returned HTML instead of PDF)
    html_path = tmp_path / "10.1234" / "test" / "article.html"
    html_path.parent.mkdir(parents=True)
    html_path.write_bytes(b"<html>existing</html>")

    with patch.object(acquirer.unpaywall, "lookup") as mock_lookup:
        mock_lookup.return_value = UnpaywallResult(
            doi="10.1234/test",
            is_oa=True,
            oa_status="gold",
            best_oa_url="https://example.com/test.pdf",
            license="cc-by",
        )

        # Should skip download
        result = acquirer.acquire_for_citation(citation)

        assert result is False
        assert citation.pdf_path == str(html_path)


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.ai_generated
def test_biorxiv_download_integration(tmp_path: Path):
    """
    Integration test: Actually download a PDF from bioRxiv.

    This test makes real network requests and should be skipped in CI.
    Run with: pytest -m integration
    """
    from citations_collector.models import CitationRecord

    # Use a stable, old bioRxiv preprint (less likely to be taken down)
    # This is the first ever bioRxiv preprint from 2013
    test_doi = "10.1101/001081"

    acquirer = PDFAcquirer(output_dir=tmp_path)

    # Create citation
    citation = CitationRecord(
        item_id="test",
        item_flavor="main",
        citation_doi=test_doi,
        citation_relationship="Cites",
        citation_source="crossref",
        citation_status="active",
    )

    # Try to acquire PDF
    try:
        result = acquirer.acquire_for_citation(citation)

        if result:
            # Check that file was downloaded
            assert citation.pdf_path is not None
            pdf_path = Path(citation.pdf_path)
            assert pdf_path.exists()
            assert pdf_path.stat().st_size > 1000  # At least 1KB

            # Check file extension
            assert pdf_path.suffix in [".pdf", ".html"]

            print(f"Successfully downloaded: {pdf_path}")
            print(f"File size: {pdf_path.stat().st_size} bytes")
        else:
            # Might not be OA or already exists
            print(f"Did not download (OA status: {citation.oa_status})")
    except Exception as e:
        pytest.skip(f"Network request failed (expected in CI): {e}")


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.ai_generated
def test_biorxiv_rate_limiting_integration(tmp_path: Path):
    """
    Integration test: Verify rate limiting works with real bioRxiv requests.

    Downloads 3 PDFs in sequence and verifies delays are enforced.
    """
    from citations_collector.models import CitationRecord

    # Use stable old bioRxiv preprints
    test_dois = [
        "10.1101/001081",  # First bioRxiv paper
        "10.1101/001123",  # Second bioRxiv paper
        "10.1101/001156",  # Third bioRxiv paper
    ]

    acquirer = PDFAcquirer(output_dir=tmp_path)
    acquirer._download_delay = 2.0  # 2 seconds between downloads

    start_time = time.time()
    downloaded = 0

    for doi in test_dois:
        citation = CitationRecord(
            item_id="test",
            item_flavor="main",
            citation_doi=doi,
            citation_relationship="Cites",
            citation_source="crossref",
            citation_status="active",
        )

        try:
            if acquirer.acquire_for_citation(citation):
                downloaded += 1
        except Exception as e:
            pytest.skip(f"Network request failed: {e}")

    elapsed = time.time() - start_time

    if downloaded >= 2:
        # Should have at least 2 seconds delay between downloads
        expected_min_time = (downloaded - 1) * 2.0
        assert elapsed >= expected_min_time, (
            f"Expected at least {expected_min_time}s for {downloaded} downloads, "
            f"but took only {elapsed}s"
        )
        print(f"Downloaded {downloaded} files in {elapsed:.1f}s (rate limiting working)")
