"""Import items from BibTeX files."""

from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path
from typing import Any

import bibtexparser

from citations_collector.models.generated import (
    Collection,
    Item,
    ItemFlavor,
    ItemRef,
    RefType,
)

logger = logging.getLogger(__name__)

# Suppress bibtexparser's duplicate key warnings - we handle deduplication ourselves
logging.getLogger("bibtexparser").setLevel(logging.ERROR)


class BibTeXImporter:
    """Import items from BibTeX files with regex-based parsing."""

    def __init__(
        self,
        bibtex_file: Path,
        bib_field: str,
        ref_type: RefType,
        ref_regex: str,
    ) -> None:
        """
        Initialize BibTeX importer.

        Args:
            bibtex_file: Path to .bib file
            bib_field: BibTeX field to extract reference from (e.g., 'doi')
            ref_type: Type of reference (e.g., RefType.doi)
            ref_regex: Regex with named groups (?P<item_id>...) and (?P<flavor_id>...)
        """
        self.bibtex_file = bibtex_file
        self.bib_field = bib_field
        self.ref_type = ref_type
        self.ref_pattern = re.compile(ref_regex)

        # Validate regex has required groups
        if "item_id" not in self.ref_pattern.groupindex:
            raise ValueError("ref_regex must contain (?P<item_id>...) named group")

    def import_all(self) -> Collection:
        """
        Import all entries from BibTeX file.

        Groups entries by item_id, creating one Item per unique item_id
        with multiple flavors (versions).

        Returns:
            Collection with items parsed from BibTeX entries
        """
        if not self.bibtex_file.exists():
            raise FileNotFoundError(f"BibTeX file not found: {self.bibtex_file}")

        # Parse BibTeX file
        library = bibtexparser.parse_file(str(self.bibtex_file))

        # Group flavors by item_id
        items_dict: dict[str, dict[str, Any]] = {}
        skipped = 0

        for entry in library.entries:
            result = self._entry_to_flavor(entry)
            if result:
                item_id, flavor, name = result
                if item_id not in items_dict:
                    items_dict[item_id] = {"name": name, "flavors": [], "seen_flavors": set()}
                # Deduplicate flavors by flavor_id
                if flavor.flavor_id not in items_dict[item_id]["seen_flavors"]:
                    items_dict[item_id]["flavors"].append(flavor)
                    items_dict[item_id]["seen_flavors"].add(flavor.flavor_id)
            else:
                skipped += 1

        # Build Item objects with merged flavors
        items = [
            Item(
                item_id=item_id,
                name=data["name"],
                flavors=data["flavors"],
            )
            for item_id, data in items_dict.items()
        ]

        total_flavors = sum(len(item.flavors) for item in items)
        logger.info(
            f"Imported {len(items)} items ({total_flavors} flavors) "
            f"from {self.bibtex_file.name}, skipped {skipped}"
        )

        return Collection(
            name=f"BibTeX: {self.bibtex_file.stem}",
            description=f"Items imported from {self.bibtex_file}",
            items=items,
        )

    def _entry_to_flavor(self, entry: Any) -> tuple[str, ItemFlavor, str] | None:
        """
        Convert BibTeX entry to flavor components.

        Args:
            entry: BibTeX entry from bibtexparser

        Returns:
            Tuple of (item_id, flavor, name) if reference can be parsed, None otherwise
        """
        # Get reference value from specified field
        ref_value = entry.fields_dict.get(self.bib_field)
        if not ref_value:
            logger.debug(f"Entry {entry.key} missing field '{self.bib_field}', skipping")
            return None

        ref_value_str = ref_value.value if hasattr(ref_value, "value") else str(ref_value)

        # Parse with regex to extract item_id and flavor_id
        match = self.ref_pattern.match(ref_value_str)
        if not match:
            logger.warning(
                f"Entry {entry.key}: '{self.bib_field}' value '{ref_value_str}' "
                f"doesn't match regex pattern, skipping"
            )
            return None

        # Normalize to lowercase for consistency (DOIs are case-insensitive)
        item_id = match.group("item_id").lower()
        flavor_id = match.group("flavor_id").lower() if "flavor_id" in match.groupdict() else "main"

        # Extract metadata
        title = self._get_field(entry, "title")
        year = self._get_field(entry, "year")
        release_date = self._parse_year(year) if year else None

        # Build ItemRef (normalize DOI to lowercase for consistency)
        item_ref = ItemRef(
            ref_type=self.ref_type,
            ref_value=ref_value_str.lower() if self.ref_type == RefType.doi else ref_value_str,
        )

        # Build ItemFlavor
        flavor = ItemFlavor(
            flavor_id=flavor_id,
            name=title or f"Version {flavor_id}",
            release_date=release_date,
            refs=[item_ref],
        )

        # Return components for grouping by item_id
        item_name = title or item_id
        return (item_id, flavor, item_name)

    def _get_field(self, entry: Any, field_name: str) -> str | None:
        """Extract field value from BibTeX entry."""
        field = entry.fields_dict.get(field_name)
        if not field:
            return None
        return field.value if hasattr(field, "value") else str(field)

    def _parse_year(self, year_str: str) -> date | None:
        """Parse year string to date (Jan 1 of that year)."""
        try:
            year = int(year_str)
            return date(year, 1, 1)
        except (ValueError, TypeError):
            logger.warning(f"Could not parse year: {year_str}")
            return None
