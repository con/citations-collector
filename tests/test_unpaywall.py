"""Tests for the Unpaywall API client."""

from __future__ import annotations

import pytest
import requests
import responses

from citations_collector.unpaywall import UnpaywallClient


@pytest.mark.ai_generated
@responses.activate
def test_lookup_gold_oa() -> None:
    """Gold OA DOI returns is_oa=True with PDF URL."""
    responses.add(
        responses.GET,
        "https://api.unpaywall.org/v2/10.1234/gold",
        json={
            "doi": "10.1234/gold",
            "is_oa": True,
            "oa_status": "gold",
            "best_oa_location": {
                "url_for_pdf": "https://example.com/paper.pdf",
                "license": "cc-by",
            },
        },
        status=200,
    )

    client = UnpaywallClient(email="test@example.com")
    result = client.lookup("10.1234/gold")

    assert result.is_oa is True
    assert result.oa_status == "gold"
    assert result.best_oa_url == "https://example.com/paper.pdf"
    assert result.license == "cc-by"
    assert result.doi == "10.1234/gold"


@pytest.mark.ai_generated
@responses.activate
def test_lookup_closed() -> None:
    """Closed DOI returns is_oa=False with no PDF URL."""
    responses.add(
        responses.GET,
        "https://api.unpaywall.org/v2/10.1234/closed",
        json={
            "doi": "10.1234/closed",
            "is_oa": False,
            "oa_status": "closed",
            "best_oa_location": None,
        },
        status=200,
    )

    client = UnpaywallClient(email="test@example.com")
    result = client.lookup("10.1234/closed")

    assert result.is_oa is False
    assert result.oa_status == "closed"
    assert result.best_oa_url is None
    assert result.license is None


@pytest.mark.ai_generated
@responses.activate
def test_lookup_404() -> None:
    """DOI not found returns closed gracefully."""
    responses.add(
        responses.GET,
        "https://api.unpaywall.org/v2/10.1234/missing",
        status=404,
    )

    client = UnpaywallClient(email="test@example.com")
    result = client.lookup("10.1234/missing")

    assert result.is_oa is False
    assert result.oa_status == "closed"
    assert result.best_oa_url is None


@pytest.mark.ai_generated
@responses.activate
def test_lookup_network_error() -> None:
    """Network error returns closed gracefully."""
    responses.add(
        responses.GET,
        "https://api.unpaywall.org/v2/10.1234/fail",
        body=requests.ConnectionError("connection refused"),
    )

    client = UnpaywallClient(email="test@example.com")
    result = client.lookup("10.1234/fail")

    assert result.is_oa is False
    assert result.oa_status == "closed"
    assert result.best_oa_url is None
