"""CrossRef Event Data citation discovery."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, cast

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


class CrossRefDiscoverer(AbstractDiscoverer):
    """Discover citations via CrossRef Event Data API."""

    BASE_URL = "https://api.eventdata.crossref.org/v1/events"
    DOI_API = "https://doi.org"

    def __init__(self, email: str | None = None) -> None:
        """
        Initialize CrossRef Event Data discoverer.

        Args:
            email: Email for polite pool (better rate limits)
        """
        self.email = email
        self.session = requests.Session()
        if email:
            self.session.headers["User-Agent"] = f"citations-collector (mailto:{email})"

    def discover(self, item_ref: ItemRef, since: datetime | None = None) -> list[CitationRecord]:
        """
        Discover citations from CrossRef Event Data.

        Args:
            item_ref: DOI reference to query
            since: Optional date for incremental updates (from-updated-date filter)

        Returns:
            List of citation records
        """
        if item_ref.ref_type != "doi":
            logger.warning(f"CrossRef only supports DOI refs, got {item_ref.ref_type}")
            return []

        doi = item_ref.ref_value

        # Query CrossRef Event Data for citations
        # obj-id is the DOI being cited, subj-id is the citing work
        params: dict[str, Any] = {"obj-id": doi, "rows": 1000}

        # Add date filter if provided
        if since:
            date_str = since.strftime("%Y-%m-%d")
            params["from-updated-date"] = date_str

        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.warning(f"CrossRef Event Data API error for {doi}: {e}")
            return []

        # Parse citations from events
        citations = []
        events = data.get("message", {}).get("events", [])

        for event in events:
            # Get the citing DOI
            subj = event.get("subj", {})
            citing_doi_url = subj.get("pid", "")

            # Extract DOI from URL (e.g., "https://doi.org/10.1234/abc" -> "10.1234/abc")
            citing_doi = citing_doi_url.replace("https://doi.org/", "").replace(
                "http://doi.org/", ""
            )

            if not citing_doi or not citing_doi.startswith("10."):
                continue

            # Fetch metadata for the citing DOI via DOI content negotiation
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
                citation_source=CitationSource("crossref"),
                citation_status="active",  # type: ignore[arg-type]
            )
            citations.append(citation)

        # Warn if Event Data returned events but they didn't yield valid citations
        if len(events) > 0 and len(citations) == 0:
            logger.info(
                f"CrossRef Event Data returned {len(events)} events for {doi} "
                f"but none were valid DOI-based citations (may be news/blog references)"
            )

        # Also check metadata API if we got 0 citations total
        if len(citations) == 0:
            try:
                meta_resp = self.session.get(f"https://api.crossref.org/works/{doi}", timeout=10)
                if meta_resp.status_code == 200:
                    meta_data = meta_resp.json()
                    cited_by_count = meta_data.get("message", {}).get("is-referenced-by-count", 0)
                    if cited_by_count > 0:
                        logger.warning(
                            f"CrossRef metadata shows {cited_by_count} citations for {doi}, "
                            f"but Event Data API has 0 valid citations. "
                            f"Full cited-by data requires CrossRef membership: "
                            f"https://www.crossref.org/services/cited-by/"
                        )
            except Exception as e:
                logger.debug(f"Failed to check cited-by count for {doi}: {e}")

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
