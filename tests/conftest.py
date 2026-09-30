"""Shared pytest fixtures for citations-collector tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from urllib3.util.retry import Retry


@pytest.fixture(autouse=True)
def _no_retry_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip urllib3 retry backoff sleeps so mocked 429/5xx responses are fast."""
    monkeypatch.setattr(Retry, "sleep", lambda self, response=None: None)


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
