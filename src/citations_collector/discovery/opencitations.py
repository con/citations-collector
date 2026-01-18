"""OpenCitations citation discovery."""

from __future__ import annotations

import logging
from datetime import datetime

import requests

from citations_collector.discovery.base import AbstractDiscoverer
from citations_collector.models import CitationRecord, CitationSource, ItemRef

logger = logging.getLogger(__name__)


class OpenCitationsDiscoverer(AbstractDiscoverer):
    """Discover citations via OpenCitations (OCI) API."""

    BASE_URL = "https://opencitations.net/index/api/v2/citations"

    def __init__(self) -> None:
        """Initialize OpenCitations discoverer."""
        self.session = requests.Session()

    def discover(self, item_ref: ItemRef, since: datetime | None = None) -> list[CitationRecord]:
        """
        Discover citations from OpenCitations.

        Args:
            item_ref: DOI reference to query
            since: Optional date for incremental updates (filter=date:>YYYY-MM-DD)

        Returns:
            List of citation records
        """
        if item_ref.ref_type != "doi":
            logger.warning(f"OpenCitations only supports DOI refs, got {item_ref.ref_type}")
            return []

        doi = item_ref.ref_value
        url = f"{self.BASE_URL}/{doi}"

        # Add date filter if provided
        if since:
            date_str = since.strftime("%Y-%m-%d")
            url = f"{url}?filter=date:>{date_str}"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.warning(f"OpenCitations API error for {doi}: {e}")
            return []

        # Parse citations from response
        citations = []
        if not isinstance(data, list):
            data = [data]

        for item in data:
            citing_doi = item.get("citing")
            if not citing_doi:
                continue

            # Create citation record
            citation = CitationRecord(
                item_id="",  # Will be filled by caller
                item_flavor="",  # Will be filled by caller
                citation_doi=citing_doi,
                citation_relationship="Cites",  # type: ignore[arg-type]
                citation_source=CitationSource("opencitations"),
                citation_status="active",  # type: ignore[arg-type]
            )
            citations.append(citation)

        return citations
