"""Tests for BibTeX importer."""

from __future__ import annotations

from pathlib import Path

import pytest

from citations_collector.importers.bibtex import BibTeXImporter
from citations_collector.models.generated import RefType


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures" / "bibtex"


@pytest.fixture
def simple_bib(tmp_path: Path) -> Path:
    """Create simple BibTeX file for testing."""
    bib_content = """
@article{test1,
    title = {Test Article One},
    author = {Smith, John and Jones, Alice},
    year = {2023},
    doi = {10.48324/dandi.000003/0.230629.1955},
    journal = {Test Journal}
}

@article{test2,
    title = {Test Article Two},
    author = {Brown, Bob},
    year = {2024},
    doi = {10.48324/dandi.000005/0.240101.1234},
    journal = {Another Journal}
}
"""
    bib_file = tmp_path / "simple.bib"
    bib_file.write_text(bib_content)
    return bib_file


@pytest.mark.ai_generated
def test_bibtex_basic_import(simple_bib: Path) -> None:
    """Test basic BibTeX import with DANDI DOI pattern."""
    importer = BibTeXImporter(
        bibtex_file=simple_bib,
        bib_field="doi",
        ref_type=RefType.doi,
        ref_regex=r"10\.48324/(?P<item_id>dandi\.\d{6})/(?P<flavor_id>[\d.]+)",
    )

    collection = importer.import_all()

    assert collection.name == "BibTeX: simple"
    assert len(collection.items) == 2

    # Check first item
    item1 = collection.items[0]
    assert item1.item_id == "dandi.000003"
    assert item1.name == "Test Article One"
    assert len(item1.flavors) == 1

    flavor1 = item1.flavors[0]
    assert flavor1.flavor_id == "0.230629.1955"
    assert len(flavor1.refs) == 1
    assert flavor1.refs[0].ref_type == RefType.doi
    assert flavor1.refs[0].ref_value == "10.48324/dandi.000003/0.230629.1955"


@pytest.mark.ai_generated
def test_bibtex_missing_field(simple_bib: Path) -> None:
    """Test BibTeX import when bib_field is missing."""
    importer = BibTeXImporter(
        bibtex_file=simple_bib,
        bib_field="url",  # Field doesn't exist in fixture
        ref_type=RefType.url,
        ref_regex=r"example\.com/(?P<item_id>[^/]+)",
    )

    collection = importer.import_all()
    assert len(collection.items) == 0  # All entries skipped


@pytest.mark.ai_generated
def test_bibtex_no_flavor_in_regex(simple_bib: Path) -> None:
    """Test regex without flavor_id group - should use 'main'."""
    importer = BibTeXImporter(
        bibtex_file=simple_bib,
        bib_field="doi",
        ref_type=RefType.doi,
        ref_regex=r"10\.48324/(?P<item_id>dandi\.\d{6})/[\d.]+",  # No flavor group
    )

    collection = importer.import_all()
    assert len(collection.items) == 2
    assert all(item.flavors[0].flavor_id == "main" for item in collection.items)


@pytest.mark.ai_generated
def test_bibtex_invalid_regex() -> None:
    """Test that missing item_id group raises ValueError."""
    with pytest.raises(ValueError, match="must contain.*item_id"):
        BibTeXImporter(
            bibtex_file=Path("dummy.bib"),
            bib_field="doi",
            ref_type=RefType.doi,
            ref_regex=r"10\.\d+/.*",  # No named groups
        )


@pytest.mark.ai_generated
def test_bibtex_file_not_found() -> None:
    """Test FileNotFoundError for missing BibTeX file."""
    importer = BibTeXImporter(
        bibtex_file=Path("/nonexistent/file.bib"),
        bib_field="doi",
        ref_type=RefType.doi,
        ref_regex=r"(?P<item_id>.*)",
    )

    with pytest.raises(FileNotFoundError):
        importer.import_all()


@pytest.mark.ai_generated
def test_bibtex_real_dandi_fixture(fixtures_dir: Path) -> None:
    """Test with real DANDI BibTeX fixture."""
    dandi_bib = fixtures_dir / "dandi.bib"

    importer = BibTeXImporter(
        bibtex_file=dandi_bib,
        bib_field="doi",
        ref_type=RefType.doi,
        ref_regex=r"10\.48324/(?P<item_id>dandi\.\d{6})/(?P<flavor_id>[\d.]+)",
    )

    collection = importer.import_all()

    assert len(collection.items) == 2

    # Check first dandiset
    item1 = collection.items[0]
    assert item1.item_id == "dandi.000003"
    assert "Hippocampal" in item1.name
    assert item1.flavors[0].flavor_id == "0.210812.1448"

    # Check second dandiset
    item2 = collection.items[1]
    assert item2.item_id == "dandi.000004"
    assert item2.flavors[0].flavor_id == "0.210831.2033"


@pytest.mark.ai_generated
def test_bibtex_year_parsing(tmp_path: Path) -> None:
    """Test year parsing converts to release_date."""
    bib_content = """
@article{test1,
    title = {Test Article},
    year = {2023},
    doi = {10.48324/dandi.000003/0.230629.1955}
}
"""
    bib_file = tmp_path / "year_test.bib"
    bib_file.write_text(bib_content)

    importer = BibTeXImporter(
        bibtex_file=bib_file,
        bib_field="doi",
        ref_type=RefType.doi,
        ref_regex=r"10\.48324/(?P<item_id>dandi\.\d{6})/(?P<flavor_id>[\d.]+)",
    )

    collection = importer.import_all()

    assert len(collection.items) == 1
    flavor = collection.items[0].flavors[0]
    assert flavor.release_date is not None
    assert flavor.release_date.year == 2023
    assert flavor.release_date.month == 1
    assert flavor.release_date.day == 1


@pytest.mark.ai_generated
def test_bibtex_regex_no_match(tmp_path: Path) -> None:
    """Test entries that don't match regex are skipped."""
    bib_content = """
@article{test1,
    title = {Test Article},
    doi = {10.1234/wrong-format}
}
"""
    bib_file = tmp_path / "no_match.bib"
    bib_file.write_text(bib_content)

    importer = BibTeXImporter(
        bibtex_file=bib_file,
        bib_field="doi",
        ref_type=RefType.doi,
        ref_regex=r"10\.48324/(?P<item_id>dandi\.\d{6})/(?P<flavor_id>[\d.]+)",
    )

    collection = importer.import_all()
    assert len(collection.items) == 0


@pytest.mark.ai_generated
def test_bibtex_empty_file(tmp_path: Path) -> None:
    """Test empty BibTeX file."""
    bib_file = tmp_path / "empty.bib"
    bib_file.write_text("")

    importer = BibTeXImporter(
        bibtex_file=bib_file,
        bib_field="doi",
        ref_type=RefType.doi,
        ref_regex=r"(?P<item_id>.*)",
    )

    collection = importer.import_all()
    assert len(collection.items) == 0
