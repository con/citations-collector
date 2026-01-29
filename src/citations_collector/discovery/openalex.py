"""OpenAlex citation discovery."""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from typing import Any

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


class OpenAlexDiscoverer(AbstractDiscoverer):
    """Discover citations via OpenAlex API."""

    BASE_URL = "https://api.openalex.org"
    RATE_LIMIT_DELAY = 0.1  # 10 requests/second = 0.1s between requests

    def __init__(self, email: str | None = None, api_key: str | None = None) -> None:
        """
        Initialize OpenAlex discoverer.

        Args:
            email: Email for polite pool (adds to User-Agent)
            api_key: Optional API key for higher rate limits
        """
        self.email = email
        self.api_key = api_key
        self.session = requests.Session()

        # Set User-Agent with mailto for polite pool
        user_agent = "citations-collector"
        if email:
            user_agent += f" (mailto:{email})"
        self.session.headers["User-Agent"] = user_agent

        self._last_request_time = 0.0

    def discover(self, item_ref: ItemRef, since: datetime | None = None) -> list[CitationRecord]:
        """
        Discover citations from OpenAlex.

        Args:
            item_ref: DOI reference to query
            since: Optional date for incremental updates (from-publication-date filter)

        Returns:
            List of citation records
        """
        if item_ref.ref_type != "doi":
            logger.warning(f"OpenAlex only supports DOI refs, got {item_ref.ref_type}")
            return []

        doi = item_ref.ref_value

        # Query OpenAlex for works that cite this DOI
        # Filter format: cites:https://doi.org/{doi}
        citations = []
        cursor = "*"  # OpenAlex uses cursor-based pagination

        while cursor:
            self._rate_limit()

            params: dict[str, Any] = {
                "filter": f"cites:https://doi.org/{doi}",
                "per-page": 200,  # Max per page
                "cursor": cursor,
            }

            if self.email:
                params["mailto"] = self.email

            # Add date filter if provided
            if since:
                date_str = since.strftime("%Y-%m-%d")
                params["filter"] += f",from_publication_date:{date_str}"

            try:
                response = self.session.get(
                    f"{self.BASE_URL}/works",
                    params=params,
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()
            except requests.RequestException as e:
                logger.warning(f"OpenAlex API error for {doi}: {e}")
                break

            # Parse results
            results = data.get("results", [])
            for work in results:
                citation = self._parse_work(work)
                if citation:
                    citations.append(citation)

            # Check for next page
            meta = data.get("meta", {})
            cursor = meta.get("next_cursor")

            # Stop if we've processed all results
            if not cursor or not results:
                break

        logger.info(f"Found {len(citations)} citations for {doi} via OpenAlex")
        return citations

    def _rate_limit(self) -> None:
        """Implement rate limiting to stay under 10 req/sec."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()

    def _parse_work(self, work: dict[str, Any]) -> CitationRecord | None:
        """
        Parse an OpenAlex work into a CitationRecord.

        Args:
            work: OpenAlex work object

        Returns:
            CitationRecord or None if missing required fields
        """
        # Extract DOI
        doi = work.get("doi")
        if not doi:
            return None

        # Remove https://doi.org/ prefix if present
        doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")

        if not doi.startswith("10."):
            return None

        # Extract title
        title = _sanitize_text(work.get("title"))

        # Extract authors
        authorships = work.get("authorships", [])
        authors = []
        for authorship in authorships:
            author_obj = authorship.get("author", {})
            display_name = author_obj.get("display_name")
            if display_name:
                authors.append(display_name)
        authors_str = _sanitize_text("; ".join(authors)) if authors else None

        # Extract year
        pub_year = work.get("publication_year")

        # Extract journal/venue
        primary_location = work.get("primary_location", {})
        source = primary_location.get("source", {})
        journal = _sanitize_text(source.get("display_name"))

        # Determine citation type based on work type
        work_type = work.get("type")
        citation_type = self._map_work_type(work_type)

        return CitationRecord(
            item_id="",  # Will be filled by caller
            item_flavor="",  # Will be filled by caller
            citation_doi=doi,
            citation_title=title,
            citation_authors=authors_str,
            citation_year=pub_year,
            citation_journal=journal,
            citation_type=citation_type,  # type: ignore[arg-type]
            citation_relationship="Cites",  # type: ignore[arg-type]
            citation_source=CitationSource("openalex"),
            citation_status="active",  # type: ignore[arg-type]
        )

    def _map_work_type(self, work_type: str | None) -> str | None:
        """
        Map OpenAlex work type to CitationType.

        OpenAlex types: article, book, dataset, paratext, preprint, etc.
        See: https://docs.openalex.org/api-entities/works/work-object#type
        """
        if not work_type:
            return None

        type_mapping = {
            "article": "Publication",
            "book-chapter": "Book",
            "monograph": "Book",
            "book": "Book",
            "dataset": "Dataset",
            "preprint": "Preprint",
            "posted-content": "Preprint",
            "dissertation": "Thesis",
            "other": "Other",
        }

        return type_mapping.get(work_type.lower(), "Other")
