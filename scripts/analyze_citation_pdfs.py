#!/usr/bin/env python3
"""Analyze collected PDFs/HTMLs to understand citation relationship patterns.

This script helps identify how papers cite DANDI datasets by extracting
context around DANDI mentions from collected papers.

Usage:
    python scripts/analyze_citation_pdfs.py /path/to/pdfs/
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import click


def extract_dandi_mentions_pdf(pdf_path: Path) -> list[str]:
    """Extract text snippets mentioning DANDI from PDF.

    Requires: pdfplumber or PyPDF2
    Returns list of context strings around DANDI mentions.
    """
    try:
        import pdfplumber
    except ImportError:
        click.echo("Install pdfplumber: pip install pdfplumber", err=True)
        return []

    mentions = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if not text:
                continue

            # Find sentences containing DANDI
            sentences = re.split(r"[.!?]\s+", text)
            for sentence in sentences:
                if re.search(r"DANDI|48324/dandi", sentence, re.IGNORECASE):
                    # Clean up whitespace
                    clean = " ".join(sentence.split())
                    mentions.append(f"[Page {page_num}] {clean}")

    return mentions


def extract_dandi_mentions_html(html_path: Path) -> list[str]:
    """Extract text snippets mentioning DANDI from HTML.

    Returns list of context strings around DANDI mentions.
    """
    from html.parser import HTMLParser

    class TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.text_chunks = []
            self.current_text = []

        def handle_data(self, data):
            self.current_text.append(data)

        def get_text(self):
            return " ".join(self.current_text)

    try:
        content = html_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = html_path.read_text(encoding="latin-1")

    parser = TextExtractor()
    parser.feed(content)
    text = parser.get_text()

    # Find sentences containing DANDI
    mentions = []
    sentences = re.split(r"[.!?]\s+", text)
    for sentence in sentences:
        if re.search(r"DANDI|48324/dandi", sentence, re.IGNORECASE):
            clean = " ".join(sentence.split())
            if len(clean) > 50:  # Filter very short fragments
                mentions.append(clean)

    return mentions


def classify_relationship_from_text(text: str) -> list[str]:
    """Suggest relationship types based on textual patterns."""
    text_lower = text.lower()
    suggestions = []

    # Data descriptor language
    if re.search(r"dataset (is )?(available|deposited|published|released)", text_lower):
        suggestions.append("IsDocumentedBy")

    # Active data use
    use_pattern = r"(we |authors )?(used|analyzed|examined|studied|processed|downloaded)"
    if re.search(use_pattern + r" (the )?(data|dataset)", text_lower):
        suggestions.append("Uses/UsesDataFrom")

    # Validation/evidence
    if re.search(r"validat(e|ed|ion)|benchmark(ed|ing)|test(ed|ing)|evaluat(e|ed|ion)", text_lower):
        suggestions.append("CitesAsEvidence")

    # Multiple datasets
    if text.count("dandi") > 1 or re.search(r"datasets|combined|aggregated|pooled", text_lower):
        suggestions.append("Compiles")

    # Review language
    if re.search(r"review(ed|ing)?|evaluat(e|ed|ion)|assess(ed|ment)|survey", text_lower):
        suggestions.append("Reviews")

    # Derivation
    if re.search(r"derived|based on|preprocessed|spike.?sorted|transformed", text_lower):
        suggestions.append("IsDerivedFrom")

    # Background reference
    if re.search(r"(publicly )?available|repository|archive|resource", text_lower):
        suggestions.append("References/CitesForInformation")

    return suggestions or ["Cites (generic)"]


@click.command()
@click.argument("pdfs_dir", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--sample",
    "-n",
    default=20,
    type=int,
    help="Number of papers to analyze (default: 20)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Save analysis to markdown file",
)
def main(pdfs_dir: Path, sample: int, output: Path | None) -> None:
    """Analyze collected PDFs/HTMLs to understand citation patterns.

    PDFS_DIR: Directory containing collected papers (e.g., /path/to/dandi-bib/citations/pdfs)
    """
    # Find all PDFs and HTMLs
    papers = list(pdfs_dir.rglob("*.pdf")) + list(pdfs_dir.rglob("*.html"))

    if not papers:
        click.echo(f"No PDFs or HTMLs found in {pdfs_dir}", err=True)
        sys.exit(1)

    click.echo(f"Found {len(papers)} papers. Analyzing {min(sample, len(papers))}...\n")

    results = []

    for i, paper_path in enumerate(papers[:sample], 1):
        click.echo(f"[{i}/{min(sample, len(papers))}] Analyzing {paper_path.name}...")

        # Extract DANDI mentions
        if paper_path.suffix == ".pdf":
            mentions = extract_dandi_mentions_pdf(paper_path)
        else:
            mentions = extract_dandi_mentions_html(paper_path)

        if not mentions:
            click.echo("  ⚠️  No DANDI mentions found\n")
            continue

        click.echo(f"  Found {len(mentions)} DANDI mention(s)")

        # Classify each mention
        analysis = {"path": paper_path, "mentions": []}

        for mention in mentions[:3]:  # Show first 3 mentions
            suggested = classify_relationship_from_text(mention)
            analysis["mentions"].append({"text": mention, "suggested": suggested})

            click.echo(f"  📄 {mention[:100]}...")
            click.echo(f"     → Suggested: {', '.join(suggested)}")

        results.append(analysis)
        click.echo()

    # Summary statistics
    all_suggestions = []
    for result in results:
        for mention in result["mentions"]:
            all_suggestions.extend(mention["suggested"])

    click.echo("\n" + "=" * 80)
    click.echo("SUMMARY")
    click.echo("=" * 80)

    from collections import Counter

    counts = Counter(all_suggestions)
    click.echo("\nSuggested relationship types (total mentions):")
    for rel_type, count in counts.most_common():
        click.echo(f"  {rel_type:30s} {count:3d}")

    # Save to file if requested
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w") as f:
            f.write("# DANDI Citation Pattern Analysis\n\n")
            f.write(f"Analyzed {len(results)} papers from {pdfs_dir}\n\n")

            for result in results:
                f.write(f"## {result['path'].name}\n\n")
                for mention in result["mentions"]:
                    f.write(f"**Mention**: {mention['text']}\n\n")
                    f.write(f"**Suggested**: {', '.join(mention['suggested'])}\n\n")
                f.write("---\n\n")

            f.write("## Summary\n\n")
            for rel_type, count in counts.most_common():
                f.write(f"- **{rel_type}**: {count}\n")

        click.echo(f"\n✅ Analysis saved to {output}")


if __name__ == "__main__":
    main()
