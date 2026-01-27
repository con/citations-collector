"""Tests for Zotero sync module."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from citations_collector.models import CitationRecord, Collection
from citations_collector.zotero_sync import ZoteroSyncer


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

    item = syncer._citation_to_zotero_item(citation, "COLL_KEY")

    assert item["itemType"] == "preprint"  # Preprint type mapping
    assert item["title"] == "Test Paper"
    assert item["DOI"] == "10.1234/test"
    assert item["url"] == "https://example.com/paper"
    assert item["date"] == "2024"
    assert item["collections"] == ["COLL_KEY"]
    assert "CitationTracker:" in item["extra"]
    # Verify authors parsed
    assert len(item["creators"]) == 2
    assert item["creators"][0]["firstName"] == "John"
    assert item["creators"][0]["lastName"] == "Doe"
    assert item["creators"][1]["firstName"] == "Jane"
    assert item["creators"][1]["lastName"] == "Smith"


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
