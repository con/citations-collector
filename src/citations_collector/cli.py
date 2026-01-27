"""Click-based CLI for citations-collector."""

from __future__ import annotations

import logging
from pathlib import Path

import click

from citations_collector.core import CitationCollector
from citations_collector.importers.dandi import DANDIImporter
from citations_collector.importers.zotero import ZoteroImporter
from citations_collector.persistence import yaml_io

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
    help="Which sources to query (default: all available)",
)
@click.option(
    "--expand-refs",
    is_flag=True,
    help="Expand non-DOI refs (zenodo_concept, github) to DOIs before discovery",
)
def discover(
    collection: Path,
    output: Path,
    full_refresh: bool,
    email: str | None,
    sources: tuple[str, ...],
    expand_refs: bool,
) -> None:
    """Discover citations for all items in COLLECTION."""
    click.echo(f"Loading collection from {collection}")

    # Load collection
    collector = CitationCollector.from_yaml(collection)

    # Expand non-DOI refs if requested
    if expand_refs:
        click.echo("Expanding non-DOI references (zenodo_concept, github) to DOIs...")
        collector.expand_refs()

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


@main.command("import-dandi")
@click.option(
    "--output",
    "-o",
    required=True,
    type=click.Path(path_type=Path),
    help="Output YAML file for collection",
)
@click.option(
    "--include-draft",
    is_flag=True,
    help="Include draft versions (no DOI)",
)
@click.option(
    "--limit",
    type=int,
    help="Limit number of dandisets to import",
)
def import_dandi(output: Path, include_draft: bool, limit: int | None) -> None:
    """Import all dandisets from DANDI Archive."""
    click.echo("Importing dandisets from DANDI Archive...")

    importer = DANDIImporter()

    with click.progressbar(length=limit or 0, label="Importing") as bar:

        def progress(current: int, total: int | None) -> None:
            bar.update(1)

        collection = importer.import_all(
            include_draft=include_draft,
            limit=limit,
            progress_callback=progress if limit else None,
        )

    yaml_io.save_collection(collection, output)
    click.echo(f"Imported {len(collection.items or [])} dandisets to {output}")


@main.command("import-zotero")
@click.option(
    "--output",
    "-o",
    required=True,
    type=click.Path(path_type=Path),
    help="Output YAML file for collection",
)
@click.option(
    "--group-id",
    required=True,
    type=int,
    help="Zotero group ID",
)
@click.option(
    "--collection-key",
    help="Specific collection within group",
)
@click.option(
    "--api-key",
    envvar="ZOTERO_API_KEY",
    help="Zotero API key (optional for public groups)",
)
@click.option(
    "--limit",
    type=int,
    help="Limit number of items to import",
)
def import_zotero(
    output: Path,
    group_id: int,
    collection_key: str | None,
    api_key: str | None,
    limit: int | None,
) -> None:
    """Import items from a Zotero group."""
    click.echo(f"Importing items from Zotero group {group_id}...")

    importer = ZoteroImporter(api_key=api_key)
    collection = importer.import_group(
        group_id=group_id,
        collection_key=collection_key,
        limit=limit,
    )

    yaml_io.save_collection(collection, output)
    click.echo(f"Imported {len(collection.items or [])} items to {output}")


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
