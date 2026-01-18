"""Tests for CLI commands."""

from __future__ import annotations

from pathlib import Path

import pytest
import responses
from click.testing import CliRunner

from citations_collector.cli import main


@pytest.mark.ai_generated
@responses.activate
def test_discover_command(collections_dir: Path, tmp_path: Path) -> None:
    """Test discover command."""
    # Mock CrossRef API
    responses.add(
        responses.GET,
        "https://api.crossref.org/works/10.1234/test.dataset",
        json={"message": {"reference": []}},
        status=200,
    )

    runner = CliRunner()
    output_file = tmp_path / "test.tsv"

    result = runner.invoke(
        main,
        [
            "discover",
            str(collections_dir / "simple.yaml"),
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 0
    assert "Discovering citations" in result.output
    assert output_file.exists()


@pytest.mark.ai_generated
@responses.activate
def test_discover_full_refresh_flag(collections_dir: Path, tmp_path: Path) -> None:
    """Test discover with --full-refresh flag."""
    # Mock CrossRef API
    responses.add(
        responses.GET,
        "https://api.crossref.org/works/10.1234/test.dataset",
        json={"message": {"reference": []}},
        status=200,
    )

    runner = CliRunner()
    output_file = tmp_path / "test.tsv"

    result = runner.invoke(
        main,
        [
            "discover",
            str(collections_dir / "simple.yaml"),
            "--output",
            str(output_file),
            "--full-refresh",
        ],
    )

    assert result.exit_code == 0
    assert "Discovering citations" in result.output


@pytest.mark.ai_generated
def test_discover_email_env_var(collections_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test discover respects CROSSREF_EMAIL environment variable."""
    monkeypatch.setenv("CROSSREF_EMAIL", "test@example.org")

    runner = CliRunner()
    output_file = tmp_path / "test.tsv"

    # Mock to avoid actual API call
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            "https://api.crossref.org/works/10.1234/test.dataset",
            json={"message": {"reference": []}},
            status=200,
        )

        result = runner.invoke(
            main,
            [
                "discover",
                str(collections_dir / "simple.yaml"),
                "--output",
                str(output_file),
            ],
        )

    assert result.exit_code == 0
    assert "polite pool" in result.output


@pytest.mark.ai_generated
def test_sync_zotero_placeholder(collections_dir: Path) -> None:
    """Test sync-zotero command placeholder."""
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "sync-zotero",
            str(collections_dir / "simple.yaml"),
            "--api-key",
            "test-key",
        ],
    )

    assert result.exit_code == 0
    assert "not yet implemented" in result.output
