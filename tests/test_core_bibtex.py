"""Integration tests for BibTeX source in CitationCollector."""

from __future__ import annotations

from pathlib import Path

import pytest

from citations_collector.core import CitationCollector
from citations_collector.models.generated import Collection, SourceConfig


@pytest.fixture
def test_bib(tmp_path: Path) -> Path:
    """Create test BibTeX file."""
    bib_content = """
@article{test1,
    title = {Test Dandiset One},
    year = {2023},
    doi = {10.48324/dandi.000003/0.230629.1955}
}

@article{test2,
    title = {Test Dandiset Two},
    year = {2024},
    doi = {10.48324/dandi.000005/0.240101.1234}
}
"""
    bib_file = tmp_path / "test.bib"
    bib_file.write_text(bib_content)
    return bib_file


@pytest.mark.ai_generated
def test_core_populate_from_bibtex_relative_path(tmp_path: Path, test_bib: Path) -> None:
    """Test populate_from_source with BibTeX using relative path."""
    # Create collection YAML in same dir as BibTeX
    collection_yaml = tmp_path / "collection.yaml"

    collection = Collection(
        name="Test Collection",
        source=SourceConfig(
            type="bibtex",
            bibtex_file="test.bib",  # Relative path
            bib_field="doi",
            ref_type="doi",
            ref_regex=r"10\.48324/(?P<item_id>dandi\.\d{6})/(?P<flavor_id>[\d.]+)",
            update_items="false",
        ),
        items=[],
    )

    collector = CitationCollector(collection, collection_path=collection_yaml)
    collector.populate_from_source()

    # Verify items were loaded
    assert len(collector.collection.items) == 2
    assert collector.collection.items[0].item_id == "dandi.000003"
    assert collector.collection.items[1].item_id == "dandi.000005"


@pytest.mark.ai_generated
def test_core_populate_from_bibtex_absolute_path(test_bib: Path) -> None:
    """Test populate_from_source with BibTeX using absolute path."""
    collection = Collection(
        name="Test Collection",
        source=SourceConfig(
            type="bibtex",
            bibtex_file=str(test_bib),  # Absolute path
            bib_field="doi",
            ref_type="doi",
            ref_regex=r"10\.48324/(?P<item_id>dandi\.\d{6})/(?P<flavor_id>[\d.]+)",
            update_items="false",
        ),
        items=[],
    )

    collector = CitationCollector(collection)
    collector.populate_from_source()

    assert len(collector.collection.items) == 2


@pytest.mark.ai_generated
def test_core_update_items_sync(test_bib: Path) -> None:
    """Test update_items='sync' replaces existing items."""
    collection = Collection(
        name="Test Collection",
        source=SourceConfig(
            type="bibtex",
            bibtex_file=str(test_bib),
            bib_field="doi",
            ref_type="doi",
            ref_regex=r"10\.48324/(?P<item_id>dandi\.\d{6})/(?P<flavor_id>[\d.]+)",
            update_items="sync",
        ),
        items=[],  # Start with no items
    )

    collector = CitationCollector(collection)
    collector.populate_from_source()

    assert len(collector.collection.items) == 2


@pytest.mark.ai_generated
def test_core_update_items_add(test_bib: Path) -> None:
    """Test update_items='add' adds only new items."""
    from citations_collector.models.generated import Item, ItemFlavor, ItemRef

    # Create collection with one existing item
    existing_item = Item(
        item_id="dandi.000003",  # Same as one in BibTeX
        name="Existing Item",
        flavors=[
            ItemFlavor(
                flavor_id="existing",
                refs=[ItemRef(ref_type="doi", ref_value="10.1234/existing")],
            )
        ],
    )

    collection = Collection(
        name="Test Collection",
        source=SourceConfig(
            type="bibtex",
            bibtex_file=str(test_bib),
            bib_field="doi",
            ref_type="doi",
            ref_regex=r"10\.48324/(?P<item_id>dandi\.\d{6})/(?P<flavor_id>[\d.]+)",
            update_items="add",
        ),
        items=[existing_item],
    )

    collector = CitationCollector(collection)
    collector.populate_from_source()

    # Should have 2 items: existing + dandi.000005 (dandi.000003 is duplicate)
    assert len(collector.collection.items) == 2
    item_ids = {item.item_id for item in collector.collection.items}
    assert "dandi.000003" in item_ids
    assert "dandi.000005" in item_ids


@pytest.mark.ai_generated
def test_core_missing_required_fields(test_bib: Path) -> None:
    """Test error handling when required BibTeX fields are missing."""
    collection = Collection(
        name="Test Collection",
        source=SourceConfig(
            type="bibtex",
            bibtex_file=str(test_bib),
            # Missing bib_field, ref_type, ref_regex
        ),
        items=[],
    )

    collector = CitationCollector(collection)

    # Should log errors but not crash
    collector.populate_from_source()

    # Items should not be populated
    assert len(collector.collection.items) == 0


@pytest.mark.ai_generated
def test_core_bibtex_file_not_found() -> None:
    """Test error handling when BibTeX file doesn't exist."""
    collection = Collection(
        name="Test Collection",
        source=SourceConfig(
            type="bibtex",
            bibtex_file="/nonexistent/file.bib",
            bib_field="doi",
            ref_type="doi",
            ref_regex=r"(?P<item_id>.*)",
        ),
        items=[],
    )

    collector = CitationCollector(collection)
    collector.populate_from_source()

    # Should log error but not crash
    assert len(collector.collection.items) == 0
