"""Import dandisets from DANDI Archive API."""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable, Iterator
from datetime import date
from typing import Any

import requests

from citations_collector.models import Collection, Item, ItemFlavor, ItemRef, RefType

logger = logging.getLogger(__name__)


class DANDIImporter:
    """
    Import dandisets from DANDI Archive API.

    Fetches all dandisets (or a subset) from the DANDI Archive API
    and creates a Collection with version DOIs for citation tracking.

    Example:
        importer = DANDIImporter()
        collection = importer.import_all(limit=10)
    """

    BASE_URL = "https://api.dandiarchive.org/api"
    PAGE_SIZE = 100  # DANDI API default

    def __init__(self, api_url: str | None = None) -> None:
        """
        Initialize DANDI importer.

        Args:
            api_url: Optional custom API URL (for testing).
                    Defaults to DANDI Archive production API.
        """
        self.api_url = api_url or self.BASE_URL
        self.session = requests.Session()
        # Set a reasonable timeout and user agent
        self.session.headers["User-Agent"] = "citations-collector/0.1"

    def import_specific(
        self,
        dandiset_ids: list[str],
        include_draft: bool = False,
        progress_callback: Callable[[int, int | None], None] | None = None,
    ) -> Collection:
        """
        Import specific dandisets by their identifiers.

        Args:
            dandiset_ids: List of dandiset identifiers (e.g., ["000003", "000402"])
            include_draft: If True, include draft versions without DOIs.
            progress_callback: Optional callback(current, total) for progress updates.

        Returns:
            Collection with the specified dandisets and their versions.
        """
        items: list[Item] = []
        total = len(dandiset_ids)

        for idx, dandiset_id in enumerate(dandiset_ids):
            # Fetch dandiset metadata
            dandiset = self._fetch_dandiset(dandiset_id)
            if dandiset is None:
                logger.warning(f"Dandiset {dandiset_id} not found, skipping")
                continue

            item = self._dandiset_to_item(dandiset, include_draft=include_draft)
            if item is not None and item.flavors:
                items.append(item)
                logger.debug(f"Imported dandiset {item.item_id} with {len(item.flavors)} versions")

            if progress_callback:
                progress_callback(idx + 1, total)

        logger.info(f"Imported {len(items)} specific dandisets from DANDI Archive")

        return Collection(
            name="DANDI Archive",
            description="Neural data archive with versioned dandisets",
            homepage="https://dandiarchive.org",
            source_type="dandi",
            items=items,
        )

    def import_all(
        self,
        include_draft: bool = False,
        limit: int | None = None,
        progress_callback: Callable[[int, int | None], None] | None = None,
    ) -> Collection:
        """
        Import all dandisets as a Collection.

        Args:
            include_draft: If True, include draft versions without DOIs.
                          Default False (only published versions with DOIs).
            limit: Optional limit on number of dandisets to import.
            progress_callback: Optional callback(current, total) for progress updates.

        Returns:
            Collection with:
            - item_id: "dandi:NNNNNN" (e.g., "dandi:000003")
            - flavor_id: version string (e.g., "0.230629.1955")
            - ref: DOI (e.g., "10.48324/dandi.000003/0.230629.1955")
        """
        items: list[Item] = []
        count = 0

        for dandiset in self._iter_dandisets():
            if limit is not None and count >= limit:
                break

            item = self._dandiset_to_item(dandiset, include_draft=include_draft)
            if item is not None and item.flavors:  # Only include if has versions
                items.append(item)
                count += 1

                if progress_callback:
                    progress_callback(count, limit)

                logger.debug(f"Imported dandiset {item.item_id} with {len(item.flavors)} versions")

        logger.info(f"Imported {len(items)} dandisets from DANDI Archive")

        return Collection(
            name="DANDI Archive",
            description="Neural data archive with versioned dandisets",
            homepage="https://dandiarchive.org",
            source_type="dandi",
            items=items,
        )

    def _fetch_dandiset(self, dandiset_id: str) -> dict | None:
        """
        Fetch a single dandiset by ID.

        Args:
            dandiset_id: The dandiset identifier (e.g., "000003", "000402")

        Returns:
            Dandiset metadata dictionary or None if not found
        """
        url = f"{self.api_url}/dandisets/{dandiset_id}/"

        try:
            response = self.session.get(url, timeout=60)
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]
        except requests.RequestException as e:
            logger.error(f"Failed to fetch dandiset {dandiset_id}: {e}")
            return None

    def _iter_dandisets(self) -> Iterator[dict]:
        """
        Iterate over all dandisets from the API (handles pagination).

        Yields:
            Dandiset metadata dictionaries from API
        """
        url: str | None = f"{self.api_url}/dandisets/"
        params: dict[str, Any] = {"page_size": self.PAGE_SIZE, "ordering": "identifier"}

        while url:
            try:
                response = self.session.get(url, params=params, timeout=60)
                response.raise_for_status()
                data = response.json()

                yield from data.get("results", [])

                # Follow pagination
                url = data.get("next")
                params = {}  # Next URL includes params

            except requests.RequestException as e:
                logger.error(f"DANDI API error: {e}")
                break

    def _dandiset_to_item(self, dandiset: dict, include_draft: bool = False) -> Item | None:
        """
        Convert a dandiset API response to an Item.

        Args:
            dandiset: Dandiset metadata from API
            include_draft: Whether to include draft versions

        Returns:
            Item with flavors for each published version, or None if no versions
        """
        identifier = dandiset.get("identifier", "")
        if not identifier:
            return None

        # Extract most recent version info for name
        draft_version = dandiset.get("draft_version", {})
        most_recent = dandiset.get("most_recent_published_version") or draft_version

        name = most_recent.get("name", f"Dandiset {identifier}")
        item_id = f"dandi:{identifier}"
        homepage = f"https://dandiarchive.org/dandiset/{identifier}"

        # Get all versions
        flavors = self._get_versions(identifier, include_draft=include_draft)

        if not flavors:
            logger.debug(f"Dandiset {identifier} has no published versions, skipping")
            return None

        return Item(
            item_id=item_id,
            name=name,
            homepage=homepage,
            flavors=flavors,
        )

    def _get_versions(self, dandiset_id: str, include_draft: bool = False) -> list[ItemFlavor]:
        """
        Get all versions for a dandiset.

        Args:
            dandiset_id: The dandiset identifier (e.g., "000003")
            include_draft: Whether to include draft version

        Returns:
            List of ItemFlavor objects for each version with a DOI
        """
        url: str | None = f"{self.api_url}/dandisets/{dandiset_id}/versions/"
        flavors: list[ItemFlavor] = []

        try:
            # Paginate through versions
            params: dict[str, Any] = {"page_size": 100, "ordering": "-created"}

            while url:
                response = self.session.get(url, params=params, timeout=60)
                response.raise_for_status()
                data = response.json()

                for version in data.get("results", []):
                    flavor = self._version_to_flavor(dandiset_id, version, include_draft)
                    if flavor:
                        flavors.append(flavor)

                url = data.get("next")
                params = {}

        except requests.RequestException as e:
            logger.warning(f"Failed to fetch versions for dandiset {dandiset_id}: {e}")

        return flavors

    def _version_to_flavor(
        self, dandiset_id: str, version: dict, include_draft: bool = False
    ) -> ItemFlavor | None:
        """
        Convert a version API response to an ItemFlavor.

        Args:
            dandiset_id: The dandiset identifier
            version: Version metadata from API
            include_draft: Whether to include draft versions

        Returns:
            ItemFlavor with DOI ref, or None if draft and not included
        """
        version_str = version.get("version", "")
        status = version.get("status", "")

        # DANDI API uses "Valid" for published versions with DOIs
        # "Published" status is confusingly used for draft versions
        # Draft versions have version_str == "draft"
        is_draft = version_str == "draft"

        # Skip draft versions unless requested
        if is_draft and not include_draft:
            return None

        # Published versions (status="Valid") have DOIs in the format:
        # 10.48324/dandi.{dandiset_id}/{version}
        # Draft versions don't have DOIs
        if status == "Valid" and not is_draft:
            doi = f"10.48324/dandi.{dandiset_id}/{version_str}"
            refs = [ItemRef(ref_type=RefType.doi, ref_value=doi)]
        elif include_draft and is_draft:
            # For drafts, we can still track them but without DOI
            refs = [
                ItemRef(
                    ref_type=RefType.url,
                    ref_value=f"https://dandiarchive.org/dandiset/{dandiset_id}/draft",
                )
            ]
        else:
            return None

        # Parse release date
        created = version.get("created")
        release_date = None
        if created:
            with contextlib.suppress(ValueError, TypeError):
                # API returns ISO format datetime
                release_date = date.fromisoformat(created[:10])

        return ItemFlavor(
            flavor_id=version_str,
            name=version.get("name"),
            release_date=release_date,
            refs=refs,
        )
