"""Abstract base class for citation discoverers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from citations_collector.models import CitationRecord, ItemRef


class AbstractDiscoverer(ABC):
    """Base class for citation discovery APIs."""

    @abstractmethod
    def discover(self, item_ref: ItemRef, since: datetime | None = None) -> list[CitationRecord]:
        """
        Discover citations for a given item reference.

        Args:
            item_ref: The identifier to query (DOI, RRID, etc.)
            since: Optional date filter for incremental updates

        Returns:
            List of discovered citation records
        """
        pass
