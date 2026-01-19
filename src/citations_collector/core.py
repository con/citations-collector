"""Core orchestration for citation collection."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from citations_collector.discovery import (
    CrossRefDiscoverer,
    DataCiteDiscoverer,
    OpenCitationsDiscoverer,
)
from citations_collector.discovery.utils import deduplicate_citations
from citations_collector.models import CitationRecord, Collection
from citations_collector.persistence import tsv_io, yaml_io

logger = logging.getLogger(__name__)


class CitationCollector:
    """
    Main orchestration class for citation collection.

    Provides library-first API for loading collections, discovering citations,
    and saving results.
    """

    def __init__(self, collection: Collection) -> None:
        """
        Initialize with a Collection object.

        Args:
            collection: Collection object to manage
        """
        self.collection = collection
        self.citations: list[CitationRecord] = []

    @classmethod
    def from_yaml(cls, path: Path) -> CitationCollector:
        """
        Load collection from YAML file.

        Args:
            path: Path to collection YAML file

        Returns:
            CitationCollector instance
        """
        collection = yaml_io.load_collection(path)
        return cls(collection)

    def discover_all(
        self,
        sources: list[str] | None = None,
        incremental: bool = True,
        email: str | None = None,
    ) -> None:
        """
        Discover citations for all items in collection.

        Args:
            sources: Which discoverers to use (default: ["crossref", "opencitations"])
                     Available: "crossref", "opencitations", "datacite"
            incremental: Use last_updated for date filtering
            email: Email for CrossRef polite pool
        """
        if sources is None:
            sources = ["crossref", "opencitations"]

        # Initialize discoverers
        discoverers: list[
            tuple[str, CrossRefDiscoverer | OpenCitationsDiscoverer | DataCiteDiscoverer]
        ] = []
        if "crossref" in sources:
            discoverers.append(("crossref", CrossRefDiscoverer(email=email)))
        if "opencitations" in sources:
            discoverers.append(("opencitations", OpenCitationsDiscoverer()))
        if "datacite" in sources:
            discoverers.append(("datacite", DataCiteDiscoverer()))

        # Determine since date for incremental
        since = None
        if incremental and self.collection.last_updated:
            since = self.collection.last_updated

        # Discover citations for all items/flavors/refs
        all_citations = []

        if not self.collection.items:
            return

        for item in self.collection.items:
            for flavor in item.flavors:
                for ref in flavor.refs:
                    logger.info(f"Discovering citations for {item.item_id}/{flavor.flavor_id}")

                    for source_name, discoverer in discoverers:
                        try:
                            citations = discoverer.discover(ref, since=since)

                            # Fill in item context
                            for citation in citations:
                                citation.item_id = item.item_id
                                citation.item_flavor = flavor.flavor_id
                                citation.item_ref_type = ref.ref_type
                                citation.item_ref_value = ref.ref_value
                                citation.item_name = item.name

                            all_citations.extend(citations)
                            logger.info(
                                f"Found {len(citations)} citations from {source_name} "
                                f"for {item.item_id}/{flavor.flavor_id}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Error discovering from {source_name} "
                                f"for {item.item_id}/{flavor.flavor_id}: {e}"
                            )

        # Deduplicate and merge with existing
        unique_citations = deduplicate_citations(all_citations)
        self.merge_citations(unique_citations)

        # Update last_updated timestamp
        self.collection.last_updated = datetime.now()

    def load_existing_citations(self, path: Path) -> None:
        """
        Load existing citations from TSV (preserves curation).

        Args:
            path: Path to TSV file
        """
        self.citations = tsv_io.load_citations(path)

    def merge_citations(self, new_citations: list[CitationRecord]) -> None:
        """
        Merge new citations with existing, preserve curation status.

        Uses unique key (item_id, item_flavor, citation_doi).

        Args:
            new_citations: New citations to merge
        """
        # Build index of existing citations
        existing_index = {(c.item_id, c.item_flavor, c.citation_doi): c for c in self.citations}

        # Merge new citations
        for new_citation in new_citations:
            key = (new_citation.item_id, new_citation.item_flavor, new_citation.citation_doi)

            if key in existing_index:
                # Citation exists - preserve curation fields
                existing = existing_index[key]
                # Keep existing curation status, comment, etc.
                # Only update metadata if not curated
                if existing.citation_status == "active" and not existing.citation_comment:
                    # Update title, authors, etc. from new discovery
                    if new_citation.citation_title:
                        existing.citation_title = new_citation.citation_title
                    if new_citation.citation_authors:
                        existing.citation_authors = new_citation.citation_authors
                    if new_citation.citation_year:
                        existing.citation_year = new_citation.citation_year
                    if new_citation.citation_journal:
                        existing.citation_journal = new_citation.citation_journal
            else:
                # New citation - add it
                self.citations.append(new_citation)
                existing_index[key] = new_citation

    def save(self, yaml_path: Path, tsv_path: Path) -> None:
        """
        Save collection and citations.

        Args:
            yaml_path: Path to output collection YAML
            tsv_path: Path to output citations TSV
        """
        yaml_io.save_collection(self.collection, yaml_path)
        tsv_io.save_citations(self.citations, tsv_path)
