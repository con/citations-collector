"""Tests for Zotero sync module."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from citations_collector.models import CitationRecord, Collection
from citations_collector.zotero_sync import SyncReport, ZoteroSyncer


def _make_citation(**kwargs) -> CitationRecord:
    """Create a CitationRecord with sensible defaults."""
    defaults = {
        "item_id": "dandi:000020",
        "item_name": "Test Dataset",
        "item_flavor": "cites",
        "citation_doi": "10.1234/test",
        "citation_title": "Test Paper",
        "citation_authors": "John Doe; Jane Smith",
        "citation_year": 2024,
        "citation_relationship": "Cites",
        "citation_source": "crossref",
        "citation_status": "active",
        "citation_type": "Preprint",
        "citation_url": "https://example.com/paper",
        "pdf_url": "https://example.com/paper.pdf",
    }
    defaults.update(kwargs)
    return CitationRecord(**defaults)


def _make_collection() -> Collection:
    """Create a minimal Collection for testing."""
    return Collection(name="Test Collection", items=[])


def _create_syncer() -> ZoteroSyncer:
    """Create a ZoteroSyncer with mocked pyzotero."""
    with patch("citations_collector.zotero_sync.zotero.Zotero"):
        syncer = ZoteroSyncer(api_key="fake", group_id=12345, collection_key="ABCDEF")
    return syncer


@pytest.mark.ai_generated
def test_sync_creates_hierarchy() -> None:
    """Sync creates collection hierarchy and items."""
    syncer = _create_syncer()
    mock_zot = syncer.zot

    # No existing subcollections or items
    mock_zot.collections_sub.return_value = []
    mock_zot.everything.return_value = []
    mock_zot.create_collections.return_value = {"successful": {"0": {"key": "NEW_COLL_KEY"}}}
    mock_zot.create_items.return_value = {"successful": {"0": {"key": "NEW_ITEM_KEY"}}}

    citations = [_make_citation()]
    report = syncer.sync(_make_collection(), citations)

    assert report.collections_created == 2  # item-level + flavor-level
    assert report.items_created == 1
    assert report.attachments_created == 1  # pdf_url is set
    assert mock_zot.create_collections.call_count == 2
    assert mock_zot.create_items.call_count == 2  # item + attachment


@pytest.mark.ai_generated
def test_sync_dry_run() -> None:
    """Dry run creates no API writes."""
    syncer = _create_syncer()
    mock_zot = syncer.zot

    mock_zot.collections_sub.return_value = []
    mock_zot.everything.return_value = []

    citations = [_make_citation()]
    report = syncer.sync(_make_collection(), citations, dry_run=True)

    assert report.collections_created >= 1
    assert report.items_created == 1
    mock_zot.create_collections.assert_not_called()
    mock_zot.create_items.assert_not_called()


@pytest.mark.ai_generated
def test_sync_skips_existing() -> None:
    """Items with matching tracker key are skipped."""
    syncer = _create_syncer()
    mock_zot = syncer.zot

    citation = _make_citation()
    tracker_key = ZoteroSyncer._make_tracker_key(citation)

    # Simulate existing item with matching tracker key
    mock_zot.collections_sub.return_value = [
        {"key": "ITEM_COLL", "data": {"name": "000020 - Test Dataset"}},
    ]
    # First call returns item-level subcollections, second returns flavor-level
    mock_zot.collections_sub.side_effect = [
        [{"key": "ITEM_COLL", "data": {"name": "000020 - Test Dataset"}}],
        [{"key": "FLAVOR_COLL", "data": {"name": "cites"}}],
    ]
    mock_zot.everything.return_value = [
        {
            "data": {
                "itemType": "journalArticle",
                "extra": f"CitationTracker: {tracker_key}",
            }
        }
    ]

    report = syncer.sync(_make_collection(), [citation])

    assert report.items_skipped == 1
    assert report.items_created == 0
    mock_zot.create_items.assert_not_called()


@pytest.mark.ai_generated
def test_strip_prefix() -> None:
    """Strip namespace prefix from item IDs."""
    assert ZoteroSyncer._strip_prefix("dandi:000020") == "000020"
    assert ZoteroSyncer._strip_prefix("plain") == "plain"
    assert ZoteroSyncer._strip_prefix("a:b:c") == "b:c"


@pytest.mark.ai_generated
def test_citation_to_zotero_item() -> None:
    """Verify field mapping from CitationRecord to Zotero item dict."""
    syncer = _create_syncer()
    citation = _make_citation()

    item = syncer._citation_to_zotero_item(citation, ["COLL_KEY", "PARENT_KEY"])

    assert item["itemType"] == "preprint"  # Preprint type mapping
    assert item["title"] == "Test Paper"
    assert item["DOI"] == "10.1234/test"
    assert item["url"] == "https://example.com/paper"
    assert item["date"] == "2024"
    assert item["collections"] == ["COLL_KEY", "PARENT_KEY"]
    assert "CitationTracker:" in item["extra"]
    # Verify authors parsed
    assert len(item["creators"]) == 2
    assert item["creators"][0]["firstName"] == "John"
    assert item["creators"][0]["lastName"] == "Doe"
    assert item["creators"][1]["firstName"] == "Jane"
    assert item["creators"][1]["lastName"] == "Smith"


@pytest.mark.ai_generated
def test_citation_to_zotero_item_preprint_repository_field() -> None:
    """Verify preprints use 'repository' field instead of 'publicationTitle'."""
    syncer = _create_syncer()
    preprint = _make_citation(
        citation_journal="bioRxiv",
        citation_type="Preprint",
    )

    item = syncer._citation_to_zotero_item(preprint, ["COLL_KEY"])

    assert item["itemType"] == "preprint"
    assert item["repository"] == "bioRxiv"
    assert "publicationTitle" not in item


@pytest.mark.ai_generated
def test_citation_to_zotero_item_journal_article_publication_title() -> None:
    """Verify journal articles use 'publicationTitle' field."""
    syncer = _create_syncer()
    article = _make_citation(
        citation_journal="Nature",
        citation_type=None,  # Defaults to journalArticle
    )

    item = syncer._citation_to_zotero_item(article, ["COLL_KEY"])

    assert item["itemType"] == "journalArticle"
    assert item["publicationTitle"] == "Nature"
    assert "repository" not in item


@pytest.mark.ai_generated
def test_attach_linked_url() -> None:
    """Verify linked URL attachment creation."""
    syncer = _create_syncer()
    mock_zot = syncer.zot

    syncer._attach_linked_url("PARENT_KEY", "https://example.com/paper.pdf", "My Paper")

    mock_zot.create_items.assert_called_once()
    call_args = mock_zot.create_items.call_args[0][0]
    attachment = call_args[0]
    assert attachment["itemType"] == "attachment"
    assert attachment["linkMode"] == "linked_url"
    assert attachment["url"] == "https://example.com/paper.pdf"
    assert attachment["title"] == "My Paper"
    assert attachment["parentItem"] == "PARENT_KEY"
    assert attachment["contentType"] == "application/pdf"


@pytest.mark.ai_generated
def test_move_item_to_collections() -> None:
    """Verify moving an existing item to different collections."""
    syncer = _create_syncer()
    mock_zot = syncer.zot

    existing_item = {
        "data": {
            "key": "ITEM_KEY",
            "version": 5,
            "title": "Test Paper",
            "collections": ["OLD_COLL_1", "OLD_COLL_2"],
        }
    }

    syncer._move_item_to_collections(existing_item, ["NEW_COLL_1"])

    mock_zot.update_item.assert_called_once()
    call_args = mock_zot.update_item.call_args[0][0]
    assert call_args["key"] == "ITEM_KEY"
    assert call_args["version"] == 5
    assert call_args["collections"] == ["NEW_COLL_1"]


@pytest.mark.ai_generated
def test_sync_single_citation_moves_to_merged() -> None:
    """Verify that an existing active item is moved to merged collection."""
    syncer = _create_syncer()
    mock_zot = syncer.zot

    citation = CitationRecord(
        item_id="dataset_001",
        item_flavor="v1.0",
        citation_doi="10.1234/test",
        citation_title="Test Paper",
        citation_relationship="Cites",
        citation_source="crossref",
        citation_status="merged",
        citation_merged_into="10.1234/published",
    )

    # Existing item in active collections
    existing_items = {
        "dataset_001/v1.0/10.1234/test": {
            "data": {
                "key": "EXISTING_KEY",
                "version": 3,
                "title": "Test Paper",
                "collections": ["ACTIVE_COLL_1", "ACTIVE_COLL_2"],
                "extra": "CitationTracker: dataset_001/v1.0/10.1234/test",
            }
        }
    }

    report = SyncReport()

    # Call with is_merged=True and new collection
    syncer._sync_single_citation(
        citation,
        ["MERGED_COLL"],
        existing_items,
        dry_run=False,
        report=report,
        is_merged=True,
    )

    # Should update the item's collections, not create a new item
    mock_zot.update_item.assert_called_once()
    assert report.items_updated == 1
    assert report.items_created == 0


@pytest.mark.ai_generated
def test_sync_single_citation_dry_run_merged_move() -> None:
    """Verify dry run reports moving merged items correctly."""
    syncer = _create_syncer()

    citation = CitationRecord(
        item_id="dataset_001",
        item_flavor="v1.0",
        citation_doi="10.1234/test",
        citation_title="Test Paper",
        citation_relationship="Cites",
        citation_source="crossref",
        citation_status="merged",
    )

    existing_items = {
        "dataset_001/v1.0/10.1234/test": {
            "data": {
                "key": "EXISTING_KEY",
                "version": 3,
                "collections": ["ACTIVE_COLL"],
                "extra": "CitationTracker: dataset_001/v1.0/10.1234/test",
            }
        }
    }

    report = SyncReport()

    syncer._sync_single_citation(
        citation,
        ["MERGED_COLL"],
        existing_items,
        dry_run=True,
        report=report,
        is_merged=True,
    )

    # Should report as updated in dry run
    assert report.items_updated == 1
    assert report.items_created == 0


@pytest.mark.ai_generated
def test_sync_single_citation_adds_related_items() -> None:
    """Verify that merged items get related items links to published versions."""
    syncer = _create_syncer()
    mock_zot = syncer.zot

    # Preprint citation that's been merged
    preprint = CitationRecord(
        item_id="dataset_001",
        item_flavor="v1.0",
        citation_doi="10.1101/2025.01.01.123456",
        citation_title="Test Paper (preprint)",
        citation_relationship="Cites",
        citation_source="crossref",
        citation_status="merged",
        citation_merged_into="10.1234/published",
    )

    # Both items already exist in Zotero
    existing_items = {
        "dataset_001/v1.0/10.1101/2025.01.01.123456": {
            "data": {
                "key": "PREPRINT_KEY",
                "version": 3,
                "title": "Test Paper (preprint)",
                "collections": ["ACTIVE_COLL"],
                "extra": "CitationTracker: dataset_001/v1.0/10.1101/2025.01.01.123456",
                "relations": {},  # No relations yet
            }
        },
        "dataset_001/v1.0/10.1234/published": {
            "data": {
                "key": "PUBLISHED_KEY",
                "version": 5,
                "title": "Test Paper (published)",
                "collections": ["ACTIVE_COLL"],
                "extra": "CitationTracker: dataset_001/v1.0/10.1234/published",
                "relations": {},
            }
        },
    }

    # Mock the item() call for refreshing items
    def mock_item(key: str):
        if key == "PUBLISHED_KEY":
            return existing_items["dataset_001/v1.0/10.1234/published"]
        return existing_items["dataset_001/v1.0/10.1101/2025.01.01.123456"]

    mock_zot.item.side_effect = mock_item

    report = SyncReport()

    # Sync the preprint to Merged collection
    syncer._sync_single_citation(
        preprint,
        ["MERGED_COLL"],
        existing_items,
        dry_run=False,
        report=report,
        is_merged=True,
    )

    # Should have moved the item and added at least one relation
    assert report.items_updated == 1
    assert mock_zot.update_item.call_count >= 2  # Move + at least one relation

    # Check that update_item was called with relations
    update_calls = mock_zot.update_item.call_args_list

    # Find the relation updates (they have 'relations' key)
    relation_updates = [call[0][0] for call in update_calls if "relations" in call[0][0]]
    assert len(relation_updates) >= 1  # At least one direction

    # Verify at least the preprint got a relation to the published version
    preprint_update = next((u for u in relation_updates if u["key"] == "PREPRINT_KEY"), None)
    assert preprint_update is not None

    # Check that the published item URI is in the preprint's relations
    expected_published_uri = "http://zotero.org/groups/12345/items/PUBLISHED_KEY"
    preprint_relations = preprint_update.get("relations", {}).get("dc:relation", [])
    assert expected_published_uri in preprint_relations
