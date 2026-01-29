"""Detect and mark merged citations (preprints with published versions)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import requests
from rapidfuzz import fuzz

if TYPE_CHECKING:
    from citations_collector.models.generated import CitationRecord

from citations_collector.models.generated import CitationStatus

logger = logging.getLogger(__name__)


class MergeDetector:
    """Detect preprints that have published versions and mark them as merged."""

    def __init__(self, email: str = "site-unpaywall@oneukrainian.com", timeout: int = 30):
        """Initialize the merge detector.

        Args:
            email: Email for CrossRef API (polite pool)
            timeout: HTTP request timeout in seconds
        """
        self.email = email
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": f"citations-collector ({email})"})

    def detect_merged_pairs(self, citations: list[CitationRecord]) -> dict[str, str]:
        """Detect which citations are preprints with published versions.

        Args:
            citations: List of citation records to analyze

        Returns:
            Dictionary mapping preprint DOI -> published DOI
        """
        merged_pairs: dict[str, str] = {}
        doi_to_citation = {c.citation_doi: c for c in citations if c.citation_doi}

        for citation in citations:
            if not citation.citation_doi:
                continue

            # Check if this is a preprint with a published version
            published_doi = self._get_published_version(citation.citation_doi)
            if published_doi and (
                published_doi in doi_to_citation or self._verify_doi_exists(published_doi)
            ):
                merged_pairs[citation.citation_doi] = published_doi
                logger.info(f"Detected merge: {citation.citation_doi} -> {published_doi}")

        return merged_pairs

    def _get_published_version(self, doi: str) -> str | None:
        """Get the published version DOI for a preprint.

        Args:
            doi: DOI of the potential preprint

        Returns:
            DOI of published version, or None if not found
        """
        try:
            # Query CrossRef for this DOI's metadata
            url = f"https://api.crossref.org/works/{doi}"
            params = {"mailto": self.email}
            resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()

            message = data.get("message", {})

            # Check for "is-preprint-of" relationship
            relations = message.get("relation", {})
            is_preprint_of = relations.get("is-preprint-of", [])

            for rel in is_preprint_of:
                if "id" in rel:
                    # Extract DOI from the full URL if needed
                    rel_id = str(rel["id"])
                    if rel_id.startswith("https://doi.org/"):
                        return str(rel_id.replace("https://doi.org/", ""))
                    elif rel_id.startswith("http://dx.doi.org/"):
                        return str(rel_id.replace("http://dx.doi.org/", ""))
                    return str(rel_id)

            # Check if this is a bioRxiv/medRxiv preprint (common case)
            # Sometimes the relationship isn't explicit but the DOI pattern helps
            if self._is_preprint_server(doi):
                # Try to find via title fuzzy matching in our dataset
                # (this is a fallback and should be used carefully)
                pass

        except requests.RequestException as e:
            logger.warning(f"Failed to check CrossRef for {doi}: {e}")
        except (KeyError, ValueError) as e:
            logger.warning(f"Unexpected CrossRef response format for {doi}: {e}")

        return None

    def _is_preprint_server(self, doi: str) -> bool:
        """Check if DOI is from a known preprint server.

        Args:
            doi: DOI to check

        Returns:
            True if from a preprint server
        """
        preprint_prefixes = [
            "10.1101/",  # bioRxiv, medRxiv
            "10.31219/",  # OSF Preprints
            "10.20944/",  # Preprints.org
            "10.48550/",  # arXiv
        ]
        return any(doi.startswith(prefix) for prefix in preprint_prefixes)

    def _verify_doi_exists(self, doi: str) -> bool:
        """Verify that a DOI exists and is accessible.

        Args:
            doi: DOI to verify

        Returns:
            True if DOI exists
        """
        try:
            url = f"https://api.crossref.org/works/{doi}"
            params = {"mailto": self.email}
            resp = self.session.get(url, params=params, timeout=self.timeout, allow_redirects=False)
            return bool(resp.status_code == 200)
        except requests.RequestException:
            return False

    def mark_merged_citations(
        self, citations: list[CitationRecord], merged_pairs: dict[str, str]
    ) -> int:
        """Mark citations as merged in place.

        Args:
            citations: List of citation records to update
            merged_pairs: Dictionary mapping preprint DOI -> published DOI

        Returns:
            Number of citations marked as merged
        """
        marked_count = 0
        for citation in citations:
            if citation.citation_doi and citation.citation_doi in merged_pairs:
                citation.citation_status = CitationStatus.merged
                citation.citation_merged_into = merged_pairs[citation.citation_doi]
                marked_count += 1
                logger.info(
                    f"Marked {citation.citation_doi} as merged into {citation.citation_merged_into}"
                )
        return marked_count

    def fuzzy_match_by_title(
        self,
        citations: list[CitationRecord],
        threshold: int = 90,
    ) -> dict[str, str]:
        """Find potential merges by fuzzy title matching (fallback method).

        This is a heuristic approach for cases where CrossRef relationships
        are not explicitly registered.

        Args:
            citations: List of citation records
            threshold: Minimum similarity score (0-100) for matching

        Returns:
            Dictionary mapping preprint DOI -> published DOI candidates
        """
        potential_pairs: dict[str, str] = {}
        preprints = [
            c for c in citations if c.citation_doi and self._is_preprint_server(c.citation_doi)
        ]
        published = [
            c for c in citations if c.citation_doi and not self._is_preprint_server(c.citation_doi)
        ]

        for preprint in preprints:
            if not preprint.citation_title:
                continue

            best_match = None
            best_score: float = 0.0

            for pub in published:
                if not pub.citation_title:
                    continue

                # Check if they have similar authors (if available)
                # and similar publication years
                # (This is a heuristic - use with caution)

                score = fuzz.ratio(preprint.citation_title.lower(), pub.citation_title.lower())
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = pub

            if best_match and preprint.citation_doi and best_match.citation_doi:
                logger.info(
                    f"Fuzzy match found (score {best_score}): "
                    f"{preprint.citation_doi} ~> {best_match.citation_doi}"
                )
                potential_pairs[preprint.citation_doi] = best_match.citation_doi

        return potential_pairs
