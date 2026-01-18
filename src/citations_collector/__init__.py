"""citations-collector: Discover and curate scholarly citations of datasets and software."""

from __future__ import annotations

__all__ = [
    "__version__",
]

try:
    from citations_collector._version import version as __version__
except ImportError:
    __version__ = "0.0.0+unknown"
