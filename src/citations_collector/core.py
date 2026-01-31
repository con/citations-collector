"""Core orchestration for citation collection."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from citations_collector.discovery import (
    CrossRefDiscoverer,
    DataCiteDiscoverer,
    OpenAlexDiscoverer,
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

    def __init__(self, collection: Collection, collection_path: Path | None = None) -> None:
        """
        Initialize with a Collection object.

        Args:
            collection: Collection object to manage
            collection_path: Path to collection YAML file (for resolving relative paths)
        """
        self.collection = collection
        self.collection_path = collection_path
        self.citations: list[CitationRecord] = []
        self._skip_yaml_save = False  # Flag to skip YAML save when items from external source

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
        return cls(collection, collection_path=path)

    def populate_from_source(
        self, progress_callback: Callable[[int, int | None], None] | None = None
    ) -> None:
        """
        Dynamically populate items from source configuration.

        If collection.source is configured (e.g., type="dandi" with dandiset_ids),
        fetches the items from the source API and adds them to collection.items.

        This allows collections to stay up-to-date without manually maintaining
        item lists - the items are fetched dynamically at discovery time.

        Args:
            progress_callback: Optional callback(current, total) for progress reporting
        """
        if not self.collection.source or not self.collection.source.type:
            return

        source_type = self.collection.source.type
        logger.info(f"Populating items from source: {source_type}")

        if source_type == "dandi":
            self._populate_from_dandi(progress_callback)
        elif source_type == "bibtex":
            self._populate_from_bibtex(progress_callback)
        else:
            logger.warning(f"Unknown source type: {source_type}")

    def _populate_from_dandi(
        self, progress_callback: Callable[[int, int | None], None] | None = None
    ) -> None:
        """Populate items from DANDI Archive using source.dandiset_ids."""
        from citations_collector.importers import DANDIImporter

        if not self.collection.source or not self.collection.source.dandiset_ids:
            logger.warning("No dandiset_ids specified in source config")
            return

        dandiset_ids = self.collection.source.dandiset_ids
        importer = DANDIImporter()

        # Import specific dandisets
        imported = importer.import_specific(
            dandiset_ids=dandiset_ids,
            progress_callback=progress_callback,
        )

        # Add imported items to collection (avoiding duplicates)
        if not imported.items:
            logger.warning("No items imported from DANDI")
            return

        if not self.collection.items:
            self.collection.items = []

        existing_ids = {item.item_id for item in self.collection.items}
        for item in imported.items:
            if item.item_id not in existing_ids:
                self.collection.items.append(item)
                logger.info(f"Added item from DANDI: {item.item_id}")
            else:
                logger.debug(f"Skipping duplicate item: {item.item_id}")

    def _populate_from_bibtex(
        self, progress_callback: Callable[[int, int | None], None] | None = None
    ) -> None:
        """
        Populate items from BibTeX source.

        Reads BibTeX file specified in source config, parses entries using
        regex pattern to extract item_id and flavor_id.
        """
        from citations_collector.importers import BibTeXImporter

        source = self.collection.source
        if not source:
            return

        # Resolve path relative to collection file location
        bibtex_file = Path(source.bibtex_file) if source.bibtex_file else None
        if not bibtex_file:
            logger.error("BibTeX source requires bibtex_file to be specified")
            return

        if not bibtex_file.is_absolute() and self.collection_path:
            # Resolve relative to collection YAML directory
            bibtex_file = (self.collection_path.parent / bibtex_file).resolve()

        if not bibtex_file.exists():
            logger.error(f"BibTeX file not found: {bibtex_file}")
            return

        # Validate required fields
        if not source.bib_field:
            logger.error("BibTeX source requires bib_field to be specified")
            return
        if not source.ref_type:
            logger.error("BibTeX source requires ref_type to be specified")
            return
        if not source.ref_regex:
            logger.error("BibTeX source requires ref_regex to be specified")
            return

        if progress_callback:
            progress_callback(0, None)

        logger.info(f"Reading BibTeX from {bibtex_file.name}")

        # Import from BibTeX
        importer = BibTeXImporter(
            bibtex_file=bibtex_file,
            bib_field=source.bib_field,
            ref_type=source.ref_type,
            ref_regex=source.ref_regex,
        )

        try:
            bib_collection = importer.import_all()
        except Exception as e:
            logger.error(f"Failed to import from BibTeX: {e}")
            return

        # Handle update_items setting
        bib_items = bib_collection.items or []
        if source.update_items == "sync":
            # Replace all items with BibTeX items
            self.collection.items = bib_items
            logger.info(f"Synced {len(bib_items)} items from BibTeX")
        elif source.update_items == "add":
            # Add only new items (by item_id)
            if not self.collection.items:
                self.collection.items = []
            existing_ids = {item.item_id for item in self.collection.items}
            new_items = [item for item in bib_items if item.item_id not in existing_ids]
            self.collection.items.extend(new_items)
            logger.info(f"Added {len(new_items)} new items from BibTeX")
        else:
            # update_items: false/omitted - don't modify YAML, just use BibTeX items for discovery
            # Replace items temporarily for discovery, but won't be saved to YAML
            self.collection.items = bib_items
            self._skip_yaml_save = True  # Don't save YAML - items maintained externally
            logger.info(f"Loaded {len(bib_items)} items from BibTeX (not saving to YAML)")

        if progress_callback:
            progress_callback(len(bib_items), len(bib_items))

    def expand_refs(
        self,
        github_token: str | None = None,
        zenodo_token: str | None = None,
        expand_types: list[str] | None = None,
    ) -> None:
        """
        Expand non-DOI references to DOI references.

        This pre-processes the collection to convert references like:
        - zenodo_concept → multiple DOI refs (concept + all versions)
        - github → DOI ref (via Zenodo badge extraction)

        Expanded DOIs are added to the item's refs list alongside original refs.

        Args:
            github_token: Optional GitHub token for API rate limits
            zenodo_token: Optional Zenodo token for authentication
            expand_types: Which ref types to expand (default: ["zenodo_concept", "github"])
        """
        from citations_collector.importers import GitHubMapper, ZenodoExpander

        if expand_types is None:
            expand_types = ["zenodo_concept", "github"]

        if not self.collection.items:
            return

        # Initialize expanders/mappers
        zenodo_expander = (
            ZenodoExpander(zenodo_token=zenodo_token) if "zenodo_concept" in expand_types else None
        )
        github_mapper = (
            GitHubMapper(github_token=github_token) if "github" in expand_types else None
        )

        for item in self.collection.items:
            for flavor in item.flavors:
                # Collect expanded refs
                expanded_refs = []

                for ref in flavor.refs:
                    # Expand zenodo_concept to all version DOIs
                    if ref.ref_type == "zenodo_concept" and zenodo_expander:
                        logger.info(f"Expanding Zenodo concept {ref.ref_value} for {item.item_id}")
                        doi_refs = zenodo_expander.expand(ref.ref_value)
                        expanded_refs.extend(doi_refs)

                    # Map github to Zenodo DOI
                    elif ref.ref_type == "github" and github_mapper:
                        logger.info(f"Mapping GitHub {ref.ref_value} to DOI for {item.item_id}")
                        doi_ref = github_mapper.map_to_doi(ref.ref_value)
                        if doi_ref:
                            expanded_refs.append(doi_ref)

                # Add expanded refs to flavor, avoiding duplicates
                existing_ref_values = {(ref.ref_type, ref.ref_value) for ref in flavor.refs}
                for expanded_ref in expanded_refs:
                    ref_key = (expanded_ref.ref_type, expanded_ref.ref_value)
                    if ref_key not in existing_ref_values:
                        flavor.refs.append(expanded_ref)
                        existing_ref_values.add(ref_key)

    def _get_most_recent_discovery_date(self) -> datetime | None:
        """
        Get the most recent discovery date from existing citations.

        Used for incremental discovery to avoid re-querying old citations.

        Returns:
            Most recent discovered_date, or None if no citations exist
        """
        if not self.citations:
            return None

        dates = [c.discovered_date for c in self.citations if c.discovered_date]
        if not dates:
            return None

        # Convert date to datetime for API compatibility
        most_recent = max(dates)
        return datetime.combine(most_recent, datetime.min.time())

    def _report_discoveries(self, new_citations: list[CitationRecord]) -> None:
        """
        Report discovered citations grouped by DOI, showing which sources found each.

        Only reports citations that are NEW (not already in self.citations).

        Args:
            new_citations: Newly discovered citations to report
        """
        if not new_citations:
            return

        # Build set of existing citation keys to identify truly new ones
        existing_keys = {(c.item_id, c.item_flavor, c.citation_doi) for c in self.citations}

        # Group new citations by DOI
        doi_groups: dict[str, list[CitationRecord]] = {}
        for citation in new_citations:
            key = (citation.item_id, citation.item_flavor, citation.citation_doi)
            # Only report if not already in existing citations
            if key not in existing_keys:
                doi = citation.citation_doi or "unknown"
                if doi not in doi_groups:
                    doi_groups[doi] = []
                doi_groups[doi].append(citation)

        # Report each new DOI with sources
        if doi_groups:
            logger.info(f"\nDiscovered {len(doi_groups)} new citations:")
            for doi, group in sorted(doi_groups.items()):
                # Collect all sources that found this DOI
                sources = set()
                for citation in group:
                    if hasattr(citation, "citation_sources") and citation.citation_sources:
                        sources.update(citation.citation_sources)
                    elif citation.citation_source:
                        sources.add(citation.citation_source)

                # Format sources
                sources_str = ", ".join(sorted(sources)) if sources else "unknown"

                # Show item_id/flavor and title (truncated)
                item_ref = f"{group[0].item_id}/{group[0].item_flavor}"
                title = (group[0].citation_title or "")[:60]
                title_suffix = "..." if len(group[0].citation_title or "") > 60 else ""
                logger.info(f"  {doi} [{sources_str}]")
                logger.info(f"    → {item_ref}: {title}{title_suffix}")

    def discover_all(
        self,
        sources: list[str] | None = None,
        incremental: bool = True,
        since_date: datetime | None = None,
        email: str | None = None,
    ) -> None:
        """
        Discover citations for all items in collection.

        Args:
            sources: Which discoverers to use (default: all available)
                     Available: "crossref", "opencitations", "datacite", "openalex"
            incremental: Derive since date from existing citations for incremental discovery
            since_date: Optional explicit since date (overrides incremental)
            email: Email for CrossRef polite pool
        """
        if sources is None:
            sources = ["crossref", "opencitations", "datacite", "openalex"]

        # Initialize discoverers
        discoverers: list[
            tuple[
                str,
                CrossRefDiscoverer
                | OpenCitationsDiscoverer
                | DataCiteDiscoverer
                | OpenAlexDiscoverer,
            ]
        ] = []
        if "crossref" in sources:
            discoverers.append(("crossref", CrossRefDiscoverer(email=email)))
        if "opencitations" in sources:
            discoverers.append(("opencitations", OpenCitationsDiscoverer()))
        if "datacite" in sources:
            discoverers.append(("datacite", DataCiteDiscoverer()))
        if "openalex" in sources:
            discoverers.append(("openalex", OpenAlexDiscoverer(email=email)))

        # Determine since date for incremental
        since = since_date  # Explicit override takes precedence
        if since is None and incremental:
            # Derive from existing citations (most recent discovered_date)
            since = self._get_most_recent_discovery_date()

        # Discover citations for all items/flavors/refs
        all_citations = []

        if not self.collection.items:
            return

        # Count total refs for progress bar
        total_refs = sum(
            len(flavor.refs) for item in self.collection.items for flavor in item.flavors
        )

        # Create progress bar with logging redirection
        # Disable only if DEBUG logging is enabled (so debug messages are visible)
        with (
            logging_redirect_tqdm(),
            tqdm(
                total=total_refs * len(discoverers),
                desc="Discovering citations",
                unit="query",
                disable=logger.getEffectiveLevel() <= logging.DEBUG,
            ) as pbar,
        ):
            for item in self.collection.items:
                for flavor in item.flavors:
                    for ref in flavor.refs:
                        for source_name, discoverer in discoverers:
                            try:
                                citations = discoverer.discover(ref, since=since)

                                # Fill in item context and track source
                                for citation in citations:
                                    citation.item_id = item.item_id
                                    citation.item_flavor = flavor.flavor_id
                                    citation.item_ref_type = ref.ref_type
                                    citation.item_ref_value = ref.ref_value
                                    citation.item_name = item.name
                                    # Track which source found this citation
                                    citation.citation_source = source_name  # type: ignore[assignment]

                                all_citations.extend(citations)
                                logger.debug(
                                    f"{source_name}: {len(citations)} citations "
                                    f"for {item.item_id}/{flavor.flavor_id}"
                                )

                            except Exception as e:
                                logger.error(
                                    f"Error discovering from {source_name} "
                                    f"for {item.item_id}/{flavor.flavor_id}: {e}"
                                )

                            # Update progress
                            pbar.update(1)

        # Deduplicate and merge with existing
        unique_citations = deduplicate_citations(all_citations)

        # Report new citations grouped by DOI with sources
        self._report_discoveries(unique_citations)

        self.merge_citations(unique_citations)

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
        # Only save YAML if items are managed in YAML (not external source)
        if not self._skip_yaml_save:
            yaml_io.save_collection(self.collection, yaml_path)
        else:
            logger.info("Skipping YAML save - items managed externally")
        tsv_io.save_citations(self.citations, tsv_path)
