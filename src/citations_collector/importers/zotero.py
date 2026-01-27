"""Import items from Zotero groups/collections."""

from __future__ import annotations

import logging
import os
import re
from datetime import date
from typing import Any, cast

from pyzotero import zotero

from citations_collector.models import Collection, Item, ItemFlavor, ItemRef, RefType

logger = logging.getLogger(__name__)


class ZoteroImporter:
    """
    Import items from Zotero group or collection.

    Extracts DOIs and other identifiers from Zotero item metadata
    to create a Collection for citation tracking.

    Example:
        importer = ZoteroImporter(api_key="your-api-key")
        collection = importer.import_group(group_id=5774211)
    """

    DOI_PATTERN = re.compile(r"^10\.\d{4,}/[^\s]+$")

    def __init__(self, api_key: str | None = None) -> None:
        """
        Initialize Zotero importer.

        Args:
            api_key: Zotero API key. If not provided, reads from
                    ZOTERO_API_KEY environment variable.
                    Public groups can be read without an API key.
        """
        self.api_key = api_key or os.getenv("ZOTERO_API_KEY")

    def import_group(
        self,
        group_id: int,
        collection_key: str | None = None,
        limit: int | None = None,
    ) -> Collection:
        """
        Import items from a Zotero group.

        Args:
            group_id: Zotero group ID
            collection_key: Optional collection key within the group.
                           If None, imports all items in the group.
            limit: Optional limit on number of items to import.

        Returns:
            Collection with items extracted from Zotero.
            Each item gets:
            - item_id: "zotero:{item_key}" or DOI-based ID if available
            - flavor_id: "main" (single flavor per item)
            - ref: DOI extracted from Zotero metadata
        """
        # Initialize pyzotero client
        zot = zotero.Zotero(group_id, "group", self.api_key)

        # Fetch items
        if collection_key:
            raw_items = self._fetch_collection_items(zot, collection_key, limit)
            collection_name = self._get_collection_name(zot, collection_key)
        else:
            raw_items = self._fetch_all_items(zot, limit)
            collection_name = self._get_group_name(zot, group_id)

        # Convert to Collection items
        items: list[Item] = []
        for raw_item in raw_items:
            item = self._zotero_item_to_item(raw_item)
            if item:
                items.append(item)

        logger.info(f"Imported {len(items)} items from Zotero group {group_id}")

        return Collection(
            name=collection_name or f"Zotero Group {group_id}",
            description=f"Items imported from Zotero group {group_id}",
            homepage=f"https://www.zotero.org/groups/{group_id}",
            source_type="zotero",
            zotero_group_id=group_id,
            zotero_collection_key=collection_key,
            items=items,
        )

    def _fetch_all_items(
        self, zot: zotero.Zotero, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Fetch all items from a Zotero library."""
        try:
            if limit:
                return cast(list[dict[str, Any]], zot.items(limit=limit))
            else:
                return cast(list[dict[str, Any]], zot.everything(zot.items()))
        except Exception as e:
            logger.error(f"Failed to fetch Zotero items: {e}")
            return []

    def _fetch_collection_items(
        self, zot: zotero.Zotero, collection_key: str, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Fetch items from a specific collection."""
        try:
            if limit:
                return cast(list[dict[str, Any]], zot.collection_items(collection_key, limit=limit))
            else:
                return cast(
                    list[dict[str, Any]], zot.everything(zot.collection_items(collection_key))
                )
        except Exception as e:
            logger.error(f"Failed to fetch collection {collection_key}: {e}")
            return []

    def _get_collection_name(self, zot: zotero.Zotero, collection_key: str) -> str | None:
        """Get the name of a collection."""
        try:
            collection = zot.collection(collection_key)
            name: str | None = collection.get("data", {}).get("name")
            return name
        except Exception:
            return None

    def _get_group_name(self, zot: zotero.Zotero, group_id: int) -> str | None:
        """Get the name of a group."""
        # pyzotero doesn't have a direct group info method for group libraries
        # Return None to use fallback
        return None

    def _zotero_item_to_item(self, raw_item: dict) -> Item | None:
        """
        Convert a Zotero item to a Collection Item.

        Args:
            raw_item: Raw item data from pyzotero

        Returns:
            Item with DOI ref if available, None if no usable identifier
        """
        data = raw_item.get("data", {})
        item_key = raw_item.get("key", "")

        # Skip attachments and notes
        item_type = data.get("itemType", "")
        if item_type in ("attachment", "note"):
            return None

        # Extract DOI
        doi = self._extract_doi(data)

        # Extract other identifiers
        pmid = data.get("extra", "")
        pmid_match = re.search(r"PMID:\s*(\d+)", pmid)
        pmid_value = pmid_match.group(1) if pmid_match else None

        # Build refs list
        refs: list[ItemRef] = []
        if doi:
            refs.append(ItemRef(ref_type=RefType.doi, ref_value=doi))
        if pmid_value:
            refs.append(ItemRef(ref_type=RefType.pmid, ref_value=pmid_value))

        # If no usable refs, use URL if available
        if not refs:
            url = data.get("url")
            if url:
                refs.append(ItemRef(ref_type=RefType.url, ref_value=url))
            else:
                # No usable identifier
                logger.debug(f"Skipping Zotero item {item_key}: no DOI, PMID, or URL")
                return None

        # Determine item_id (prefer DOI-based ID)
        item_id = f"doi:{doi}" if doi else f"zotero:{item_key}"

        # Extract metadata
        title = data.get("title", f"Untitled ({item_key})")
        url = data.get("url")

        # Parse date
        date_str = data.get("date", "")
        release_date = self._parse_date(date_str)

        # Create single flavor for the item
        flavor = ItemFlavor(
            flavor_id="main",
            name=title,
            release_date=release_date,
            refs=refs,
        )

        return Item(
            item_id=item_id,
            name=title,
            homepage=url,
            flavors=[flavor],
        )

    def _extract_doi(self, data: dict[str, Any]) -> str | None:
        """
        Extract DOI from Zotero item data.

        Checks multiple fields where DOI might be stored.
        """
        # Check dedicated DOI field
        doi: str = data.get("DOI", "")
        if doi and self.DOI_PATTERN.match(doi):
            return doi

        # Check URL field for DOI URLs
        url = data.get("url", "")
        if "doi.org/" in url:
            # Extract DOI from URL
            match = re.search(r"doi\.org/(10\.\d{4,}/[^\s]+)", url)
            if match:
                return match.group(1)

        # Check extra field for DOI
        extra = data.get("extra", "")
        match = re.search(r"DOI:\s*(10\.\d{4,}/[^\s]+)", extra, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    def _parse_date(self, date_str: str) -> date | None:
        """Parse various date formats from Zotero."""
        if not date_str:
            return None

        # Try ISO format first
        try:
            return date.fromisoformat(date_str[:10])
        except ValueError:
            pass

        # Try year-only
        match = re.match(r"^(\d{4})$", date_str)
        if match:
            return date(int(match.group(1)), 1, 1)

        # Try "Month Day, Year" format
        try:
            from datetime import datetime

            for fmt in ["%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%Y/%m/%d"]:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
        except Exception:
            pass

        return None
