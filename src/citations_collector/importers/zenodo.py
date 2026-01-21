"""Zenodo concept expansion to version DOIs."""

from __future__ import annotations

import logging
import os

import requests

from citations_collector.models import ItemRef, RefType

logger = logging.getLogger(__name__)


class ZenodoExpander:
    """
    Expand Zenodo concept IDs to all version DOIs.

    Zenodo uses a "concept" DOI that represents all versions of a work,
    and separate version-specific DOIs. This expander queries the Zenodo
    API to get all version DOIs for a concept.

    Example:
        Concept ID 808846 (DataLad) expands to:
        - 10.5281/zenodo.808846 (concept DOI)
        - 10.5281/zenodo.808847 (v0.1.0)
        - 10.5281/zenodo.1234567 (v0.2.0)
        - ... (all other versions)
    """

    BASE_URL = "https://zenodo.org/api/records"

    def __init__(self, zenodo_token: str | None = None) -> None:
        """
        Initialize Zenodo expander.

        Args:
            zenodo_token: Optional Zenodo personal access token for authentication.
                         If not provided, reads from ZENODO_TOKEN environment variable.
        """
        # Use provided token, or fallback to environment variable
        if zenodo_token is None:
            zenodo_token = os.getenv("ZENODO_TOKEN")

        self.session = requests.Session()
        if zenodo_token:
            # Zenodo uses Bearer token authentication
            self.session.headers["Authorization"] = f"Bearer {zenodo_token}"
            logger.debug("Using Zenodo token for authentication")

    def expand(self, concept_id: str) -> list[ItemRef]:
        """
        Expand Zenodo concept ID to all version DOIs.

        Args:
            concept_id: Zenodo concept ID (numeric, e.g. "808846")

        Returns:
            List of ItemRef objects with DOI references for each version
        """
        # Query Zenodo API for the concept record (latest version)
        url = f"{self.BASE_URL}/{concept_id}"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.warning(f"Zenodo API error for concept {concept_id}: {e}")
            return []

        # Extract version DOIs
        refs = []

        # Strategy 1: Get concept DOI (represents all versions)
        # This is the most comprehensive as it aggregates citations across versions
        concept_doi = data.get("conceptdoi")
        if concept_doi:
            # Extract just the DOI part (remove https://doi.org/ prefix if present)
            concept_doi_clean = concept_doi.replace("https://doi.org/", "")
            refs.append(ItemRef(ref_type=RefType("doi"), ref_value=concept_doi_clean))

        # Strategy 2: Get all individual version DOIs
        # Check if there's a link to all versions
        links = data.get("links", {})
        versions_url = links.get("versions")

        if versions_url:
            # Query the versions endpoint to get all versions
            try:
                versions_response = self.session.get(versions_url, timeout=30)
                versions_response.raise_for_status()
                versions_data = versions_response.json()

                # Extract DOIs from each version
                for hit in versions_data.get("hits", {}).get("hits", []):
                    version_doi = hit.get("doi")
                    if version_doi:
                        version_doi_clean = version_doi.replace("https://doi.org/", "")
                        # Don't duplicate concept DOI
                        if version_doi_clean != concept_doi_clean:
                            refs.append(
                                ItemRef(ref_type=RefType("doi"), ref_value=version_doi_clean)
                            )
            except requests.RequestException as e:
                logger.warning(f"Failed to fetch versions for {concept_id}: {e}")
                # Fall back to just the concept DOI

        logger.info(f"Expanded Zenodo concept {concept_id} to {len(refs)} DOI references")
        return refs
