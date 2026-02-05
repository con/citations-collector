"""Data models for citations-collector.

Generated from LinkML schema at schema/citations.yaml.
"""

from __future__ import annotations

from citations_collector.models.generated import (
    CitationRecord as _CitationRecord,
)
from citations_collector.models.generated import (
    CitationRelationship,
    CitationSource,
    CitationStatus,
    CitationType,
    ClassificationMethod,
    Collection,
    CurationConfig,
    CurationRule,
    DiscoverConfig,
    Item,
    ItemFlavor,
    ItemRef,
    PdfsConfig,
    RefType,
    SourceConfig,
    ZoteroConfig,
)
from citations_collector.models.validators import create_citation_record_with_validators

# Apply custom validators to CitationRecord
CitationRecord = create_citation_record_with_validators(_CitationRecord)

__all__ = [
    "CitationRecord",
    "CitationRelationship",
    "CitationSource",
    "CitationStatus",
    "CitationType",
    "ClassificationMethod",
    "Collection",
    "CurationConfig",
    "CurationRule",
    "DiscoverConfig",
    "Item",
    "ItemFlavor",
    "ItemRef",
    "PdfsConfig",
    "RefType",
    "SourceConfig",
    "ZoteroConfig",
]
