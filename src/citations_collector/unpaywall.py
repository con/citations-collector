"""Unpaywall API client for open access PDF discovery."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)


@dataclass
class UnpaywallResult:
    doi: str
    is_oa: bool
    oa_status: str  # gold/green/bronze/hybrid/closed
    best_oa_url: str | None  # direct PDF URL
    license: str | None


class UnpaywallClient:
    BASE_URL = "https://api.unpaywall.org/v2/"

    def __init__(self, email: str = "site-unpaywall@oneukrainian.com") -> None:
        self.email = email
        self._last_request_time = 0.0

    def lookup(self, doi: str) -> UnpaywallResult:
        """Look up OA status and PDF URL for a DOI."""
        self._rate_limit()
        url = f"{self.BASE_URL}{doi}"
        try:
            resp = requests.get(url, params={"email": self.email}, timeout=30)
            if resp.status_code == 404:
                return UnpaywallResult(
                    doi=doi, is_oa=False, oa_status="closed", best_oa_url=None, license=None
                )
            resp.raise_for_status()
            data = resp.json()
            best_loc = data.get("best_oa_location") or {}
            return UnpaywallResult(
                doi=doi,
                is_oa=data.get("is_oa", False),
                oa_status=data.get("oa_status", "closed") or "closed",
                best_oa_url=best_loc.get("url_for_pdf") or best_loc.get("url"),
                license=best_loc.get("license"),
            )
        except requests.RequestException as e:
            logger.warning("Unpaywall lookup failed for %s: %s", doi, e)
            return UnpaywallResult(
                doi=doi, is_oa=False, oa_status="closed", best_oa_url=None, license=None
            )

    def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < 0.1:
            time.sleep(0.1 - elapsed)
        self._last_request_time = time.monotonic()
