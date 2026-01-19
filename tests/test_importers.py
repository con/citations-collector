"""Tests for reference importers."""

from __future__ import annotations

import base64

import pytest
import responses

from citations_collector.importers import GitHubMapper, ZenodoExpander


@pytest.mark.ai_generated
@responses.activate
def test_zenodo_expander_success() -> None:
    """Test successful Zenodo concept expansion."""
    # Mock Zenodo API response for concept record
    concept_response = {
        "conceptdoi": "10.5281/zenodo.808846",
        "doi": "10.5281/zenodo.808847",
        "links": {"versions": "https://zenodo.org/api/records/808846/versions"},
    }

    # Mock versions endpoint response
    versions_response = {
        "hits": {
            "hits": [
                {"doi": "10.5281/zenodo.808847"},
                {"doi": "10.5281/zenodo.1234567"},
                {"doi": "10.5281/zenodo.2345678"},
            ]
        }
    }

    responses.add(
        responses.GET,
        "https://zenodo.org/api/records/808846",
        json=concept_response,
        status=200,
    )

    responses.add(
        responses.GET,
        "https://zenodo.org/api/records/808846/versions",
        json=versions_response,
        status=200,
    )

    # Expand concept
    expander = ZenodoExpander()
    refs = expander.expand("808846")

    # Verify results
    assert len(refs) == 4  # concept DOI + 3 version DOIs
    dois = {ref.ref_value for ref in refs}
    assert "10.5281/zenodo.808846" in dois  # concept DOI
    assert "10.5281/zenodo.808847" in dois  # current version DOI
    assert "10.5281/zenodo.1234567" in dois  # older version DOI
    assert "10.5281/zenodo.2345678" in dois  # another version DOI


@pytest.mark.ai_generated
@responses.activate
def test_zenodo_expander_no_versions() -> None:
    """Test Zenodo expansion when versions endpoint not available."""
    concept_response = {
        "conceptdoi": "https://doi.org/10.5281/zenodo.808846",
        "doi": "https://doi.org/10.5281/zenodo.808847",
        # No versions link
    }

    responses.add(
        responses.GET,
        "https://zenodo.org/api/records/808846",
        json=concept_response,
        status=200,
    )

    expander = ZenodoExpander()
    refs = expander.expand("808846")

    # Should still get concept DOI (cleaned of https prefix)
    assert len(refs) == 1
    assert refs[0].ref_type == "doi"
    assert refs[0].ref_value == "10.5281/zenodo.808846"


@pytest.mark.ai_generated
@responses.activate
def test_zenodo_expander_network_error() -> None:
    """Test Zenodo expansion with network error."""
    responses.add(responses.GET, "https://zenodo.org/api/records/808846", status=500)

    expander = ZenodoExpander()
    refs = expander.expand("808846")

    # Should return empty list on error
    assert refs == []


@pytest.mark.ai_generated
@responses.activate
def test_github_mapper_from_description() -> None:
    """Test GitHub to DOI mapping from repository description."""
    repo_response = {
        "name": "datalad",
        "description": "Data management system. DOI: 10.5281/zenodo.808846",
    }

    responses.add(
        responses.GET,
        "https://api.github.com/repos/datalad/datalad",
        json=repo_response,
        status=200,
    )

    mapper = GitHubMapper()
    ref = mapper.map_to_doi("datalad/datalad")

    assert ref is not None
    assert ref.ref_type == "doi"
    assert ref.ref_value == "10.5281/zenodo.808846"


@pytest.mark.ai_generated
@responses.activate
def test_github_mapper_from_readme() -> None:
    """Test GitHub to DOI mapping from README badge."""
    repo_response = {"name": "test-repo", "description": "A test repository"}

    readme_content = base64.b64encode(
        b"# Test Repo\n[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.123456.svg)](https://doi.org/10.5281/zenodo.123456)"
    ).decode("utf-8")

    readme_response = {"content": readme_content}

    responses.add(
        responses.GET,
        "https://api.github.com/repos/owner/test-repo",
        json=repo_response,
        status=200,
    )

    responses.add(
        responses.GET,
        "https://api.github.com/repos/owner/test-repo/readme",
        json=readme_response,
        status=200,
    )

    mapper = GitHubMapper()
    ref = mapper.map_to_doi("owner/test-repo")

    assert ref is not None
    assert ref.ref_type == "doi"
    assert ref.ref_value == "10.5281/zenodo.123456"


@pytest.mark.ai_generated
@responses.activate
def test_github_mapper_no_doi_found() -> None:
    """Test GitHub mapper when no DOI is found."""
    repo_response = {"name": "test-repo", "description": "A test repository"}

    readme_response = {"content": base64.b64encode(b"# Test Repo\nNo DOI here").decode("utf-8")}

    responses.add(
        responses.GET,
        "https://api.github.com/repos/owner/test-repo",
        json=repo_response,
        status=200,
    )

    responses.add(
        responses.GET,
        "https://api.github.com/repos/owner/test-repo/readme",
        json=readme_response,
        status=200,
    )

    responses.add(
        responses.GET,
        "https://api.github.com/repos/owner/test-repo/contents/.zenodo.json",
        status=404,
    )

    mapper = GitHubMapper()
    ref = mapper.map_to_doi("owner/test-repo")

    assert ref is None


@pytest.mark.ai_generated
@responses.activate
def test_github_mapper_network_error() -> None:
    """Test GitHub mapper with network error."""
    responses.add(responses.GET, "https://api.github.com/repos/owner/test-repo", status=500)

    mapper = GitHubMapper()
    ref = mapper.map_to_doi("owner/test-repo")

    assert ref is None
