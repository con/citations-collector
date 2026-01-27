"""Tests for DANDI importer."""

from __future__ import annotations

import pytest
import responses

from citations_collector.importers.dandi import DANDIImporter


@pytest.mark.ai_generated
@responses.activate
def test_dandi_importer_single_dandiset() -> None:
    """Test importing a single dandiset with versions."""
    # Mock dandisets list endpoint
    dandisets_response = {
        "count": 1,
        "next": None,
        "results": [
            {
                "identifier": "000003",
                "draft_version": {"name": "Test Dandiset"},
                "most_recent_published_version": {
                    "name": "Test Dandiset",
                    "version": "0.210812.1448",
                },
            }
        ],
    }

    # Mock versions endpoint
    versions_response = {
        "count": 2,
        "next": None,
        "results": [
            {
                "version": "0.220126.1853",
                "status": "Valid",
                "name": "Test Dandiset v2",
                "created": "2022-01-26T18:53:00Z",
            },
            {
                "version": "0.210812.1448",
                "status": "Valid",
                "name": "Test Dandiset v1",
                "created": "2021-08-12T14:48:00Z",
            },
        ],
    }

    responses.add(
        responses.GET,
        "https://api.dandiarchive.org/api/dandisets/",
        json=dandisets_response,
        status=200,
    )

    responses.add(
        responses.GET,
        "https://api.dandiarchive.org/api/dandisets/000003/versions/",
        json=versions_response,
        status=200,
    )

    # Import
    importer = DANDIImporter()
    collection = importer.import_all()

    # Verify collection
    assert collection.name == "DANDI Archive"
    assert collection.source_type == "dandi"
    assert len(collection.items) == 1

    # Verify item
    item = collection.items[0]
    assert item.item_id == "dandi:000003"
    assert item.name == "Test Dandiset"
    assert item.homepage == "https://dandiarchive.org/dandiset/000003"

    # Verify flavors (versions)
    assert len(item.flavors) == 2

    # Check first flavor (most recent)
    flavor1 = item.flavors[0]
    assert flavor1.flavor_id == "0.220126.1853"
    assert len(flavor1.refs) == 1
    assert flavor1.refs[0].ref_type == "doi"
    assert flavor1.refs[0].ref_value == "10.48324/dandi.000003/0.220126.1853"

    # Check second flavor
    flavor2 = item.flavors[1]
    assert flavor2.flavor_id == "0.210812.1448"
    assert flavor2.refs[0].ref_value == "10.48324/dandi.000003/0.210812.1448"


@pytest.mark.ai_generated
@responses.activate
def test_dandi_importer_with_limit() -> None:
    """Test importing with a limit on dandisets."""
    # Mock dandisets list with 3 dandisets
    dandisets_response = {
        "count": 3,
        "next": None,
        "results": [
            {
                "identifier": "000001",
                "most_recent_published_version": {"name": "Dandiset 1", "version": "0.1"},
            },
            {
                "identifier": "000002",
                "most_recent_published_version": {"name": "Dandiset 2", "version": "0.1"},
            },
            {
                "identifier": "000003",
                "most_recent_published_version": {"name": "Dandiset 3", "version": "0.1"},
            },
        ],
    }

    # Mock versions for each dandiset
    for i in range(1, 4):
        responses.add(
            responses.GET,
            f"https://api.dandiarchive.org/api/dandisets/00000{i}/versions/",
            json={
                "count": 1,
                "next": None,
                "results": [
                    {"version": "0.1", "status": "Valid", "created": "2021-01-01T00:00:00Z"}
                ],
            },
            status=200,
        )

    responses.add(
        responses.GET,
        "https://api.dandiarchive.org/api/dandisets/",
        json=dandisets_response,
        status=200,
    )

    # Import with limit=2
    importer = DANDIImporter()
    collection = importer.import_all(limit=2)

    # Should only have 2 items
    assert len(collection.items) == 2
    assert collection.items[0].item_id == "dandi:000001"
    assert collection.items[1].item_id == "dandi:000002"


@pytest.mark.ai_generated
@responses.activate
def test_dandi_importer_skip_draft_by_default() -> None:
    """Test that draft versions are skipped by default."""
    dandisets_response = {
        "count": 1,
        "next": None,
        "results": [
            {
                "identifier": "000001",
                "draft_version": {"name": "Draft Dandiset", "version": "draft"},
            }
        ],
    }

    versions_response = {
        "count": 1,
        "next": None,
        "results": [{"version": "draft", "status": "Draft", "created": "2021-01-01T00:00:00Z"}],
    }

    responses.add(
        responses.GET,
        "https://api.dandiarchive.org/api/dandisets/",
        json=dandisets_response,
        status=200,
    )

    responses.add(
        responses.GET,
        "https://api.dandiarchive.org/api/dandisets/000001/versions/",
        json=versions_response,
        status=200,
    )

    importer = DANDIImporter()
    collection = importer.import_all()

    # Should have no items (draft-only dandiset skipped)
    assert len(collection.items) == 0


@pytest.mark.ai_generated
@responses.activate
def test_dandi_importer_include_draft() -> None:
    """Test including draft versions when requested."""
    dandisets_response = {
        "count": 1,
        "next": None,
        "results": [
            {
                "identifier": "000001",
                "draft_version": {"name": "Draft Dandiset", "version": "draft"},
            }
        ],
    }

    versions_response = {
        "count": 1,
        "next": None,
        "results": [{"version": "draft", "status": "Draft", "created": "2021-01-01T00:00:00Z"}],
    }

    responses.add(
        responses.GET,
        "https://api.dandiarchive.org/api/dandisets/",
        json=dandisets_response,
        status=200,
    )

    responses.add(
        responses.GET,
        "https://api.dandiarchive.org/api/dandisets/000001/versions/",
        json=versions_response,
        status=200,
    )

    importer = DANDIImporter()
    collection = importer.import_all(include_draft=True)

    # Should have the draft item
    assert len(collection.items) == 1
    item = collection.items[0]
    assert item.item_id == "dandi:000001"
    assert len(item.flavors) == 1

    # Draft flavor should have URL ref, not DOI
    flavor = item.flavors[0]
    assert flavor.flavor_id == "draft"
    assert flavor.refs[0].ref_type == "url"
    assert "draft" in flavor.refs[0].ref_value


@pytest.mark.ai_generated
@responses.activate
def test_dandi_importer_pagination() -> None:
    """Test handling of paginated results."""
    # First page
    page1_response = {
        "count": 2,
        "next": "https://api.dandiarchive.org/api/dandisets/?page=2",
        "results": [
            {
                "identifier": "000001",
                "most_recent_published_version": {"name": "Dandiset 1", "version": "0.1"},
            }
        ],
    }

    # Second page
    page2_response = {
        "count": 2,
        "next": None,
        "results": [
            {
                "identifier": "000002",
                "most_recent_published_version": {"name": "Dandiset 2", "version": "0.1"},
            }
        ],
    }

    responses.add(
        responses.GET,
        "https://api.dandiarchive.org/api/dandisets/",
        json=page1_response,
        status=200,
    )

    responses.add(
        responses.GET,
        "https://api.dandiarchive.org/api/dandisets/?page=2",
        json=page2_response,
        status=200,
    )

    # Mock versions for both
    for i in [1, 2]:
        responses.add(
            responses.GET,
            f"https://api.dandiarchive.org/api/dandisets/00000{i}/versions/",
            json={
                "count": 1,
                "next": None,
                "results": [
                    {"version": "0.1", "status": "Valid", "created": "2021-01-01T00:00:00Z"}
                ],
            },
            status=200,
        )

    importer = DANDIImporter()
    collection = importer.import_all()

    # Should have both items from pagination
    assert len(collection.items) == 2


@pytest.mark.ai_generated
@responses.activate
def test_dandi_importer_api_error() -> None:
    """Test handling of API errors."""
    responses.add(
        responses.GET,
        "https://api.dandiarchive.org/api/dandisets/",
        status=500,
    )

    importer = DANDIImporter()
    collection = importer.import_all()

    # Should return empty collection on error
    assert len(collection.items) == 0


@pytest.mark.ai_generated
@responses.activate
def test_dandi_importer_custom_api_url() -> None:
    """Test using a custom API URL."""
    custom_url = "https://custom.dandi.api/api"

    dandisets_response = {
        "count": 1,
        "next": None,
        "results": [
            {
                "identifier": "000001",
                "most_recent_published_version": {"name": "Test", "version": "0.1"},
            }
        ],
    }

    versions_response = {
        "count": 1,
        "next": None,
        "results": [{"version": "0.1", "status": "Valid", "created": "2021-01-01T00:00:00Z"}],
    }

    responses.add(
        responses.GET,
        f"{custom_url}/dandisets/",
        json=dandisets_response,
        status=200,
    )

    responses.add(
        responses.GET,
        f"{custom_url}/dandisets/000001/versions/",
        json=versions_response,
        status=200,
    )

    importer = DANDIImporter(api_url=custom_url)
    collection = importer.import_all()

    assert len(collection.items) == 1


@pytest.mark.ai_generated
@pytest.mark.integration
def test_dandi_importer_real_api() -> None:
    """Integration test with real DANDI API."""
    importer = DANDIImporter()
    collection = importer.import_all(limit=3)

    # Verify we got some dandisets
    assert collection.name == "DANDI Archive"
    assert len(collection.items) > 0
    assert len(collection.items) <= 3

    # Verify structure of first item
    item = collection.items[0]
    assert item.item_id.startswith("dandi:")
    assert item.homepage.startswith("https://dandiarchive.org/dandiset/")
    assert len(item.flavors) > 0

    # Verify DOI format
    for flavor in item.flavors:
        for ref in flavor.refs:
            if ref.ref_type == "doi":
                assert ref.ref_value.startswith("10.48324/dandi.")
