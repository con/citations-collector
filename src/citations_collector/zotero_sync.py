"""Sync citations to Zotero as hierarchical collections."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from pyzotero import zotero

from citations_collector.models import CitationRecord, Collection

logger = logging.getLogger(__name__)

TRACKER_PREFIX = "CitationTracker:"


@dataclass
class SyncReport:
    """Summary of a Zotero sync operation."""

    collections_created: int = 0
    items_created: int = 0
    items_updated: int = 0
    items_skipped: int = 0
    attachments_created: int = 0
    errors: list[str] = field(default_factory=list)


class ZoteroSyncer:
    """Sync citation records to Zotero as hierarchical collections.

    Creates a two-level collection hierarchy under the configured top-level
    collection:

        top_collection/
            {item_id} - {item_name}/
                {flavor}/
                    <citation items>

    Each citation item includes a tracker key in the ``extra`` field
    (``CitationTracker: {item_id}/{flavor}/{doi_or_url}``) so that
    subsequent syncs can detect items that already exist.
    """

    def __init__(self, api_key: str, group_id: int, collection_key: str) -> None:
        self.zot = zotero.Zotero(group_id, "group", api_key)
        self.group_id = group_id
        self.top_collection_key = collection_key

    def sync(
        self,
        collection: Collection,
        citations: list[CitationRecord],
        dry_run: bool = False,
    ) -> SyncReport:
        """Sync citations to Zotero hierarchy.

        Args:
            collection: The source collection definition.
            citations: Citation records to sync.
            dry_run: If ``True``, log what would happen but make no API calls.

        Returns:
            A :class:`SyncReport` summarising the operations performed.
        """
        report = SyncReport()

        # 1. Fetch existing collections under top_collection_key
        existing_collections = self._fetch_subcollections(self.top_collection_key)

        # 2. Fetch existing items and index by tracker key
        existing_items = self._fetch_existing_items()

        # 3. Group citations by item_id, then flavor
        grouped = self._group_citations(citations)

        # 4. For each item, ensure collection hierarchy exists
        for item_id, flavors in grouped.items():
            item_name = self._get_item_name(citations, item_id)
            bare_id = self._strip_prefix(item_id)
            item_collection_name = f"{bare_id} - {item_name}" if item_name else bare_id

            # Find or create item-level collection
            item_coll_key = self._find_collection(existing_collections, item_collection_name)
            if not item_coll_key:
                if dry_run:
                    logger.info("Would create collection: %s", item_collection_name)
                    report.collections_created += 1
                    # Cannot continue without a real key in dry-run; log everything
                    for flavor_id, flavor_citations in flavors.items():
                        logger.info("  Would create sub-collection: %s", flavor_id)
                        report.collections_created += 1
                        for c in flavor_citations:
                            logger.info(
                                "    Would create item: %s", c.citation_doi or c.citation_title
                            )
                            report.items_created += 1
                    continue
                item_coll_key = self._create_collection(
                    item_collection_name, self.top_collection_key
                )
                report.collections_created += 1
                existing_collections[item_coll_key] = item_collection_name

            # Fetch sub-collections for this item
            item_subcollections = self._fetch_subcollections(item_coll_key)

            for flavor_id, flavor_citations in flavors.items():
                # Find or create flavor-level collection
                flavor_coll_key = self._find_collection(item_subcollections, flavor_id)
                if not flavor_coll_key:
                    if dry_run:
                        logger.info(
                            "  Would create sub-collection: %s under %s",
                            flavor_id,
                            item_collection_name,
                        )
                        report.collections_created += 1
                        for c in flavor_citations:
                            logger.info(
                                "    Would create item: %s",
                                c.citation_doi or c.citation_title,
                            )
                            report.items_created += 1
                        continue
                    flavor_coll_key = self._create_collection(flavor_id, item_coll_key)
                    report.collections_created += 1
                    item_subcollections[flavor_coll_key] = flavor_id

                # Sync citation items into this flavor collection
                for citation in flavor_citations:
                    self._sync_single_citation(
                        citation, flavor_coll_key, existing_items, dry_run, report
                    )

        return report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sync_single_citation(
        self,
        citation: CitationRecord,
        collection_key: str,
        existing_items: dict[str, dict],
        dry_run: bool,
        report: SyncReport,
    ) -> None:
        """Create or skip a single citation item."""
        tracker_key = self._make_tracker_key(citation)

        if tracker_key in existing_items:
            report.items_skipped += 1
            return

        if dry_run:
            logger.info("    Would create: %s (%s)", citation.citation_title, citation.citation_doi)
            report.items_created += 1
            return

        try:
            zot_item = self._citation_to_zotero_item(citation, collection_key)
            resp = self.zot.create_items([zot_item])

            if resp.get("successful"):
                report.items_created += 1
                # Attach PDF link if available
                if citation.pdf_url:
                    created_key = resp["successful"]["0"]["key"]
                    self._attach_linked_url(created_key, citation.pdf_url, citation.citation_title)
                    report.attachments_created += 1
            elif resp.get("failed"):
                err = str(resp["failed"])
                logger.error("Failed to create item %s: %s", citation.citation_doi, err)
                report.errors.append(f"{citation.citation_doi}: {err}")
        except Exception as e:
            logger.error("Error creating item %s: %s", citation.citation_doi, e)
            report.errors.append(f"{citation.citation_doi}: {e}")

    def _fetch_subcollections(self, parent_key: str) -> dict[str, str]:
        """Fetch subcollections under *parent_key*.  Returns ``{key: name}``."""
        try:
            collections = self.zot.collections_sub(parent_key)
            return {c["key"]: c["data"]["name"] for c in collections}
        except Exception:
            return {}

    def _fetch_existing_items(self) -> dict[str, dict]:
        """Fetch all items under the top collection, indexed by tracker key."""
        items: dict[str, dict] = {}
        try:
            all_items = self.zot.everything(self.zot.collection_items(self.top_collection_key))
            for item in all_items:
                if item["data"].get("itemType") in ("attachment", "note"):
                    continue
                extra = item["data"].get("extra", "")
                for line in extra.split("\n"):
                    if line.startswith(TRACKER_PREFIX):
                        tracker_key = line[len(TRACKER_PREFIX) :].strip()
                        items[tracker_key] = item
                        break
        except Exception as e:
            logger.warning("Error fetching existing items: %s", e)
        return items

    def _group_citations(
        self, citations: list[CitationRecord]
    ) -> dict[str, dict[str, list[CitationRecord]]]:
        """Group citations by ``item_id -> flavor -> [citations]``."""
        grouped: dict[str, dict[str, list[CitationRecord]]] = {}
        for c in citations:
            if c.citation_status != "active":
                continue
            grouped.setdefault(c.item_id, {}).setdefault(c.item_flavor, []).append(c)
        return grouped

    def _get_item_name(self, citations: list[CitationRecord], item_id: str) -> str | None:
        """Return the item name from the first citation matching *item_id*."""
        for c in citations:
            if c.item_id == item_id and c.item_name:
                return c.item_name
        return None

    @staticmethod
    def _strip_prefix(item_id: str) -> str:
        """Strip namespace prefix: ``'dandi:000020'`` -> ``'000020'``."""
        return item_id.split(":", 1)[-1]

    @staticmethod
    def _find_collection(collections: dict[str, str], name: str) -> str | None:
        """Find collection key by name."""
        for key, coll_name in collections.items():
            if coll_name == name:
                return key
        return None

    def _create_collection(self, name: str, parent_key: str) -> str:
        """Create a new collection under *parent_key*.  Returns the new key."""
        payload = {"name": name, "parentCollection": parent_key}
        resp = self.zot.create_collections([payload])
        if resp.get("successful"):
            return resp["successful"]["0"]["key"]
        raise RuntimeError(f"Failed to create collection '{name}': {resp}")

    def _citation_to_zotero_item(self, citation: CitationRecord, collection_key: str) -> dict:
        """Convert a :class:`CitationRecord` to a Zotero item dict."""
        # Determine item type
        item_type = "journalArticle"
        if citation.citation_type:
            type_map = {
                "Preprint": "preprint",
                "Thesis": "thesis",
                "Book": "book",
                "Software": "computerProgram",
                "Dataset": "dataset",
            }
            item_type = type_map.get(str(citation.citation_type), "journalArticle")

        # Build creators list
        creators = []
        if citation.citation_authors:
            for author in citation.citation_authors.split("; "):
                parts = author.rsplit(" ", 1)
                if len(parts) == 2:
                    creators.append(
                        {"creatorType": "author", "firstName": parts[0], "lastName": parts[1]}
                    )
                else:
                    creators.append({"creatorType": "author", "name": author})

        tracker_key = self._make_tracker_key(citation)
        extra_lines = [f"{TRACKER_PREFIX} {tracker_key}"]
        if citation.citation_source:
            extra_lines.append(f"Discovery Source: {citation.citation_source}")

        return {
            "itemType": item_type,
            "title": citation.citation_title or "",
            "creators": creators,
            "DOI": citation.citation_doi or "",
            "url": citation.citation_url or "",
            "date": str(citation.citation_year) if citation.citation_year else "",
            "publicationTitle": citation.citation_journal or "",
            "extra": "\n".join(extra_lines),
            "collections": [collection_key],
        }

    @staticmethod
    def _make_tracker_key(citation: CitationRecord) -> str:
        """Create tracker key for the ``extra`` field."""
        return (
            f"{citation.item_id}/{citation.item_flavor}"
            f"/{citation.citation_doi or citation.citation_url or ''}"
        )

    def _attach_linked_url(self, parent_key: str, url: str, title: str | None = None) -> None:
        """Attach a linked URL to a Zotero item."""
        try:
            attachment = {
                "itemType": "attachment",
                "linkMode": "linked_url",
                "url": url,
                "title": title or "PDF",
                "parentItem": parent_key,
                "tags": [],
                "relations": {},
                "contentType": "application/pdf",
            }
            self.zot.create_items([attachment])
        except Exception as e:
            logger.warning("Failed to attach URL to %s: %s", parent_key, e)
