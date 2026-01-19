"""Click-based CLI for citations-collector."""

from __future__ import annotations

import logging
from pathlib import Path

import click

from citations_collector.core import CitationCollector

logger = logging.getLogger(__name__)


@click.group()
@click.version_option()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def main(verbose: bool) -> None:
    """Discover and curate scholarly citations of datasets and software."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )


@main.command()
@click.argument("collection", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default="citations.tsv",
    help="Output TSV file for citations",
)
@click.option(
    "--full-refresh",
    is_flag=True,
    help="Ignore incremental mode (discover all citations)",
)
@click.option(
    "--email",
    envvar="CROSSREF_EMAIL",
    help="Email for CrossRef polite pool (better rate limits)",
)
@click.option(
    "--sources",
    multiple=True,
    type=click.Choice(["crossref", "opencitations", "datacite"]),
    help="Which sources to query (default: crossref+opencitations)",
)
def discover(
    collection: Path,
    output: Path,
    full_refresh: bool,
    email: str | None,
    sources: tuple[str, ...],
) -> None:
    """Discover citations for all items in COLLECTION."""
    click.echo(f"Loading collection from {collection}")

    # Load collection
    collector = CitationCollector.from_yaml(collection)

    # Load existing citations if TSV exists
    if output.exists():
        click.echo(f"Loading existing citations from {output}")
        collector.load_existing_citations(output)
        existing_count = len(collector.citations)
    else:
        existing_count = 0

    # Discover citations
    click.echo(f"Discovering citations for {collector.collection.name}...")
    if email:
        click.echo(f"Using CrossRef polite pool with email: {email}")

    sources_list = list(sources) if sources else None
    collector.discover_all(
        sources=sources_list,
        incremental=not full_refresh,
        email=email,
    )

    # Report results
    new_count = len(collector.citations) - existing_count
    click.echo(f"Found {new_count} new citations ({len(collector.citations)} total)")

    # Save results
    collector.save(collection, output)
    click.echo(f"Saved to {output}")


@main.command("sync-zotero")
@click.argument("collection", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--api-key",
    envvar="ZOTERO_API_KEY",
    required=True,
    help="Zotero API key",
)
@click.option(
    "--group-id",
    type=int,
    help="Zotero group ID",
)
def sync_zotero(collection: Path, api_key: str, group_id: int | None) -> None:
    """Sync citations to Zotero (not yet implemented)."""
    click.echo("Zotero sync not yet implemented (Phase 6 feature)")
    click.echo(f"Collection: {collection}")
    click.echo(f"Group ID: {group_id}")


if __name__ == "__main__":
    main()
