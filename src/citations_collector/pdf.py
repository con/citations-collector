"""PDF acquisition and management."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import requests

from citations_collector.models import CitationRecord
from citations_collector.unpaywall import UnpaywallClient

logger = logging.getLogger(__name__)


class PDFAcquirer:
    def __init__(
        self,
        output_dir: Path = Path("pdfs"),
        email: str = "site-unpaywall@oneukrainian.com",
        git_annex: bool = False,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.unpaywall = UnpaywallClient(email=email)
        self.git_annex = git_annex

    def acquire_for_citation(self, citation: CitationRecord, dry_run: bool = False) -> bool:
        """Look up OA status, download PDF if available. Returns True if PDF was acquired."""
        if not citation.citation_doi:
            return False

        result = self.unpaywall.lookup(citation.citation_doi)
        citation.oa_status = result.oa_status
        citation.pdf_url = result.best_oa_url

        if not result.best_oa_url or not result.is_oa:
            return False

        pdf_path = self._doi_to_path(citation.citation_doi)

        if dry_run:
            logger.info("Would download %s -> %s", citation.citation_doi, pdf_path)
            return False

        # Skip if already downloaded
        full_path = self.output_dir / pdf_path
        if full_path.exists():
            citation.pdf_path = str(self.output_dir / pdf_path)
            return False

        # Download PDF
        if self._download(result.best_oa_url, full_path):
            citation.pdf_path = str(self.output_dir / pdf_path)
            # Also fetch BibTeX
            self._fetch_bibtex(citation.citation_doi, full_path.parent / "article.bib")
            # git-annex
            if self.git_annex:
                self._annex_addurl(full_path, result.best_oa_url)
            return True
        return False

    def acquire_all(
        self,
        citations: list[CitationRecord],
        dry_run: bool = False,
    ) -> dict[str, int]:
        """Process all citations. Returns counts dict."""
        counts = {"downloaded": 0, "skipped": 0, "no_oa": 0, "no_doi": 0, "error": 0}
        seen_dois: set[str] = set()

        for citation in citations:
            if not citation.citation_doi:
                counts["no_doi"] += 1
                continue
            if citation.citation_doi in seen_dois:
                # Copy fields from first citation with same DOI
                for prev in citations:
                    if prev.citation_doi == citation.citation_doi and prev.oa_status:
                        citation.oa_status = prev.oa_status
                        citation.pdf_url = prev.pdf_url
                        citation.pdf_path = prev.pdf_path
                        break
                counts["skipped"] += 1
                continue
            seen_dois.add(citation.citation_doi)

            if citation.pdf_path and Path(citation.pdf_path).exists():
                counts["skipped"] += 1
                continue

            try:
                if self.acquire_for_citation(citation, dry_run=dry_run):
                    counts["downloaded"] += 1
                elif citation.oa_status == "closed" or not citation.pdf_url:
                    counts["no_oa"] += 1
                else:
                    counts["skipped"] += 1
            except Exception:
                logger.exception("Error acquiring PDF for %s", citation.citation_doi)
                counts["error"] += 1

        return counts

    def _doi_to_path(self, doi: str) -> Path:
        """Convert DOI to relative path: 10.1038/s41597-023-02214-y -> 10.1038/.../article.pdf"""
        return Path(doi) / "article.pdf"

    def _download(self, url: str, dest: Path) -> bool:
        """Download URL to dest. Returns True on success."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            resp = requests.get(url, timeout=60, stream=True)
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info("Downloaded %s", dest)
            return True
        except requests.RequestException as e:
            logger.warning("Download failed for %s: %s", url, e)
            if dest.exists():
                dest.unlink()
            return False

    def _fetch_bibtex(self, doi: str, dest: Path) -> None:
        """Fetch BibTeX via DOI content negotiation."""
        try:
            resp = requests.get(
                f"https://doi.org/{doi}",
                headers={"Accept": "application/x-bibtex"},
                timeout=30,
                allow_redirects=True,
            )
            if resp.status_code == 200 and resp.text.strip():
                dest.write_text(resp.text)
                logger.info("Saved BibTeX to %s", dest)
        except requests.RequestException as e:
            logger.warning("BibTeX fetch failed for %s: %s", doi, e)

    def _annex_addurl(self, path: Path, url: str) -> None:
        """Register URL with git-annex."""
        try:
            subprocess.run(
                ["git", "annex", "addurl", "--file", str(path), url],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info("git annex addurl for %s", path)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.warning("git annex addurl failed for %s: %s", path, e)
