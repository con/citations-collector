# Usage Guide

Quick guide to using citations-collector with the provided examples.

## Installation

```bash
# Install with development dependencies
uv pip install -e ".[devel]"

# Or just the package
uv pip install -e .
```

## Basic Commands

### Show Help

```bash
citations-collector --help
citations-collector discover --help
```

### Check Version

```bash
citations-collector --version
```

## Example 1: ReproNim Tools Collection

The ReproNim example includes various types of references that need expansion:
- `zenodo_concept` - Zenodo concept records that expand to all version DOIs
- `github` - GitHub repositories that may have Zenodo DOIs
- `doi` - Direct DOI references

### Discover Citations with Expansion

```bash
# Expand non-DOI refs and discover citations via CrossRef
citations-collector discover examples/repronim-tools.yaml \
    --expand-refs \
    --sources crossref \
    --email your.email@example.org \
    --output repronim-citations.tsv
```

**What this does:**
1. Loads the collection from `examples/repronim-tools.yaml`
2. Expands `zenodo_concept` refs by querying Zenodo API for all versions
3. Maps `github` refs to Zenodo DOIs by checking README, description, .zenodo.json
4. Discovers citations via CrossRef for all DOI references
5. Saves results to `repronim-citations.tsv`

**Note:** Using `--email` puts you in CrossRef's "polite pool" with better rate limits.

### Full Refresh vs Incremental

```bash
# Incremental mode (default): Only discover new citations since last run
citations-collector discover examples/repronim-tools.yaml \
    --expand-refs \
    --sources crossref \
    --output repronim-citations.tsv

# Full refresh: Rediscover all citations regardless of previous runs
citations-collector discover examples/repronim-tools.yaml \
    --expand-refs \
    --sources crossref \
    --full-refresh \
    --output repronim-citations.tsv
```

### Using Multiple Discovery Sources

```bash
# Use both CrossRef and OpenCitations (default)
citations-collector discover examples/repronim-tools.yaml \
    --expand-refs \
    --output repronim-citations.tsv

# Use all available sources
citations-collector discover examples/repronim-tools.yaml \
    --expand-refs \
    --sources crossref \
    --sources opencitations \
    --sources datacite \
    --output repronim-citations.tsv
```

## Example 2: DANDI Archive Collection

The DANDI example contains dataset DOIs from the DANDI Archive. DataCite Event Data is the best source for dataset citations.

### Discover Citations for DANDI DOIs

```bash
# Use DataCite for dataset DOIs
citations-collector discover examples/dandi-collection.yaml \
    --sources datacite \
    --output dandi-citations.tsv
```

**Note:** DataCite Event Data may not have citations for all DOIs yet. Finding 0 citations is acceptable - it means the datasets haven't been cited in tracked publications yet.

### Try Multiple Sources

```bash
# Try both DataCite and CrossRef
citations-collector discover examples/dandi-collection.yaml \
    --sources datacite \
    --sources crossref \
    --output dandi-citations.tsv
```

## Understanding the Output

The output TSV file contains one row per citation discovered:

```tsv
item_id	item_flavor	item_ref_type	item_ref_value	citation_doi	citation_source	citation_status
open-brain-consent	latest	doi	10.1002/hbm.25351	10.1109/ISBI.2019.8759515	crossref	active
```

**Key columns:**
- `item_id`: The item being cited (from your collection)
- `item_flavor`: Version/flavor of the item
- `item_ref_value`: The specific DOI that was cited
- `citation_doi`: The DOI of the paper that cites your item
- `citation_source`: Which API found this citation (crossref, opencitations, datacite)
- `citation_status`: Status (active, retracted, etc.)

## Verbose Output

Add the `-v` flag before the command to see detailed API activity:

```bash
citations-collector -v discover examples/repronim-tools.yaml \
    --expand-refs \
    --sources crossref \
    --output repronim-citations.tsv
```

This shows:
- API calls being made
- Expansion results (how many DOIs found)
- Discovery progress
- Any errors or warnings

## Common Use Cases

### 1. First-time Discovery for New Collection

```bash
# Full discovery with expansion
citations-collector discover examples/repronim-tools.yaml \
    --expand-refs \
    --sources crossref \
    --sources opencitations \
    --email your.email@example.org \
    --full-refresh \
    --output citations.tsv
```

### 2. Regular Updates (Check for New Citations)

```bash
# Incremental mode - only new citations
citations-collector discover examples/repronim-tools.yaml \
    --expand-refs \
    --sources crossref \
    --sources opencitations \
    --output citations.tsv
```

The incremental mode tracks the last discovery date and only queries for citations added since then.

### 3. Quick Test with Simple Collection

```bash
# Use the simple test fixture
citations-collector discover tests/fixtures/collections/simple.yaml \
    --sources crossref \
    --output test-citations.tsv
```

## Expected API Behavior

### CrossRef
- ✅ Works well for DOIs from academic publishers (journals, conferences)
- ⚠️ Returns 404 for Zenodo DOIs (Zenodo DOIs not indexed by CrossRef)
- ✅ Supports polite pool with `--email` flag for better rate limits
- 🌐 No authentication required

### OpenCitations
- ✅ Free and open citation data
- ✅ Good coverage for older academic papers
- 🌐 No authentication required

### DataCite Event Data
- ✅ Best for dataset DOIs (DANDI, Zenodo, etc.)
- ⚠️ Coverage is still growing - may return 0 citations for new datasets
- 🌐 No authentication required

### Zenodo API (for expansion)
- ✅ Expands concept records to all version DOIs
- ⚠️ May rate limit if queried too frequently
- 🌐 No authentication required

### GitHub API (for mapping)
- ✅ Maps GitHub repos to Zenodo DOIs
- ⚠️ Rate limit: 60 requests/hour without token, 5000/hour with token
- 💡 Set `GITHUB_TOKEN` environment variable for higher limits

## Troubleshooting

### GitHub Rate Limits

If you hit GitHub rate limits during expansion:

```bash
# Set GitHub token for higher rate limits
export GITHUB_TOKEN="your_github_token_here"

# Then run discovery
citations-collector discover examples/repronim-tools.yaml --expand-refs --output citations.tsv
```

### Zenodo API Errors

If Zenodo returns 403 Forbidden:
- The Zenodo API may be temporarily blocking requests
- Try again later or reduce request frequency
- The tool will gracefully handle errors and continue with other refs

### No Citations Found

This is normal and acceptable:
- DataCite Event Data has incomplete coverage
- New/unpublished datasets may not have citations yet
- Software archived on Zenodo may not be cited via DOI yet
- The tool will save an empty TSV file (header only)

## Pre-commit Setup

The project now uses pre-commit hooks to ensure code quality:

```bash
# Install pre-commit hooks (one time)
uv run pre-commit install

# Run manually on all files
uv run pre-commit run --all-files

# Hooks run automatically on git commit
git commit -m "your message"
```

The hooks check:
- Ruff linting and formatting
- Trailing whitespace
- End-of-file newlines
- YAML/TOML syntax
- Large files
- Line endings

## Testing

```bash
# Run unit tests only (fast, no network calls)
tox

# Run integration tests only (slow, live APIs)
tox -e integration

# Run all tests
tox -e all

# Run specific test
pytest tests/test_integration.py::test_repronim_collection_with_expansion -v
```

See `tests/INTEGRATION_TESTS.md` for more details on testing.

## Next Steps

1. **Try the examples** - Run discovery on repronim or dandi examples
2. **Create your own collection** - Use the examples as templates
3. **Set up automation** - Use GitHub Actions for regular discovery (see `examples/github-ci-workflow.yaml`)
4. **Curate results** - Review the TSV file and mark false positives
5. **Sync to Zotero** - (Coming soon) Sync citations to your Zotero library
