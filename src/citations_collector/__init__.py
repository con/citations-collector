"""citations-collector: Discover and curate scholarly citations of datasets and software."""

from __future__ import annotations

from citations_collector.core import CitationCollector
from citations_collector.models import CitationRecord, Collection

__all__ = [
    "__version__",
    "CitationCollector",
    "CitationRecord",
    "Collection",
]

try:
    from citations_collector._version import version as __version__
except ImportError:
    __version__ = "0.0.0+unknown"
