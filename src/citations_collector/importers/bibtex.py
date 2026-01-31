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

        Returns:
            Collection with items parsed from BibTeX entries
        """
        if not self.bibtex_file.exists():
            raise FileNotFoundError(f"BibTeX file not found: {self.bibtex_file}")

        # Parse BibTeX file
        library = bibtexparser.parse_file(self.bibtex_file)

        items: list[Item] = []
        skipped = 0

        for entry in library.entries:
            item = self._entry_to_item(entry)
            if item:
                items.append(item)
            else:
                skipped += 1

        logger.info(f"Imported {len(items)} items from {self.bibtex_file.name}, skipped {skipped}")

        return Collection(
            name=f"BibTeX: {self.bibtex_file.stem}",
            description=f"Items imported from {self.bibtex_file}",
            items=items,
        )

    def _entry_to_item(self, entry: Any) -> Item | None:
        """
        Convert BibTeX entry to Item.

        Args:
            entry: BibTeX entry from bibtexparser

        Returns:
            Item if reference can be parsed, None otherwise
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

        # Build Item
        item = Item(
            item_id=item_id,
            name=title or item_id,
            flavors=[flavor],
        )

        return item

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
