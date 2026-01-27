"""Tests for Zotero importer."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from citations_collector.importers.zotero import ZoteroImporter


@pytest.mark.ai_generated
def test_zotero_importer_basic() -> None:
    """Test basic Zotero import with DOI items."""
    # Mock Zotero item data
    mock_items = [
        {
            "key": "ABC123",
            "data": {
                "itemType": "journalArticle",
                "title": "Test Article",
                "DOI": "10.1234/test.article",
                "url": "https://example.com/article",
                "date": "2023-05-15",
            },
        },
        {
            "key": "DEF456",
            "data": {
                "itemType": "book",
                "title": "Test Book",
                "DOI": "10.5678/test.book",
                "date": "2022",
            },
        },
    ]

    with patch("citations_collector.importers.zotero.zotero.Zotero") as mock_zotero_class:
        mock_zot = MagicMock()
        mock_zotero_class.return_value = mock_zot
        mock_zot.everything.return_value = mock_items

        importer = ZoteroImporter(api_key="test-key")
        collection = importer.import_group(group_id=12345)

        # Verify Zotero was initialized correctly
        mock_zotero_class.assert_called_once_with(12345, "group", "test-key")

        # Verify collection
        assert collection.source_type == "zotero"
        assert collection.zotero_group_id == 12345
        assert len(collection.items) == 2

        # Verify first item (DOI-based ID)
        item1 = collection.items[0]
        assert item1.item_id == "doi:10.1234/test.article"
        assert item1.name == "Test Article"
        assert len(item1.flavors) == 1
        assert item1.flavors[0].refs[0].ref_type == "doi"
        assert item1.flavors[0].refs[0].ref_value == "10.1234/test.article"

        # Verify second item
        item2 = collection.items[1]
        assert item2.item_id == "doi:10.5678/test.book"


@pytest.mark.ai_generated
def test_zotero_importer_skip_attachments() -> None:
    """Test that attachments and notes are skipped."""
    mock_items = [
        {
            "key": "ABC123",
            "data": {
                "itemType": "journalArticle",
                "title": "Test Article",
                "DOI": "10.1234/test",
            },
        },
        {
            "key": "ATT001",
            "data": {
                "itemType": "attachment",
                "title": "PDF attachment",
            },
        },
        {
            "key": "NOTE01",
            "data": {
                "itemType": "note",
                "title": "My note",
            },
        },
    ]

    with patch("citations_collector.importers.zotero.zotero.Zotero") as mock_zotero_class:
        mock_zot = MagicMock()
        mock_zotero_class.return_value = mock_zot
        mock_zot.everything.return_value = mock_items

        importer = ZoteroImporter()
        collection = importer.import_group(group_id=12345)

        # Only the article should be imported
        assert len(collection.items) == 1
        assert collection.items[0].item_id == "doi:10.1234/test"


@pytest.mark.ai_generated
def test_zotero_importer_doi_from_url() -> None:
    """Test extracting DOI from URL field."""
    mock_items = [
        {
            "key": "ABC123",
            "data": {
                "itemType": "journalArticle",
                "title": "Test Article",
                "url": "https://doi.org/10.1234/from.url",
            },
        }
    ]

    with patch("citations_collector.importers.zotero.zotero.Zotero") as mock_zotero_class:
        mock_zot = MagicMock()
        mock_zotero_class.return_value = mock_zot
        mock_zot.everything.return_value = mock_items

        importer = ZoteroImporter()
        collection = importer.import_group(group_id=12345)

        assert len(collection.items) == 1
        assert collection.items[0].flavors[0].refs[0].ref_value == "10.1234/from.url"


@pytest.mark.ai_generated
def test_zotero_importer_doi_from_extra() -> None:
    """Test extracting DOI from extra field."""
    mock_items = [
        {
            "key": "ABC123",
            "data": {
                "itemType": "journalArticle",
                "title": "Test Article",
                "extra": "DOI: 10.1234/from.extra\nPMID: 12345678",
            },
        }
    ]

    with patch("citations_collector.importers.zotero.zotero.Zotero") as mock_zotero_class:
        mock_zot = MagicMock()
        mock_zotero_class.return_value = mock_zot
        mock_zot.everything.return_value = mock_items

        importer = ZoteroImporter()
        collection = importer.import_group(group_id=12345)

        assert len(collection.items) == 1
        item = collection.items[0]
        assert item.item_id == "doi:10.1234/from.extra"

        # Should also have PMID
        refs = item.flavors[0].refs
        ref_types = {r.ref_type for r in refs}
        assert "doi" in ref_types
        assert "pmid" in ref_types


@pytest.mark.ai_generated
def test_zotero_importer_url_fallback() -> None:
    """Test falling back to URL when no DOI available."""
    mock_items = [
        {
            "key": "ABC123",
            "data": {
                "itemType": "webpage",
                "title": "Test Webpage",
                "url": "https://example.com/page",
            },
        }
    ]

    with patch("citations_collector.importers.zotero.zotero.Zotero") as mock_zotero_class:
        mock_zot = MagicMock()
        mock_zotero_class.return_value = mock_zot
        mock_zot.everything.return_value = mock_items

        importer = ZoteroImporter()
        collection = importer.import_group(group_id=12345)

        assert len(collection.items) == 1
        item = collection.items[0]
        assert item.item_id == "zotero:ABC123"  # Uses Zotero key since no DOI
        assert item.flavors[0].refs[0].ref_type == "url"
        assert item.flavors[0].refs[0].ref_value == "https://example.com/page"


@pytest.mark.ai_generated
def test_zotero_importer_skip_no_identifier() -> None:
    """Test skipping items without any usable identifier."""
    mock_items = [
        {
            "key": "ABC123",
            "data": {
                "itemType": "journalArticle",
                "title": "Useless Item",
                # No DOI, no URL
            },
        }
    ]

    with patch("citations_collector.importers.zotero.zotero.Zotero") as mock_zotero_class:
        mock_zot = MagicMock()
        mock_zotero_class.return_value = mock_zot
        mock_zot.everything.return_value = mock_items

        importer = ZoteroImporter()
        collection = importer.import_group(group_id=12345)

        # Item should be skipped
        assert len(collection.items) == 0


@pytest.mark.ai_generated
def test_zotero_importer_collection_key() -> None:
    """Test importing from a specific collection."""
    mock_items = [
        {
            "key": "ABC123",
            "data": {
                "itemType": "journalArticle",
                "title": "Collection Item",
                "DOI": "10.1234/test",
            },
        }
    ]

    mock_collection = {"data": {"name": "My Collection"}}

    with patch("citations_collector.importers.zotero.zotero.Zotero") as mock_zotero_class:
        mock_zot = MagicMock()
        mock_zotero_class.return_value = mock_zot
        mock_zot.everything.return_value = mock_items
        mock_zot.collection.return_value = mock_collection

        importer = ZoteroImporter()
        collection = importer.import_group(group_id=12345, collection_key="COLL001")

        # Verify collection_items was called
        mock_zot.collection_items.assert_called_once_with("COLL001")
        mock_zot.collection.assert_called_once_with("COLL001")

        assert collection.name == "My Collection"
        assert collection.zotero_collection_key == "COLL001"


@pytest.mark.ai_generated
def test_zotero_importer_with_limit() -> None:
    """Test importing with a limit."""
    with patch("citations_collector.importers.zotero.zotero.Zotero") as mock_zotero_class:
        mock_zot = MagicMock()
        mock_zotero_class.return_value = mock_zot
        mock_zot.items.return_value = []

        importer = ZoteroImporter()
        importer.import_group(group_id=12345, limit=10)

        # Verify limit was passed
        mock_zot.items.assert_called_once_with(limit=10)


@pytest.mark.ai_generated
def test_zotero_importer_date_parsing() -> None:
    """Test various date format parsing."""
    mock_items = [
        {
            "key": "DATE1",
            "data": {
                "itemType": "journalArticle",
                "title": "ISO Date",
                "DOI": "10.1234/iso",
                "date": "2023-05-15",
            },
        },
        {
            "key": "DATE2",
            "data": {
                "itemType": "journalArticle",
                "title": "Year Only",
                "DOI": "10.1234/year",
                "date": "2022",
            },
        },
        {
            "key": "DATE3",
            "data": {
                "itemType": "journalArticle",
                "title": "No Date",
                "DOI": "10.1234/nodate",
            },
        },
    ]

    with patch("citations_collector.importers.zotero.zotero.Zotero") as mock_zotero_class:
        mock_zot = MagicMock()
        mock_zotero_class.return_value = mock_zot
        mock_zot.everything.return_value = mock_items

        importer = ZoteroImporter()
        collection = importer.import_group(group_id=12345)

        # ISO date
        assert collection.items[0].flavors[0].release_date.year == 2023
        assert collection.items[0].flavors[0].release_date.month == 5

        # Year only
        assert collection.items[1].flavors[0].release_date.year == 2022
        assert collection.items[1].flavors[0].release_date.month == 1

        # No date
        assert collection.items[2].flavors[0].release_date is None


@pytest.mark.ai_generated
def test_zotero_importer_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test reading API key from environment variable."""
    monkeypatch.setenv("ZOTERO_API_KEY", "env-api-key")

    with patch("citations_collector.importers.zotero.zotero.Zotero") as mock_zotero_class:
        mock_zot = MagicMock()
        mock_zotero_class.return_value = mock_zot
        mock_zot.everything.return_value = []

        importer = ZoteroImporter()  # No explicit key
        importer.import_group(group_id=12345)

        mock_zotero_class.assert_called_once_with(12345, "group", "env-api-key")


@pytest.mark.ai_generated
def test_zotero_importer_error_handling() -> None:
    """Test handling of API errors."""
    with patch("citations_collector.importers.zotero.zotero.Zotero") as mock_zotero_class:
        mock_zot = MagicMock()
        mock_zotero_class.return_value = mock_zot
        mock_zot.everything.side_effect = Exception("API Error")

        importer = ZoteroImporter()
        collection = importer.import_group(group_id=12345)

        # Should return empty collection on error
        assert len(collection.items) == 0


@pytest.mark.ai_generated
@pytest.mark.integration
def test_zotero_importer_real_public_group() -> None:
    """Integration test with a real public Zotero group (dandi-bib)."""
    # dandi-bib group is public and doesn't require API key
    importer = ZoteroImporter()
    collection = importer.import_group(group_id=5774211, limit=5)

    # Verify we got some items
    assert collection.zotero_group_id == 5774211
    assert len(collection.items) > 0
    assert len(collection.items) <= 5

    # Verify structure
    for item in collection.items:
        assert item.item_id
        assert len(item.flavors) == 1
        assert len(item.flavors[0].refs) > 0
