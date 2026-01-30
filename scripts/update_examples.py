#!/usr/bin/env python
"""Update all example collections with latest citations.

This script:
1. Finds all .yaml collection files in examples/
2. Runs citation discovery for each
3. Preserves manually curated citations
4. Outputs updated TSV files
5. Provides a summary report
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import click

from citations_collector.core import CitationCollector
from citations_collector.persistence import yaml_io

# Color formatting for terminal output
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def update_collection(yaml_path: Path) -> dict[str, Any]:
    """
    Update citations for a single collection.

    Args:
        yaml_path: Path to collection YAML file

    Returns:
        Dictionary with update statistics
    """
    stats = {
        "name": yaml_path.stem,
        "yaml_path": str(yaml_path),
        "status": "success",
        "error": None,
        "new_citations": 0,
        "total_citations": 0,
        "items_count": 0,
    }

    try:
        # Load collection
        collection = yaml_io.load_collection(yaml_path)
        stats["items_count"] = len(collection.items) if collection.items else 0

        # Determine TSV output path from collection config
        tsv_path = yaml_path.parent / (collection.output_tsv or f"{yaml_path.stem}-citations.tsv")

        # Create collector and load existing citations
        collector = CitationCollector(collection)

        # Load existing citations if TSV exists
        if tsv_path.exists():
            click.echo(f"  Loading existing citations from {tsv_path.name}")
            collector.load_existing_citations(tsv_path)
            existing_count = len(collector.citations)
        else:
            existing_count = 0

        # Populate items from source if configured (e.g., DANDI API)
        if collection.source and collection.source.type:
            click.echo(f"  Populating items from {collection.source.type} source...")
            collector.populate_from_source()

        # Discover citations
        sources = (
            collection.discover.sources
            if collection.discover and collection.discover.sources
            else None
        )
        email = (
            collection.discover.email if collection.discover and collection.discover.email else None
        )

        click.echo(f"  Discovering citations from {sources or 'default sources'}...")
        collector.discover_all(sources=sources, email=email, incremental=True)

        # Calculate new citations
        stats["new_citations"] = len(collector.citations) - existing_count
        stats["total_citations"] = len(collector.citations)

        # Save updated collection and citations
        collector.save(yaml_path, tsv_path)

        click.echo(
            f"  {GREEN}✓{RESET} Saved {stats['total_citations']} citations to {tsv_path.name}"
        )

    except Exception as e:
        stats["status"] = "error"
        stats["error"] = str(e)
        click.echo(f"  {YELLOW}✗{RESET} Error: {e}", err=True)

    return stats


@click.command()
@click.option(
    "--examples-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default="examples",
    help="Directory containing example collection YAML files",
)
def main(examples_dir: Path) -> None:
    """Update all example collections with latest citations."""
    click.echo(f"\n{BOLD}Updating Example Citations{RESET}\n")

    # Find all YAML files in examples directory
    all_yaml_files = sorted(examples_dir.glob("*.yaml"))

    # Filter to only valid collection files
    yaml_files = []
    for yaml_path in all_yaml_files:
        try:
            yaml_io.load_collection(yaml_path)
            yaml_files.append(yaml_path)
        except Exception:
            # Skip files that aren't valid collections (e.g., GitHub workflows)
            click.echo(f"  Skipping non-collection file: {yaml_path.name}")

    if not yaml_files:
        click.echo(f"{YELLOW}No valid collection YAML files found in {examples_dir}{RESET}")
        sys.exit(1)

    click.echo(f"\nFound {len(yaml_files)} collection(s) to update\n")

    # Update each collection
    all_stats = []
    for yaml_path in yaml_files:
        click.echo(f"{BOLD}{BLUE}Processing:{RESET} {yaml_path.name}")
        stats = update_collection(yaml_path)
        all_stats.append(stats)
        click.echo()

    # Print summary
    click.echo(f"\n{BOLD}{'=' * 60}{RESET}")
    click.echo(f"{BOLD}Summary{RESET}\n")

    total_new = 0
    total_citations = 0
    success_count = 0
    error_count = 0

    for stats in all_stats:
        status_icon = f"{GREEN}✓{RESET}" if stats["status"] == "success" else f"{YELLOW}✗{RESET}"
        click.echo(
            f"  {status_icon} {stats['name']}: "
            f"{stats['new_citations']:+d} new, "
            f"{stats['total_citations']} total"
        )

        if stats["status"] == "success":
            success_count += 1
            total_new += stats["new_citations"]
            total_citations += stats["total_citations"]
        else:
            error_count += 1

    click.echo(f"\n{BOLD}Overall:{RESET}")
    click.echo(f"  Collections updated: {success_count}/{len(all_stats)}")
    click.echo(f"  New citations: {total_new:+d}")
    click.echo(f"  Total citations: {total_citations}")

    if error_count > 0:
        click.echo(f"\n{YELLOW}Errors occurred in {error_count} collection(s){RESET}")
        sys.exit(1)

    click.echo(f"\n{GREEN}All collections updated successfully!{RESET}\n")


if __name__ == "__main__":
    main()
