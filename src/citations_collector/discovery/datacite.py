"""DataCite citation discovery via Event Data API."""

from __future__ import annotations

import logging
from contextlib import suppress
from datetime import datetime

import requests

from citations_collector.discovery.base import AbstractDiscoverer
from citations_collector.models import CitationRecord, CitationSource, ItemRef

logger = logging.getLogger(__name__)


class DataCiteDiscoverer(AbstractDiscoverer):
    """
    Discover citations via DataCite Event Data API.

    DataCite Event Data tracks citation events from various sources including
    Crossref, DataCite, and others. This provides broader coverage than just
    DataCite-registered content.
    """

    # DataCite Event Data API for citation events
    EVENT_DATA_URL = "https://api.datacite.org/events"

    def __init__(self) -> None:
        """Initialize DataCite discoverer."""
        self.session = requests.Session()

    def discover(self, item_ref: ItemRef, since: datetime | None = None) -> list[CitationRecord]:
        """
        Discover citations from DataCite Event Data.

        Queries the Event Data API for citation events where the target is
        the given DOI.

        Args:
            item_ref: DOI reference to query
            since: Optional date for incremental updates

        Returns:
            List of citation records
        """
        if item_ref.ref_type != "doi":
            logger.warning(f"DataCite only supports DOI refs, got {item_ref.ref_type}")
            return []

        doi = item_ref.ref_value
        # Query for events where this DOI is cited (is-referenced-by relation)
        params: dict[str, str | int] = {
            "obj-id": doi,
            "relation-type-id": "is-referenced-by",
            "page[size]": 1000,  # Max results per page
        }

        # Add date filter if provided
        if since:
            params["occurred-since"] = since.strftime("%Y-%m-%d")

        try:
            response = self.session.get(
                self.EVENT_DATA_URL,
                params=params,
                timeout=30,  # type: ignore[arg-type]
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.warning(f"DataCite Event Data API error for {doi}: {e}")
            return []

        # Parse citation events
        citations = []
        events = data.get("data", [])

        for event in events:
            attributes = event.get("attributes", {})
            subj = attributes.get("subj", {})

            # Extract citing work DOI
            subj_id = subj.get("pid")
            if not subj_id:
                continue

            # Remove doi: prefix if present
            citing_doi = subj_id.replace("https://doi.org/", "").replace("doi:", "")

            # Extract metadata
            title = subj.get("title")
            year = None
            if "published" in subj:
                with suppress(ValueError, TypeError):
                    year = int(subj["published"][:4])

            # Create citation record
            citation = CitationRecord(
                item_id="",  # Will be filled by caller
                item_flavor="",  # Will be filled by caller
                citation_doi=citing_doi,
                citation_title=title,
                citation_year=year,
                citation_relationship="Cites",  # type: ignore[arg-type]
                citation_source=CitationSource("datacite"),
                citation_status="active",  # type: ignore[arg-type]
            )
            citations.append(citation)

        return citations
