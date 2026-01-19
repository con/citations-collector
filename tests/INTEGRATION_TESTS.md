# Integration Tests

This directory contains integration tests that make real HTTP requests to external APIs. These tests validate the real-world functionality of the citations-collector with live services.

## Test Types

### Unit Tests (Mocked)
- **Files**: `test_*.py` (except `test_integration.py`)
- **Markers**: `@pytest.mark.ai_generated`
- **Speed**: Fast (~0.2 seconds)
- **Network**: No external calls (uses `@responses.activate`)
- **Purpose**: Test code logic with predictable mocked responses

### Integration Tests (Live APIs)
- **File**: `test_integration.py`
- **Markers**: `@pytest.mark.integration` and `@pytest.mark.slow`
- **Speed**: Slow (~20 seconds total)
- **Network**: Makes real API calls to external services
- **Purpose**: Validate real-world workflow with example collections

## Running Tests

### Run Unit Tests Only (Default)
```bash
# Via tox (recommended)
tox

# Or directly with pytest
pytest -m "not integration"
```

**Result**: Runs 32 unit tests, skips 6 integration tests (~2 seconds)

### Run Integration Tests Only
```bash
# Via tox
tox -e integration

# Or directly with pytest
pytest -m integration -v
pytest tests/test_integration.py -v
```

**Result**: Runs 6 integration tests with live API calls (~20 seconds)

### Run All Tests (Unit + Integration)
```bash
# Via tox
tox -e all

# Or directly with pytest
pytest -v
```

**Result**: Runs all 38 tests (~22 seconds)

## Integration Test Coverage

### 1. ReproNim Collection with Expansion
**Test**: `test_repronim_collection_with_expansion`

- Loads `examples/repronim-tools.yaml`
- Expands zenodo_concept and github refs to DOIs (live API calls)
- Discovers citations using CrossRef
- Validates ~30 refs expanded, 18+ citations discovered

**APIs Called**:
- Zenodo API (for concept expansion)
- GitHub API (for repo→DOI mapping)
- CrossRef API (for citation discovery)

### 2. DANDI Collection with DataCite
**Test**: `test_dandi_collection_with_datacite`

- Loads `examples/dandi-collection.yaml`
- Discovers citations using DataCite Event Data
- Validates workflow completes (may find 0 citations - acceptable)

**APIs Called**:
- DataCite Event Data API

### 3. Simple Collection with CrossRef
**Test**: `test_simple_collection_crossref`

- Loads `tests/fixtures/collections/simple.yaml`
- Basic CrossRef API integration test
- Minimal test to verify API connectivity

**APIs Called**:
- CrossRef API

### 4. Zenodo Expansion Real Concept
**Test**: `test_zenodo_expansion_real_concept`

- Tests Zenodo concept expansion in isolation
- Uses DataLad concept ID (808846)
- Validates expansion to 25+ version DOIs

**APIs Called**:
- Zenodo API

### 5. GitHub Mapping Real Repo
**Test**: `test_github_mapping_real_repo`

- Tests GitHub→Zenodo DOI mapping in isolation
- Uses datalad/datalad repository
- Validates DOI extraction from repo metadata

**APIs Called**:
- GitHub API (may hit rate limits without token)

### 6. Full Workflow End-to-End
**Test**: `test_full_workflow_end_to_end`

- Complete workflow: load → expand → discover → save → reload
- Validates data persistence and round-trip
- Tests with ReproNim collection

**APIs Called**:
- Zenodo API
- GitHub API
- CrossRef API

## External Dependencies

### APIs Used
1. **CrossRef** - https://api.crossref.org
   - Rate Limits: 50 req/s (anonymous), better with polite pool
   - No authentication required

2. **OpenCitations** - https://opencitations.net/index/api/v2
   - Rate Limits: Generous
   - No authentication required

3. **DataCite Event Data** - https://api.datacite.org/events
   - Rate Limits: Generous
   - No authentication required

4. **Zenodo** - https://zenodo.org/api
   - Rate Limits: Generous
   - No authentication required

5. **GitHub** - https://api.github.com
   - Rate Limits: 60 req/hour (anonymous), 5000 req/hour (authenticated)
   - Optional: Set `GITHUB_TOKEN` env var for higher limits

### Network Requirements
- Internet connection required
- Tests will fail if external services are down
- GitHub tests may fail due to rate limits (run less frequently)

## CI/CD Considerations

### Default CI Workflow
Run only unit tests (fast, no external dependencies):
```yaml
- name: Run tests
  run: tox
```

### Optional Integration Tests in CI
Run integration tests separately (slower, requires network):
```yaml
- name: Run integration tests
  run: tox -e integration
  continue-on-error: true  # Don't fail build if external API is down
```

### GitHub Actions Rate Limits
If running GitHub integration tests in CI, consider:
```yaml
- name: Run integration tests
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: tox -e integration
```

## Test Expectations

### Expected Results
- **Unit tests**: Should always pass (deterministic, mocked)
- **Integration tests**: May occasionally fail due to:
  - Network connectivity issues
  - External API downtime
  - Rate limiting (especially GitHub)
  - Data coverage (e.g., DataCite may have no citations for some DOIs)

### Acceptable Failures
Some integration tests are designed to handle empty results gracefully:
- DANDI DataCite test may find 0 citations (Event Data coverage incomplete)
- GitHub mapper may fail if rate limited
- Any test may fail if external service is temporarily down

These are not test failures - they validate graceful degradation.

## Debugging Integration Tests

### Verbose Output
```bash
pytest tests/test_integration.py -v -s
```

The `-s` flag shows print statements with API call progress.

### Run Single Test
```bash
pytest tests/test_integration.py::test_repronim_collection_with_expansion -v -s
```

### Check API Responses
Tests print results to stdout:
```
Expanding Zenodo concept 808846 (live API call)...
Expanded to 26 DOI references
  - 10.5281/zenodo.808846
  - 10.5281/zenodo.18281145
  ...
```

### Network Troubleshooting
```bash
# Check if APIs are reachable
curl https://api.crossref.org/works/10.1002/hbm.25351
curl https://zenodo.org/api/records/808846
curl https://api.github.com/repos/datalad/datalad
```

## Adding New Integration Tests

### Template
```python
@pytest.mark.integration
@pytest.mark.slow
def test_my_integration() -> None:
    """
    Integration test: Brief description.

    Expected behavior:
    - What should happen
    - What APIs are called
    - Acceptable failure modes
    """
    # Test implementation
    # Make real API calls
    # Verify results (allow graceful failures)
```

### Best Practices
1. Mark with `@pytest.mark.integration` and `@pytest.mark.slow`
2. Document expected behavior and acceptable failures
3. Print progress information for debugging
4. Handle network/API errors gracefully
5. Don't assert exact counts (external data changes)
6. Assert structural correctness instead

## Performance Benchmarks

Typical run times on good network connection:

| Test | Duration | API Calls |
|------|----------|-----------|
| Unit tests (32) | ~0.2s | 0 |
| ReproNim expansion | ~6s | ~30 |
| DANDI DataCite | ~2s | ~3 |
| Zenodo expansion | ~2s | 2 |
| GitHub mapping | ~1s | 1-3 |
| Full workflow | ~8s | ~35 |
| **All integration (6)** | **~20s** | **~75** |

Total: Unit (0.2s) + Integration (20s) = **~20s for all 38 tests**
