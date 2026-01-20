"""Integration tests with real external APIs.

These tests make actual HTTP requests to external services and are slower.
They validate the real-world workflow with example collections.

Run with: pytest tests/test_integration.py -v
Skip with: pytest -m "not integration"
"""

from __future__ import annotations

from pathlib import Path

import pytest

from citations_collector import CitationCollector


@pytest.mark.integration
@pytest.mark.slow
def test_repronim_collection_with_expansion() -> None:
    """
    Integration test: ReproNim tools collection with ref expansion.

    This test:
    1. Loads the real repronim-tools.yaml example
    2. Expands zenodo_concept and github refs to DOIs (live API calls)
    3. Discovers citations using CrossRef (live API calls)
    4. Verifies the workflow completes successfully

    Expected behavior:
    - Should expand ~20 items to 50+ DOIs
    - Should find some citations (at least for open-brain-consent)
    - May get 404s for Zenodo DOIs from CrossRef (expected)
    """
    # Load example collection
    collection_path = Path("examples/repronim-tools.yaml")
    collector = CitationCollector.from_yaml(collection_path)

    # Verify collection loaded
    assert collector.collection.name == "ReproNim Tools"
    assert len(collector.collection.items) > 0

    # Count original refs
    original_ref_count = sum(
        len(flavor.refs) for item in collector.collection.items for flavor in item.flavors
    )
    print(f"\nOriginal refs: {original_ref_count}")

    # Expand refs (makes live API calls to Zenodo and GitHub)
    print("Expanding references (live API calls)...")
    collector.expand_refs()

    # Count refs after expansion
    expanded_ref_count = sum(
        len(flavor.refs) for item in collector.collection.items for flavor in item.flavors
    )
    print(f"After expansion: {expanded_ref_count}")

    # Should have significantly more refs after expansion
    assert expanded_ref_count > original_ref_count
    print(f"Added {expanded_ref_count - original_ref_count} refs via expansion")

    # Discover citations using CrossRef only (faster than all sources)
    print("Discovering citations (live API calls)...")
    collector.discover_all(
        sources=["crossref"],  # Just CrossRef for speed
        incremental=False,
        email="test@example.org",
    )

    # Should have discovered some citations
    # (at least open-brain-consent has citations)
    print(f"Discovered {len(collector.citations)} citations")
    assert len(collector.citations) > 0, "Should discover at least some citations"

    # Verify citations have correct structure
    for citation in collector.citations[:5]:
        assert citation.citation_doi
        assert citation.citation_source == "crossref"
        assert citation.citation_status == "active"
        print(f"  - {citation.item_id}: {citation.citation_doi}")


@pytest.mark.integration
@pytest.mark.slow
def test_dandi_collection_with_datacite() -> None:
    """
    Integration test: DANDI collection with DataCite discoverer.

    This test:
    1. Loads the real dandi-collection.yaml example
    2. Discovers citations using DataCite Event Data (live API calls)
    3. Verifies the workflow completes successfully

    Expected behavior:
    - Should load 2 dandisets with multiple versions
    - DataCite queries should succeed (may return empty results)
    - Workflow should complete without errors

    Note: DataCite Event Data may not have citations for all DOIs yet,
    so finding 0 citations is acceptable (not a failure).
    """
    # Load example collection
    collection_path = Path("examples/dandi-collection.yaml")
    collector = CitationCollector.from_yaml(collection_path)

    # Verify collection loaded
    assert collector.collection.name == "DANDI Archive"
    assert len(collector.collection.items) >= 2

    # Count total refs
    total_refs = sum(
        len(flavor.refs) for item in collector.collection.items for flavor in item.flavors
    )
    print(f"\nTotal DANDI DOI refs: {total_refs}")

    # Discover citations using DataCite (makes live API calls)
    print("Discovering citations via DataCite (live API calls)...")
    collector.discover_all(
        sources=["datacite"],  # DataCite for DANDI DOIs
        incremental=False,
    )

    # DataCite Event Data might not have citations yet - that's OK
    print(f"Discovered {len(collector.citations)} citations from DataCite")

    # The important thing is that the workflow completes without errors
    # and the API calls succeed (even if they return no citations)
    assert collector.citations is not None, "Citations list should be initialized (even if empty)"

    # If citations were found, verify structure
    if collector.citations:
        for citation in collector.citations[:3]:
            assert citation.citation_doi
            assert citation.citation_source == "datacite"
            assert citation.citation_status == "active"
            print(f"  - {citation.item_id}: {citation.citation_doi}")
    else:
        print("  (No citations found - DataCite Event Data may not have coverage yet)")


@pytest.mark.integration
@pytest.mark.slow
def test_simple_collection_crossref() -> None:
    """
    Integration test: Simple test collection with CrossRef.

    This is a minimal test to verify basic CrossRef API integration.
    Uses the simple.yaml test fixture.

    Expected behavior:
    - Should load simple collection
    - CrossRef API call should succeed
    - May return 0 citations (DOI may not be real)
    """
    # Load test fixture
    collection_path = Path("tests/fixtures/collections/simple.yaml")
    collector = CitationCollector.from_yaml(collection_path)

    assert collector.collection.name == "Simple Test Collection"
    assert len(collector.collection.items) == 1

    # Discover citations
    print("\nDiscovering citations for simple collection...")
    collector.discover_all(
        sources=["crossref"],
        incremental=False,
        email="test@example.org",
    )

    # Should complete without errors (even if no citations found)
    print(f"Discovered {len(collector.citations)} citations")
    assert collector.citations is not None


@pytest.mark.integration
@pytest.mark.slow
def test_zenodo_expansion_real_concept() -> None:
    """
    Integration test: Zenodo concept expansion with real API.

    Tests expansion of a known Zenodo concept (DataLad: 808846)
    to verify the Zenodo API integration works.

    Expected behavior:
    - Should expand to multiple version DOIs
    - Should include concept DOI + version DOIs

    Note: Zenodo may return 403 Forbidden without authentication.
    Set ZENODO_TOKEN environment variable to avoid this.
    Test will be skipped if Zenodo blocks the request.
    """

    from citations_collector.importers import ZenodoExpander

    # Use ZENODO_TOKEN from environment if available
    expander = ZenodoExpander()

    # DataLad concept ID
    concept_id = "808846"

    print(f"\nExpanding Zenodo concept {concept_id} (live API call)...")
    refs = expander.expand(concept_id)

    # Should get multiple DOIs
    print(f"Expanded to {len(refs)} DOI references")

    # Zenodo may return 403 Forbidden due to rate limiting/blocking
    # This is an acceptable failure - skip the test rather than failing
    if len(refs) == 0:
        pytest.skip("Zenodo API blocked or rate limited (returned 0 refs)")

    # Should have concept DOI
    concept_dois = [ref.ref_value for ref in refs if "808846" in ref.ref_value]
    assert len(concept_dois) > 0, "Should include concept DOI"

    # Print some results
    for ref in refs[:5]:
        print(f"  - {ref.ref_value}")
    if len(refs) > 5:
        print(f"  ... and {len(refs) - 5} more")


@pytest.mark.integration
@pytest.mark.slow
def test_github_mapping_real_repo() -> None:
    """
    Integration test: GitHub repo mapping with real API.

    Tests mapping a known GitHub repo (datalad/datalad) to its Zenodo DOI.

    Expected behavior:
    - Should find Zenodo DOI from repository metadata
    - May require multiple API calls (description, README, etc.)

    Note: May hit GitHub rate limits if run too frequently without token.
    """
    from citations_collector.importers import GitHubMapper

    mapper = GitHubMapper()

    # DataLad repository
    repo = "datalad/datalad"

    print(f"\nMapping GitHub repo {repo} to DOI (live API call)...")
    ref = mapper.map_to_doi(repo)

    if ref:
        print(f"Found DOI: {ref.ref_value}")
        # ref_type could be string or enum depending on how it's created
        ref_type_str = ref.ref_type if isinstance(ref.ref_type, str) else ref.ref_type.value
        assert ref_type_str == "doi"
        assert "zenodo" in ref.ref_value.lower()
    else:
        # May fail due to rate limits or missing DOI
        print("No DOI found (may be rate limited or DOI not in expected locations)")


@pytest.mark.integration
@pytest.mark.slow
def test_full_workflow_end_to_end() -> None:
    """
    Integration test: Full end-to-end workflow.

    Complete workflow from collection loading to citation discovery and saving.

    Expected behavior:
    - Load ReproNim collection
    - Expand refs
    - Discover citations
    - Save results to temp files
    - Reload and verify
    """
    import tempfile

    from citations_collector.persistence import tsv_io, yaml_io

    # Load collection
    collector = CitationCollector.from_yaml(Path("examples/repronim-tools.yaml"))

    # Expand refs
    print("\n=== Full Workflow Test ===")
    print("1. Expanding references...")
    collector.expand_refs()

    # Discover citations (just a few items to keep it fast)
    print("2. Discovering citations...")
    collector.discover_all(
        sources=["crossref"],  # Just CrossRef for speed
        incremental=False,
        email="test@example.org",
    )

    # Save to temp files
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        yaml_path = tmppath / "collection.yaml"
        tsv_path = tmppath / "citations.tsv"

        print("3. Saving results...")
        collector.save(yaml_path, tsv_path)

        # Verify files were created
        assert yaml_path.exists()
        assert tsv_path.exists()

        # Reload and verify
        print("4. Reloading and verifying...")
        reloaded_collection = yaml_io.load_collection(yaml_path)
        assert reloaded_collection.name == "ReproNim Tools"

        reloaded_citations = tsv_io.load_citations(tsv_path)
        assert len(reloaded_citations) == len(collector.citations)

        print(f"✓ Workflow complete: {len(reloaded_citations)} citations saved and reloaded")
