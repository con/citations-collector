"""Click-based CLI for citations-collector."""

from __future__ import annotations

import logging
from datetime import datetime
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
    help="Output TSV file (overrides collection YAML output_tsv)",
)
@click.option(
    "--full-refresh",
    is_flag=True,
    help="Ignore incremental mode (discover all citations)",
)
@click.option(
    "--since",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Only discover citations since this date (YYYY-MM-DD). Overrides incremental mode.",
)
@click.option(
    "--email",
    envvar="CROSSREF_EMAIL",
    help="Email for CrossRef polite pool (overrides discover.email in YAML)",
)
@click.option(
    "--sources",
    multiple=True,
    type=click.Choice(["crossref", "opencitations", "datacite", "openalex"]),
    help="Which sources to query (overrides discover.sources in YAML)",
)
@click.option(
    "--expand-refs",
    is_flag=True,
    help="Expand non-DOI refs (zenodo_concept, github) to DOIs before discovery",
)
def discover(
    collection: Path,
    output: Path | None,
    full_refresh: bool,
    since: datetime | None,
    email: str | None,
    sources: tuple[str, ...],
    expand_refs: bool,
) -> None:
    """Discover citations for all items in COLLECTION."""
    click.echo(f"Loading collection from {collection}")

    # Load collection
    collector = CitationCollector.from_yaml(collection)
    cfg = collector.collection

    # Populate items dynamically from source config (e.g., DANDI API)
    if cfg.source and cfg.source.type:
        click.echo(f"Populating items from {cfg.source.type} source...")
        collector.populate_from_source()

    # Resolve config: CLI overrides > YAML config > defaults
    discover_cfg = cfg.discover
    if not output:
        output = Path(cfg.output_tsv) if cfg.output_tsv else Path("citations.tsv")
    if not email and discover_cfg:
        email = discover_cfg.email
    if not sources and discover_cfg and discover_cfg.sources:
        sources = tuple(discover_cfg.sources)

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
    click.echo(f"Discovering citations for {cfg.name}...")
    if email:
        click.echo(f"Using CrossRef polite pool with email: {email}")

    sources_list = list(sources) if sources else None
    collector.discover_all(
        sources=sources_list,
        incremental=not full_refresh,
        since_date=since,
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
    help="Limit number of dandisets to import (only for --all)",
)
@click.option(
    "--dandiset-id",
    "-d",
    "dandiset_ids",
    multiple=True,
    help="Import specific dandiset(s) by ID (e.g., -d 000402 -d 000003)",
)
@click.option(
    "--all",
    "import_all",
    is_flag=True,
    help="Import all dandisets (default if no --dandiset-id specified)",
)
def import_dandi(
    output: Path,
    include_draft: bool,
    limit: int | None,
    dandiset_ids: tuple[str, ...],
    import_all: bool,
) -> None:
    """Import dandisets from DANDI Archive.

    Examples:

      # Import specific dandisets
      citations-collector import-dandi -o microns.yaml -d 000402

      # Import multiple specific dandisets
      citations-collector import-dandi -o multi.yaml -d 000003 -d 000402

      # Import all dandisets (with limit)
      citations-collector import-dandi -o all.yaml --all --limit 10
    """
    importer = DANDIImporter()

    # Determine what to import
    if dandiset_ids:
        # Import specific dandisets
        click.echo(f"Importing {len(dandiset_ids)} specific dandiset(s)...")

        with click.progressbar(length=len(dandiset_ids), label="Importing") as bar:  # type: ignore[var-annotated]

            def progress(current: int, total: int | None) -> None:
                bar.update(1)

            collection = importer.import_specific(
                dandiset_ids=list(dandiset_ids),
                include_draft=include_draft,
                progress_callback=progress,
            )
    else:
        # Import all dandisets
        if not import_all:
            click.echo(
                "No --dandiset-id specified, importing all dandisets "
                "(use --all to suppress this message)"
            )
        else:
            click.echo("Importing all dandisets from DANDI Archive...")

        with click.progressbar(length=limit or 0, label="Importing") as bar:  # type: ignore[var-annotated]

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
    "--tsv",
    type=click.Path(exists=True, path_type=Path),
    help="Citations TSV file (overrides collection YAML output_tsv)",
)
@click.option(
    "--api-key",
    envvar="ZOTERO_API_KEY",
    help="Zotero API key",
)
@click.option(
    "--group-id",
    type=int,
    help="Zotero group ID (overrides zotero.group_id in YAML)",
)
@click.option(
    "--collection-key",
    help="Zotero collection key (overrides zotero.collection_key in YAML)",
)
@click.option("--dry-run", is_flag=True, help="Show what would be synced without writing")
def sync_zotero(
    collection: Path,
    tsv: Path | None,
    api_key: str | None,
    group_id: int | None,
    collection_key: str | None,
    dry_run: bool,
) -> None:
    """Sync citations to Zotero as hierarchical collections."""
    from citations_collector.persistence import tsv_io
    from citations_collector.zotero_sync import ZoteroSyncer

    collector = CitationCollector.from_yaml(collection)
    cfg = collector.collection
    zotero_cfg = cfg.zotero

    # Resolve config
    if not tsv:
        tsv_path = Path(cfg.output_tsv) if cfg.output_tsv else Path("citations.tsv")
    else:
        tsv_path = tsv
    if not group_id and zotero_cfg:
        group_id = zotero_cfg.group_id
    if not collection_key and zotero_cfg:
        collection_key = zotero_cfg.collection_key
    if not api_key:
        raise click.UsageError("Zotero API key required (--api-key or ZOTERO_API_KEY)")
    if not group_id:
        raise click.UsageError("Zotero group ID required (--group-id or zotero.group_id in YAML)")
    if not collection_key:
        raise click.UsageError(
            "Zotero collection key required (--collection-key or zotero.collection_key in YAML)"
        )

    citations = tsv_io.load_citations(tsv_path)
    click.echo(f"Loaded {len(citations)} citations from {tsv_path}")

    syncer = ZoteroSyncer(api_key=api_key, group_id=group_id, collection_key=collection_key)
    report = syncer.sync(cfg, citations, dry_run=dry_run)

    prefix = "[DRY RUN] " if dry_run else ""
    click.echo(f"{prefix}Collections created: {report.collections_created}")
    click.echo(f"{prefix}Items created: {report.items_created}")
    click.echo(f"{prefix}Items skipped: {report.items_skipped}")
    click.echo(f"{prefix}Attachments created: {report.attachments_created}")
    if report.errors:
        click.echo(f"Errors: {len(report.errors)}")
        for err in report.errors[:10]:
            click.echo(f"  {err}")


@main.command("fetch-pdfs")
@click.argument("collection", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--tsv",
    type=click.Path(path_type=Path),
    help="Citations TSV file (overrides collection YAML output_tsv)",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    help="PDF output directory (overrides pdfs.output_dir in YAML)",
)
@click.option(
    "--email",
    envvar="UNPAYWALL_EMAIL",
    help="Email for Unpaywall API (overrides pdfs.unpaywall_email in YAML)",
)
@click.option("--git-annex/--no-git-annex", default=None, help="Use git-annex for PDFs")
@click.option("--dry-run", is_flag=True, help="Report OA status without downloading")
def fetch_pdfs(
    collection: Path,
    tsv: Path | None,
    output_dir: Path | None,
    email: str | None,
    git_annex: bool | None,
    dry_run: bool,
) -> None:
    """Fetch open-access PDFs for citations in COLLECTION."""
    from citations_collector.pdf import PDFAcquirer
    from citations_collector.persistence import tsv_io

    collector = CitationCollector.from_yaml(collection)
    cfg = collector.collection
    pdfs_cfg = cfg.pdfs

    # Resolve config
    if not tsv:
        tsv_path = Path(cfg.output_tsv) if cfg.output_tsv else Path("citations.tsv")
    else:
        tsv_path = tsv
    if not output_dir:
        output_dir = Path((pdfs_cfg.output_dir if pdfs_cfg else None) or "pdfs/")

    # Resolve with fallbacks (ensure non-None types for PDFAcquirer)
    email_resolved: str = (
        email
        or (pdfs_cfg.unpaywall_email if pdfs_cfg else None)
        or "site-unpaywall@oneukrainian.com"
    )
    git_annex_resolved: bool = (
        git_annex
        if git_annex is not None
        else ((pdfs_cfg.git_annex if pdfs_cfg else None) or False)
    )

    citations = tsv_io.load_citations(tsv_path)
    click.echo(f"Loaded {len(citations)} citations from {tsv_path}")

    acquirer = PDFAcquirer(
        output_dir=output_dir, email=email_resolved, git_annex=git_annex_resolved
    )
    counts = acquirer.acquire_all(citations, dry_run=dry_run)

    prefix = "[DRY RUN] " if dry_run else ""
    click.echo(f"{prefix}Downloaded: {counts['downloaded']}")
    click.echo(f"{prefix}Skipped (existing): {counts['skipped']}")
    click.echo(f"{prefix}No OA available: {counts['no_oa']}")
    click.echo(f"{prefix}No DOI: {counts['no_doi']}")
    if counts["error"]:
        click.echo(f"Errors: {counts['error']}")

    if not dry_run:
        tsv_io.save_citations(citations, tsv_path)
        click.echo(f"Updated {tsv_path}")


@main.command(name="detect-merges")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to collection YAML config",
)
@click.option(
    "--tsv",
    type=click.Path(exists=True, path_type=Path),
    help="Override: path to TSV file (default: from config)",
)
@click.option(
    "--email",
    help="Email for CrossRef API (default: from config or fallback)",
)
@click.option(
    "--fuzzy-match",
    is_flag=True,
    help="Also perform fuzzy title matching (heuristic, use with caution)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be marked without saving",
)
def detect_merges(
    config: Path | None,
    tsv: Path | None,
    email: str | None,
    fuzzy_match: bool,
    dry_run: bool,
) -> None:
    """Detect and mark preprints that have published versions.

    Uses CrossRef API to find "is-preprint-of" relationships and marks
    preprints as merged with citation_status=merged.
    """
    from citations_collector.core import CitationCollector
    from citations_collector.merge_detection import MergeDetector
    from citations_collector.persistence import tsv_io

    # Load config if provided
    pdfs_cfg = None
    if config:
        collector = CitationCollector.from_yaml(config)
        cfg = collector.collection
        pdfs_cfg = cfg.pdfs
        if not tsv:
            tsv_path = Path(cfg.output_tsv) if cfg.output_tsv else Path("citations.tsv")
        else:
            tsv_path = tsv
    elif tsv:
        tsv_path = tsv
    else:
        raise click.UsageError("Must provide either --config or --tsv")

    # Resolve email
    email_resolved: str = (
        email
        or (pdfs_cfg.unpaywall_email if pdfs_cfg else None)
        or "site-unpaywall@oneukrainian.com"
    )

    citations = tsv_io.load_citations(tsv_path)
    click.echo(f"Loaded {len(citations)} citations from {tsv_path}")

    detector = MergeDetector(email=email_resolved)

    # Detect merges via CrossRef relationships
    merged_pairs = detector.detect_merged_pairs(citations)
    click.echo(f"Found {len(merged_pairs)} merged pairs via CrossRef API")

    # Optionally add fuzzy matching
    if fuzzy_match:
        click.echo("Running fuzzy title matching...")
        fuzzy_pairs = detector.fuzzy_match_by_title(citations)
        click.echo(f"Found {len(fuzzy_pairs)} potential pairs via fuzzy matching")

        # Show fuzzy matches for manual review
        if fuzzy_pairs:
            click.echo("\nFuzzy matches (review before accepting):")
            for preprint_doi, pub_doi in fuzzy_pairs.items():
                click.echo(f"  {preprint_doi} -> {pub_doi}")

        # Don't auto-merge fuzzy matches - require manual review
        click.echo(
            "\nFuzzy matches not applied automatically. "
            "Review and add to CrossRef metadata if valid."
        )

    # Mark merged citations
    if merged_pairs:
        prefix = "[DRY RUN] " if dry_run else ""
        marked = detector.mark_merged_citations(citations, merged_pairs)
        click.echo(f"{prefix}Marked {marked} citations as merged")

        if not dry_run:
            tsv_io.save_citations(citations, tsv_path)
            click.echo(f"Updated {tsv_path}")
    else:
        click.echo("No merges detected")


if __name__ == "__main__":
    main()
