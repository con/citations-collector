"""Citation discovery from external APIs."""

from __future__ import annotations

from citations_collector.discovery.base import AbstractDiscoverer
from citations_collector.discovery.crossref import CrossRefDiscoverer
from citations_collector.discovery.datacite import DataCiteDiscoverer
from citations_collector.discovery.openalex import OpenAlexDiscoverer
from citations_collector.discovery.opencitations import OpenCitationsDiscoverer

__all__ = [
    "AbstractDiscoverer",
    "CrossRefDiscoverer",
    "DataCiteDiscoverer",
    "OpenAlexDiscoverer",
    "OpenCitationsDiscoverer",
]
