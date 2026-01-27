"""OpenCitations citation discovery."""

from __future__ import annotations

import logging
import re
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


class OpenCitationsDiscoverer(AbstractDiscoverer):
    """Discover citations via OpenCitations COCI API."""

    BASE_URL = "https://opencitations.net/index/coci/api/v1/citations"
    DOI_API = "https://doi.org"

    def __init__(self) -> None:
        """Initialize OpenCitations discoverer."""
        self.session = requests.Session()

    def discover(self, item_ref: ItemRef, since: datetime | None = None) -> list[CitationRecord]:
        """
        Discover citations from OpenCitations COCI.

        Args:
            item_ref: DOI reference to query
            since: Optional date for incremental updates (creation date filter)

        Returns:
            List of citation records
        """
        if item_ref.ref_type != "doi":
            logger.warning(f"OpenCitations only supports DOI refs, got {item_ref.ref_type}")
            return []

        doi = item_ref.ref_value
        url = f"{self.BASE_URL}/{doi}"

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

            # Apply date filter if provided
            if since:
                creation_date = item.get("creation", "")
                try:
                    # Parse creation date (formats: YYYY-MM, YYYY-MM-DD, YYYY)
                    if creation_date:
                        # Convert to datetime for comparison
                        if len(creation_date) == 4:  # YYYY
                            item_date = datetime.strptime(creation_date, "%Y")
                        elif len(creation_date) == 7:  # YYYY-MM
                            item_date = datetime.strptime(creation_date, "%Y-%m")
                        else:  # YYYY-MM-DD
                            item_date = datetime.strptime(creation_date, "%Y-%m-%d")

                        if item_date < since:
                            continue  # Skip older citations
                except ValueError:
                    pass  # Include if we can't parse date

            # Fetch metadata for the citing DOI
            metadata = self._fetch_doi_metadata(citing_doi)

            # Create citation record with metadata
            citation = CitationRecord(
                item_id="",  # Will be filled by caller
                item_flavor="",  # Will be filled by caller
                citation_doi=citing_doi,
                citation_title=cast(str | None, metadata.get("title")),
                citation_authors=cast(str | None, metadata.get("authors")),
                citation_year=cast(int | None, metadata.get("year")),
                citation_journal=cast(str | None, metadata.get("journal")),
                citation_relationship="Cites",  # type: ignore[arg-type]
                citation_source=CitationSource("opencitations"),
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
                f"{self.DOI_API}/{doi}",
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
