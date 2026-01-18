"""Shared pytest fixtures for citations-collector tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def collections_dir(fixtures_dir: Path) -> Path:
    """Return path to test collection fixtures."""
    return fixtures_dir / "collections"


@pytest.fixture
def tsv_dir(fixtures_dir: Path) -> Path:
    """Return path to test TSV fixtures."""
    return fixtures_dir / "tsv"


@pytest.fixture
def responses_dir(fixtures_dir: Path) -> Path:
    """Return path to mock API response fixtures."""
    return fixtures_dir / "responses"
