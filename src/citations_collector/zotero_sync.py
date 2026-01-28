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
    collection::

        top_collection/
            {item_id}/
                {flavor}/
                    <active citation items>
                    Merged/
                        <preprints and old versions>

    Active citations are dual-assigned to both the item-level and
    flavor-level collections so they appear when browsing either level.
    Merged citations are only placed in the ``Merged`` subcollection.

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
            bare_id = self._strip_prefix(item_id)
            item_collection_name = bare_id

            # Find or create item-level collection
            item_coll_key = self._find_collection(existing_collections, item_collection_name)
            if not item_coll_key:
                if dry_run:
                    logger.info("Would create collection: %s", item_collection_name)
                    report.collections_created += 1
                    for flavor_id, buckets in flavors.items():
                        logger.info("  Would create sub-collection: %s", flavor_id)
                        report.collections_created += 1
                        for bucket_citations in buckets.values():
                            for c in bucket_citations:
                                logger.info(
                                    "    Would create item: %s",
                                    c.citation_doi or c.citation_title,
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

            for flavor_id, buckets in flavors.items():
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
                        for bucket_citations in buckets.values():
                            for c in bucket_citations:
                                logger.info(
                                    "    Would create item: %s",
                                    c.citation_doi or c.citation_title,
                                )
                                report.items_created += 1
                        continue
                    flavor_coll_key = self._create_collection(flavor_id, item_coll_key)
                    report.collections_created += 1
                    item_subcollections[flavor_coll_key] = flavor_id

                # Resolve Merged subcollection only if needed
                merged_coll_key: str | None = None

                # Sync active citations — dual-assign to item + flavor collections
                for citation in buckets.get("active", []):
                    self._sync_single_citation(
                        citation,
                        [item_coll_key, flavor_coll_key],
                        existing_items,
                        dry_run,
                        report,
                        is_merged=False,
                    )

                # Sync merged citations — only in Merged subcollection
                merged_list = buckets.get("merged", [])
                if merged_list:
                    flavor_subcollections = self._fetch_subcollections(flavor_coll_key)
                    merged_coll_key = self._find_collection(flavor_subcollections, "Merged")
                    if not merged_coll_key:
                        if dry_run:
                            logger.info("    Would create sub-collection: Merged")
                            report.collections_created += 1
                        else:
                            merged_coll_key = self._create_collection("Merged", flavor_coll_key)
                            report.collections_created += 1

                    for citation in merged_list:
                        target = [merged_coll_key] if merged_coll_key else []
                        self._sync_single_citation(
                            citation, target, existing_items, dry_run, report, is_merged=True
                        )

        return report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sync_single_citation(
        self,
        citation: CitationRecord,
        collection_keys: list[str],
        existing_items: dict[str, dict],
        dry_run: bool,
        report: SyncReport,
        is_merged: bool = False,
    ) -> None:
        """Create or update a single citation item.

        Args:
            citation: Citation record to sync
            collection_keys: Target collection keys for this citation
            existing_items: Dict of existing items by tracker key
            dry_run: If True, log actions without making API calls
            report: Sync report to update
            is_merged: If True, this citation is marked as merged
        """
        tracker_key = self._make_tracker_key(citation)

        # Check if item already exists
        if tracker_key in existing_items:
            existing_item = existing_items[tracker_key]
            current_collections = existing_item["data"].get("collections", [])

            # If citation is merged, handle moving and related items
            if is_merged:
                needs_move = set(current_collections) != set(collection_keys)
                needs_relation = False
                published_key = None

                # Try to find published version for related items link
                if citation.citation_merged_into:
                    published_tracker = self._make_tracker_key_for_doi(
                        citation.item_id, citation.item_flavor, citation.citation_merged_into
                    )
                    if published_tracker in existing_items:
                        merged_key = existing_item["data"]["key"]
                        published_key = existing_items[published_tracker]["data"]["key"]

                        # Check if relation already exists
                        relations = existing_item["data"].get("relations", {})
                        dc_relation = relations.get("dc:relation", [])
                        if isinstance(dc_relation, str):
                            dc_relation = [dc_relation]

                        published_uri = (
                            f"http://zotero.org/groups/{self.group_id}/items/{published_key}"
                        )
                        needs_relation = published_uri not in dc_relation

                # Update if move or relation needed
                if needs_move or needs_relation:
                    if dry_run:
                        if needs_move:
                            logger.info(
                                "    Would move existing item to Merged: %s",
                                citation.citation_title,
                            )
                        if needs_relation:
                            logger.info(
                                "    Would add related item link: %s",
                                citation.citation_title,
                            )
                        report.items_updated += 1
                    else:
                        try:
                            if needs_move:
                                self._move_item_to_collections(existing_item, collection_keys)
                                logger.info("Moved item to Merged: %s", citation.citation_title)

                            if needs_relation and published_key:
                                # Build items-by-key dict for the relation method
                                merged_key = existing_item["data"]["key"]
                                items_by_key = {
                                    merged_key: existing_item,
                                    published_key: existing_items[published_tracker],
                                }
                                self._add_related_item(merged_key, published_key, items_by_key)

                            report.items_updated += 1
                        except Exception as e:
                            logger.error("Error updating item %s: %s", citation.citation_doi, e)
                            report.errors.append(f"{citation.citation_doi}: {e}")
                else:
                    report.items_skipped += 1
            else:
                report.items_skipped += 1
            return

        # Create new item
        if dry_run:
            logger.info("    Would create: %s (%s)", citation.citation_title, citation.citation_doi)
            report.items_created += 1
            return

        try:
            zot_item = self._citation_to_zotero_item(citation, collection_keys)
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
        """Fetch all items under the top collection tree, indexed by tracker key.

        Walks subcollections recursively since ``collection_items`` only
        returns items directly in the given collection.
        """
        items: dict[str, dict] = {}
        try:
            collection_keys = self._collect_all_subcollection_keys(self.top_collection_key)
            collection_keys.append(self.top_collection_key)
            for coll_key in collection_keys:
                coll_items = self.zot.everything(self.zot.collection_items(coll_key))
                for item in coll_items:
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

    def _collect_all_subcollection_keys(self, parent_key: str) -> list[str]:
        """Recursively collect all subcollection keys under a parent."""
        keys: list[str] = []
        subs = self._fetch_subcollections(parent_key)
        for key in subs:
            keys.append(key)
            keys.extend(self._collect_all_subcollection_keys(key))
        return keys

    def _group_citations(
        self, citations: list[CitationRecord]
    ) -> dict[str, dict[str, dict[str, list[CitationRecord]]]]:
        """Group citations by ``item_id -> flavor -> status_bucket -> [citations]``.

        ``status_bucket`` is either ``"active"`` or ``"merged"``.
        Other statuses (e.g. ``ignored``) are skipped entirely.
        """
        grouped: dict[str, dict[str, dict[str, list[CitationRecord]]]] = {}
        for c in citations:
            status = str(c.citation_status) if c.citation_status else "active"
            if status not in ("active", "merged"):
                continue
            bucket = "merged" if status == "merged" else "active"
            (
                grouped.setdefault(c.item_id, {})
                .setdefault(c.item_flavor, {})
                .setdefault(bucket, [])
                .append(c)
            )
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
            return str(resp["successful"]["0"]["key"])
        raise RuntimeError(f"Failed to create collection '{name}': {resp}")

    def _citation_to_zotero_item(
        self, citation: CitationRecord, collection_keys: list[str]
    ) -> dict:
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

        # Build base item
        item = {
            "itemType": item_type,
            "title": citation.citation_title or "",
            "creators": creators,
            "DOI": citation.citation_doi or "",
            "url": citation.citation_url or "",
            "date": str(citation.citation_year) if citation.citation_year else "",
            "extra": "\n".join(extra_lines),
            "collections": collection_keys,
        }

        # Add journal/repository field based on item type
        if citation.citation_journal:
            if item_type == "preprint":
                # Preprints use 'repository' field (e.g., bioRxiv, arXiv)
                item["repository"] = citation.citation_journal
            else:
                # Journal articles and most other types use 'publicationTitle'
                item["publicationTitle"] = citation.citation_journal

        return item

    @staticmethod
    def _make_tracker_key(citation: CitationRecord) -> str:
        """Create tracker key for the ``extra`` field."""
        return (
            f"{citation.item_id}/{citation.item_flavor}"
            f"/{citation.citation_doi or citation.citation_url or ''}"
        )

    @staticmethod
    def _make_tracker_key_for_doi(item_id: str, flavor: str, doi: str) -> str:
        """Create tracker key for a specific DOI."""
        return f"{item_id}/{flavor}/{doi}"

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

    def _move_item_to_collections(
        self, existing_item: dict, new_collection_keys: list[str]
    ) -> None:
        """Move an existing Zotero item to different collections.

        Args:
            existing_item: The existing item dict from Zotero API
            new_collection_keys: List of collection keys to move the item to
        """
        item_key = existing_item["data"]["key"]
        version = existing_item["data"]["version"]

        # Update the item's collections
        updated_data = {
            "key": item_key,
            "version": version,
            "collections": new_collection_keys,
        }

        try:
            self.zot.update_item(updated_data)
            logger.info(
                "Updated collections for item %s: %s",
                existing_item["data"].get("title", ""),
                new_collection_keys,
            )
        except Exception as e:
            logger.error("Failed to update item collections: %s", e)
            raise

    def _add_related_item(
        self, item1_key: str, item2_key: str, existing_items_by_key: dict[str, dict]
    ) -> None:
        """Add bidirectional 'Related Items' link between two Zotero items.

        Args:
            item1_key: Zotero key of first item (e.g., merged preprint)
            item2_key: Zotero key of second item (e.g., published version)
            existing_items_by_key: Dict of existing items indexed by Zotero key
        """
        try:
            # Get current state of both items
            item1 = existing_items_by_key.get(item1_key)
            item2 = existing_items_by_key.get(item2_key)

            if not item1 or not item2:
                logger.warning(
                    f"Cannot add relation: item keys not found ({item1_key}, {item2_key})"
                )
                return

            # Get current relations
            relations1 = item1["data"].get("relations", {})
            relations2 = item2["data"].get("relations", {})

            # Ensure relations are dicts with proper structure
            if not isinstance(relations1, dict):
                relations1 = {}
            if not isinstance(relations2, dict):
                relations2 = {}

            # Build full item URIs
            item1_uri = f"http://zotero.org/groups/{self.group_id}/items/{item1_key}"
            item2_uri = f"http://zotero.org/groups/{self.group_id}/items/{item2_key}"

            # Add item2 to item1's related items (if not already there)
            dc_relation1 = relations1.get("dc:relation", [])
            if isinstance(dc_relation1, str):
                dc_relation1 = [dc_relation1]
            elif not isinstance(dc_relation1, list):
                dc_relation1 = []

            if item2_uri not in dc_relation1:
                dc_relation1.append(item2_uri)
                relations1["dc:relation"] = dc_relation1

                # Update item1
                update1 = {
                    "key": item1_key,
                    "version": item1["data"]["version"],
                    "relations": relations1,
                }
                self.zot.update_item(update1)
                logger.info(f"Added related item link: {item1_key} -> {item2_key}")

            # Add item1 to item2's related items (if not already there)
            dc_relation2 = relations2.get("dc:relation", [])
            if isinstance(dc_relation2, str):
                dc_relation2 = [dc_relation2]
            elif not isinstance(dc_relation2, list):
                dc_relation2 = []

            if item1_uri not in dc_relation2:
                dc_relation2.append(item1_uri)
                relations2["dc:relation"] = dc_relation2

                # Refresh item2 to get latest version (item1 update may have changed it)
                item2_refreshed = self.zot.item(item2_key)
                relations2_refreshed = item2_refreshed["data"].get("relations", {})
                if not isinstance(relations2_refreshed, dict):
                    relations2_refreshed = {}

                dc_relation2_refreshed = relations2_refreshed.get("dc:relation", [])
                if isinstance(dc_relation2_refreshed, str):
                    dc_relation2_refreshed = [dc_relation2_refreshed]
                elif not isinstance(dc_relation2_refreshed, list):
                    dc_relation2_refreshed = []

                if item1_uri not in dc_relation2_refreshed:
                    dc_relation2_refreshed.append(item1_uri)
                    relations2_refreshed["dc:relation"] = dc_relation2_refreshed

                    update2 = {
                        "key": item2_key,
                        "version": item2_refreshed["data"]["version"],
                        "relations": relations2_refreshed,
                    }
                    self.zot.update_item(update2)
                    logger.info(f"Added related item link: {item2_key} -> {item1_key}")

        except Exception as e:
            logger.warning(f"Failed to add related items: {e}")
