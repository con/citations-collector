"""CrossRef citation discovery."""

from __future__ import annotations

import logging
from datetime import datetime

import requests

from citations_collector.discovery.base import AbstractDiscoverer
from citations_collector.models import CitationRecord, CitationSource, ItemRef

logger = logging.getLogger(__name__)


class CrossRefDiscoverer(AbstractDiscoverer):
    """Discover citations via CrossRef cited-by API."""

    BASE_URL = "https://api.crossref.org/works"

    def __init__(self, email: str | None = None) -> None:
        """
        Initialize CrossRef discoverer.

        Args:
            email: Email for polite pool (better rate limits)
        """
        self.email = email
        self.session = requests.Session()
        if email:
            self.session.headers["User-Agent"] = f"citations-collector (mailto:{email})"

    def discover(
        self, item_ref: ItemRef, since: datetime | None = None
    ) -> list[CitationRecord]:
        """
        Discover citations from CrossRef.

        Args:
            item_ref: DOI reference to query
            since: Optional date for incremental updates (from-index-date filter)

        Returns:
            List of citation records
        """
        if item_ref.ref_type != "doi":
            logger.warning(f"CrossRef only supports DOI refs, got {item_ref.ref_type}")
            return []

        doi = item_ref.ref_value
        url = f"{self.BASE_URL}/{doi}"

        # Add date filter if provided
        if since:
            date_str = since.strftime("%Y-%m-%d")
            url = f"{url}?filter=from-index-date:{date_str}"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.warning(f"CrossRef API error for {doi}: {e}")
            return []

        # Parse citations from response
        citations = []
        message = data.get("message", {})
        references = message.get("reference", [])

        for ref in references:
            ref_doi = ref.get("DOI")
            if not ref_doi:
                continue

            # Extract authors
            authors = ref.get("author", [])
            author_str = None
            if authors:
                author_names = [
                    f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors
                ]
                author_str = "; ".join(author_names)

            # Extract year
            year = None
            published = ref.get("published", {})
            date_parts = published.get("date-parts", [[]])
            if date_parts and date_parts[0]:
                year = date_parts[0][0]

            # Extract title
            titles = ref.get("title", [])
            title = titles[0] if titles else None

            # Extract journal
            containers = ref.get("container-title", [])
            journal = containers[0] if containers else None

            # Create citation record
            citation = CitationRecord(
                item_id="",  # Will be filled by caller
                item_flavor="",  # Will be filled by caller
                citation_doi=ref_doi,
                citation_title=title,
                citation_authors=author_str,
                citation_year=year,
                citation_journal=journal,
                citation_relationship="Cites",
                citation_source=CitationSource("crossref"),
                citation_status="active",
            )
            citations.append(citation)

        return citations
