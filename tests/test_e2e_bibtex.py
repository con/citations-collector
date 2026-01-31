"""End-to-end test for BibTeX source workflow."""

from __future__ import annotations

from pathlib import Path

import pytest

from citations_collector.core import CitationCollector
from citations_collector.persistence import yaml_io


@pytest.mark.ai_generated
def test_e2e_bibtex_workflow(tmp_path: Path) -> None:
    """
    End-to-end test: BibTeX file → collection loading → item population.

    This simulates the complete workflow:
    1. User creates BibTeX file with references
    2. User creates collection YAML pointing to BibTeX
    3. System loads collection and populates items
    """
    # Step 1: Create BibTeX file
    bib_file = tmp_path / "references.bib"
    bib_file.write_text("""
@misc{dandi_000003,
    title = {Hippocampal Granule Cells Dataset},
    author = {Senzai, Yuta and Buzsáki, György},
    year = {2021},
    doi = {10.48324/dandi.000003/0.210812.1448},
    publisher = {DANDI Archive}
}

@misc{dandi_000004,
    title = {Human Single-Neuron Activity Dataset},
    author = {Chandravadia, Nand and others},
    year = {2020},
    doi = {10.48324/dandi.000004/0.210831.2033},
    publisher = {DANDI Archive}
}
""")

    # Step 2: Create collection YAML
    collection_yaml = tmp_path / "collection.yaml"
    collection_yaml.write_text("""
name: Test DANDI Collection
description: Testing BibTeX source integration

source:
  type: bibtex
  bibtex_file: references.bib
  bib_field: doi
  ref_type: doi
  ref_regex: '10\\.48324/(?P<item_id>dandi\\.\\d{6})/(?P<flavor_id>[\\d.]+)'

items: []

discover:
  email: test@example.com

output_tsv: citations.tsv
""")

    # Step 3: Load collection
    collection = yaml_io.load_collection(collection_yaml)

    # Verify collection loaded correctly
    assert collection.name == "Test DANDI Collection"
    assert collection.source is not None
    assert collection.source.type == "bibtex"
    assert collection.source.bibtex_file == "references.bib"
    assert len(collection.items) == 0  # No items yet

    # Step 4: Populate from BibTeX source
    collector = CitationCollector(collection, collection_path=collection_yaml)
    collector.populate_from_source()

    # Step 5: Verify items were populated
    assert len(collector.collection.items) == 2

    # Verify first item
    item1 = collector.collection.items[0]
    assert item1.item_id == "dandi.000003"
    assert "Hippocampal" in item1.name
    assert len(item1.flavors) == 1
    assert item1.flavors[0].flavor_id == "0.210812.1448"
    assert item1.flavors[0].refs[0].ref_type == "doi"
    assert item1.flavors[0].refs[0].ref_value == "10.48324/dandi.000003/0.210812.1448"

    # Verify second item
    item2 = collector.collection.items[1]
    assert item2.item_id == "dandi.000004"
    assert item2.flavors[0].flavor_id == "0.210831.2033"


@pytest.mark.ai_generated
def test_e2e_bibtex_relative_path_resolution(tmp_path: Path) -> None:
    """Test that relative BibTeX paths are resolved correctly."""
    # Create subdirectory structure
    config_dir = tmp_path / "configs"
    data_dir = tmp_path / "data"
    config_dir.mkdir()
    data_dir.mkdir()

    # BibTeX in data directory
    bib_file = data_dir / "refs.bib"
    bib_file.write_text("""
@misc{test1,
    doi = {10.48324/dandi.000003/0.210812.1448}
}
""")

    # Collection YAML in config directory, referencing ../data/refs.bib
    collection_yaml = config_dir / "collection.yaml"
    collection_yaml.write_text("""
name: Test Collection
source:
  type: bibtex
  bibtex_file: ../data/refs.bib
  bib_field: doi
  ref_type: doi
  ref_regex: '10\\.48324/(?P<item_id>dandi\\.\\d{6})/(?P<flavor_id>[\\d.]+)'
items: []
""")

    # Load and populate
    collection = yaml_io.load_collection(collection_yaml)
    collector = CitationCollector(collection, collection_path=collection_yaml)
    collector.populate_from_source()

    # Verify item was found via relative path
    assert len(collector.collection.items) == 1
    assert collector.collection.items[0].item_id == "dandi.000003"
