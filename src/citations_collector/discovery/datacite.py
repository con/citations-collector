"""DataCite citation discovery via Event Data API and DOI metadata API."""

from __future__ import annotations

import logging
import re
from contextlib import suppress
from datetime import datetime
from typing import cast

import requests

from citations_collector.discovery.base import AbstractDiscoverer
from citations_collector.models import CitationRecord, CitationSource, ItemRef

logger = logging.getLogger(__name__)


def _sanitize_text(text: str | None) -> str | None:
    """Sanitize text for TSV output - normalize whitespace, remove control chars."""
    if text is None:
        return None
    # Replace newlines, tabs, carriage returns with spaces
    text = re.sub(r"[\n\r\t]+", " ", text)
    # Collapse multiple spaces
    text = re.sub(r" +", " ", text)
    # Strip leading/trailing whitespace
    return text.strip() or None


class DataCiteDiscoverer(AbstractDiscoverer):
    """
    Discover citations via DataCite APIs.

    Uses two approaches:
    1. Event Data API - tracks citation events from various sources
    2. DOI Metadata API - relationships.citations from DOI records

    This provides broader coverage for DataCite-registered content (datasets, etc.).
    """

    # DataCite Event Data API for citation events
    EVENT_DATA_URL = "https://api.datacite.org/events"
    # DataCite DOI Metadata API
    DOI_API_URL = "https://api.datacite.org/dois"
    # DOI content negotiation for metadata
    DOI_ORG = "https://doi.org"

    def __init__(self) -> None:
        """Initialize DataCite discoverer."""
        self.session = requests.Session()

    def discover(self, item_ref: ItemRef, since: datetime | None = None) -> list[CitationRecord]:
        """
        Discover citations from DataCite.

        Queries both Event Data API and DOI relationships endpoint.

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
        seen_dois: set[str] = set()
        citations = []

        # Method 1: Event Data API
        event_citations = self._discover_from_events(doi, since)
        for citation in event_citations:
            if citation.citation_doi and citation.citation_doi not in seen_dois:
                seen_dois.add(citation.citation_doi)
                citations.append(citation)

        # Method 2: DOI relationships.citations (what SPARC-Citations uses)
        rel_citations = self._discover_from_relationships(doi)
        for citation in rel_citations:
            if citation.citation_doi and citation.citation_doi not in seen_dois:
                seen_dois.add(citation.citation_doi)
                citations.append(citation)

        return citations

    def _discover_from_events(
        self, doi: str, since: datetime | None = None
    ) -> list[CitationRecord]:
        """Query DataCite Event Data API for citation events."""
        # DataCite requires full DOI URL and uses "references" relation type
        doi_url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
        params: dict[str, str | int] = {
            "obj-id": doi_url,
            "relation-type-id": "references",
            "page[size]": 1000,
        }

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

        citations = []
        events = data.get("data", [])

        for event in events:
            attributes = event.get("attributes", {})
            subj = attributes.get("subj", {})

            subj_id = subj.get("pid")
            if not subj_id:
                continue

            citing_doi = subj_id.replace("https://doi.org/", "").replace("doi:", "")

            # Get metadata from event or fetch via DOI
            title = _sanitize_text(subj.get("title"))
            year = None
            if "published" in subj:
                with suppress(ValueError, TypeError):
                    year = int(subj["published"][:4])

            # If missing metadata, fetch from DOI
            if not title:
                metadata = self._fetch_doi_metadata(citing_doi)
                title = cast(str | None, metadata.get("title"))  # Already sanitized
                if not year:
                    year = cast(int | None, metadata.get("year"))
                authors = cast(str | None, metadata.get("authors"))
                journal = cast(str | None, metadata.get("journal"))
            else:
                authors = None
                journal = None

            citation = CitationRecord(
                item_id="",
                item_flavor="",
                citation_doi=citing_doi,
                citation_title=title,
                citation_authors=authors,
                citation_year=year,
                citation_journal=journal,
                citation_relationship="Cites",  # type: ignore[arg-type]
                citation_source=CitationSource("datacite"),
                citation_status="active",  # type: ignore[arg-type]
            )
            citations.append(citation)

        return citations

    def _discover_from_relationships(self, doi: str) -> list[CitationRecord]:
        """Query DataCite DOI API for relationships.citations."""
        url = f"{self.DOI_API_URL}/{doi}"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.debug(f"DataCite DOI API error for {doi}: {e}")
            return []

        citations = []

        # Navigate to relationships.citations.data
        relationships = data.get("data", {}).get("relationships", {})
        citations_data = relationships.get("citations", {}).get("data", [])

        for citation_entry in citations_data:
            citing_doi = citation_entry.get("id")
            if not citing_doi:
                continue

            # Fetch metadata for the citing DOI
            metadata = self._fetch_doi_metadata(citing_doi)

            citation = CitationRecord(
                item_id="",
                item_flavor="",
                citation_doi=citing_doi,
                citation_title=cast(str | None, metadata.get("title")),
                citation_authors=cast(str | None, metadata.get("authors")),
                citation_year=cast(int | None, metadata.get("year")),
                citation_journal=cast(str | None, metadata.get("journal")),
                citation_relationship="Cites",  # type: ignore[arg-type]
                citation_source=CitationSource("datacite"),
                citation_status="active",  # type: ignore[arg-type]
            )
            citations.append(citation)

        return citations

    def _fetch_doi_metadata(self, doi: str) -> dict[str, str | int | None]:
        """
        Fetch metadata for a DOI via content negotiation.

        Args:
            doi: The DOI to fetch metadata for

        Returns:
            Dictionary with title, authors, year, journal
        """
        metadata: dict[str, str | int | None] = {
            "title": None,
            "authors": None,
            "year": None,
            "journal": None,
        }

        try:
            response = self.session.get(
                f"{self.DOI_ORG}/{doi}",
                headers={"Accept": "application/json"},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            # Extract title (sanitize for TSV)
            metadata["title"] = _sanitize_text(data.get("title"))

            # Extract authors
            authors = data.get("author", [])
            if authors:
                author_names = [
                    f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors
                ]
                metadata["authors"] = _sanitize_text("; ".join(author_names))

            # Extract year
            published = data.get("published", {})
            date_parts = published.get("date-parts", [[]])
            if date_parts and len(date_parts[0]) > 0:
                metadata["year"] = date_parts[0][0]

            # Extract journal (may be string or list, sanitize for TSV)
            container = data.get("container-title")
            if isinstance(container, list):
                metadata["journal"] = _sanitize_text(container[0]) if container else None
            else:
                metadata["journal"] = _sanitize_text(container)

        except requests.RequestException as e:
            logger.debug(f"Failed to fetch metadata for DOI {doi}: {e}")

        return metadata
