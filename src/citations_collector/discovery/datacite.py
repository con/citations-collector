"""DataCite citation discovery."""

from __future__ import annotations

import logging
from datetime import datetime

import requests

from citations_collector.discovery.base import AbstractDiscoverer
from citations_collector.models import CitationRecord, ItemRef

logger = logging.getLogger(__name__)


class DataCiteDiscoverer(AbstractDiscoverer):
    """Discover citations via DataCite API."""

    BASE_URL = "https://api.datacite.org/dois"

    def __init__(self) -> None:
        """Initialize DataCite discoverer."""
        self.session = requests.Session()

    def discover(
        self, item_ref: ItemRef, since: datetime | None = None
    ) -> list[CitationRecord]:
        """
        Discover citations from DataCite.

        Args:
            item_ref: DOI reference to query
            since: Optional date for incremental updates

        Returns:
            List of citation records
        """
        if item_ref.ref_type != "doi":
            logger.warning(f"DataCite only supports DOI refs, got {item_ref.ref_type}")
            return []

        # DataCite implementation placeholder
        # Full implementation would query DataCite's citation API
        logger.info("DataCite discoverer not yet implemented")
        return []
