"""GitHub repository to Zenodo DOI mapping."""

from __future__ import annotations

import logging
import os
import re

import requests

from citations_collector.models import ItemRef, RefType

logger = logging.getLogger(__name__)


class GitHubMapper:
    """
    Map GitHub repositories to Zenodo DOIs.

    Many open source projects use Zenodo to archive releases and get DOIs.
    This mapper attempts to extract Zenodo DOIs from GitHub repositories
    via multiple strategies:

    1. Check repository description for Zenodo badge
    2. Check README for Zenodo DOI badge
    3. Look for .zenodo.json file

    Example:
        "datalad/datalad" → 10.5281/zenodo.808846 (concept DOI)
    """

    GITHUB_API = "https://api.github.com/repos"
    ZENODO_DOI_PATTERN = re.compile(r"10\.5281/zenodo\.(\d+)")

    def __init__(self, github_token: str | None = None) -> None:
        """
        Initialize GitHub mapper.

        Args:
            github_token: Optional GitHub personal access token for higher rate limits.
                         If not provided, reads from GITHUB_TOKEN environment variable.
        """
        # Use provided token, or fallback to environment variable
        if github_token is None:
            github_token = os.getenv("GITHUB_TOKEN")

        self.session = requests.Session()
        if github_token:
            self.session.headers["Authorization"] = f"token {github_token}"
            logger.debug("Using GitHub token for authentication")

    def map_to_doi(self, repo: str) -> ItemRef | None:
        """
        Map GitHub repository to Zenodo DOI.

        Args:
            repo: GitHub repository in "owner/name" format (e.g., "datalad/datalad")

        Returns:
            ItemRef with DOI if found, None otherwise
        """
        # Query GitHub API for repository info
        url = f"{self.GITHUB_API}/{repo}"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.warning(f"GitHub API error for {repo}: {e}")
            return None

        # Strategy 1: Check repository description
        description = data.get("description", "")
        doi = self._extract_zenodo_doi(description)
        if doi:
            logger.info(f"Found Zenodo DOI in description for {repo}: {doi}")
            return ItemRef(ref_type=RefType("doi"), ref_value=doi)

        # Strategy 2: Check README
        readme_url = f"{self.GITHUB_API}/{repo}/readme"
        try:
            readme_response = self.session.get(readme_url, timeout=30)
            readme_response.raise_for_status()
            readme_data = readme_response.json()

            # README content is base64 encoded
            import base64

            content = base64.b64decode(readme_data.get("content", "")).decode("utf-8")
            doi = self._extract_zenodo_doi(content)
            if doi:
                logger.info(f"Found Zenodo DOI in README for {repo}: {doi}")
                return ItemRef(ref_type=RefType("doi"), ref_value=doi)
        except requests.RequestException:
            # README not found or other error, continue to next strategy
            pass

        # Strategy 3: Check for .zenodo.json file
        zenodo_json_url = f"{self.GITHUB_API}/{repo}/contents/.zenodo.json"
        try:
            zenodo_response = self.session.get(zenodo_json_url, timeout=30)
            zenodo_response.raise_for_status()
            zenodo_data = zenodo_response.json()

            import base64
            import json

            content = base64.b64decode(zenodo_data.get("content", "")).decode("utf-8")
            zenodo_config = json.loads(content)

            # .zenodo.json might have related_identifiers with DOI
            for identifier in zenodo_config.get("related_identifiers", []):
                if identifier.get("scheme") == "doi":
                    doi_value = identifier.get("identifier")
                    if doi_value:
                        # Clean up DOI (remove https://doi.org/ prefix)
                        doi_clean = doi_value.replace("https://doi.org/", "")
                        logger.info(f"Found Zenodo DOI in .zenodo.json for {repo}: {doi_clean}")
                        return ItemRef(ref_type=RefType("doi"), ref_value=doi_clean)
        except requests.RequestException:
            # .zenodo.json not found or other error
            pass

        logger.info(f"No Zenodo DOI found for GitHub repo {repo}")
        return None

    def _extract_zenodo_doi(self, text: str) -> str | None:
        """
        Extract Zenodo DOI from text.

        Looks for common patterns like:
        - https://doi.org/10.5281/zenodo.808846
        - 10.5281/zenodo.808846
        - [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.808846.svg)]

        Args:
            text: Text to search

        Returns:
            DOI string if found, None otherwise
        """
        match = self.ZENODO_DOI_PATTERN.search(text)
        if match:
            # Return full DOI
            return f"10.5281/zenodo.{match.group(1)}"
        return None
