# TODO: LLM Integration - Production Readiness

## Overview

The LLM-based citation classification system is currently implemented with:
- ✅ Working code (LLM backends, context extraction, git-annex)
- ✅ Ad-hoc scripts for testing (`scripts/test_*.py`)
- ✅ Bash workflow scripts (`scripts/run-dandi-bib-workflow.sh`)
- ✅ Makefile for automation
- ⚠️ Partial CLI integration (`extract-contexts` implemented)
- ❌ Missing `classify` CLI command
- ❌ Missing comprehensive tests

**Goal**: Migrate from ad-hoc scripts to proper Python CLI commands with full test coverage.

---

## Phase 1: Complete CLI Integration (High Priority)

### 1.1 Implement `classify` Command

**Current state**: Classification works via direct Python imports in test scripts

**Needed**: Proper CLI command in `src/citations_collector/cli.py`

```python
@main.command()
@click.argument("collection", type=click.Path(exists=True, path_type=Path))
@click.option("--backend", type=click.Choice(["ollama", "dartmouth", "openrouter", "openai"]))
@click.option("--model", help="Model name (e.g., qwen2:7b)")
@click.option("--confidence-threshold", type=float, default=0.7)
@click.option("--review/--no-review", default=False)
@click.option("--dry-run", is_flag=True)
def classify(collection, backend, model, confidence_threshold, review, dry_run):
    """Classify citation relationships using LLM."""
    # Load collection config
    # Load TSV with extracted contexts
    # Create LLM backend
    # Classify each citation
    # Update TSV with results
    # Interactive review if --review
    pass
```

**Implementation tasks**:
- [ ] Create `Classifier` class in `src/citations_collector/classifier.py`
- [ ] Integrate with `extract-contexts` output (read `extracted_citations.json`)
- [ ] Update TSV with classification results
- [ ] Add interactive review mode (prompt user for low-confidence)
- [ ] Add progress bar (tqdm)
- [ ] Add batch processing for efficiency
- [ ] Handle missing contexts gracefully

**Files to create/modify**:
- `src/citations_collector/classifier.py` (new)
- `src/citations_collector/cli.py` (add command)

**Tests needed**:
- `tests/test_classifier.py` (new)
- Mock LLM responses
- Test batch processing
- Test TSV updates
- Test interactive review

### 1.2 Improve `extract-contexts` Command

**Current state**: Basic implementation exists but not fully tested

**Improvements needed**:
- [ ] Add progress bar for PDF processing
- [ ] Better error handling for corrupt PDFs
- [ ] Support for resuming interrupted extractions
- [ ] Parallel processing option for large batches
- [ ] Better logging

**Files to modify**:
- `src/citations_collector/cli.py` (enhance command)
- `src/citations_collector/context_extractor.py` (add features)

### 1.3 Add `test-llm` Diagnostic Command

**Purpose**: Replace `scripts/test_ollama_connection.py` with proper CLI command

```python
@main.command()
@click.option("--backend", type=click.Choice(["ollama", "dartmouth", "openrouter", "openai"]))
@click.option("--model", help="Model to test")
def test_llm(backend, model):
    """Test LLM backend connection and classification."""
    # Test connection
    # Run sample classification
    # Report performance metrics
    pass
```

---

## Phase 2: Proper Testing (High Priority)

### 2.1 Unit Tests

**Missing tests for new modules**:
- [ ] `tests/test_llm_backends.py` - Test all LLM backends with mocked APIs
  - Mock Ollama API responses
  - Mock OpenAI/Dartmouth API responses
  - Test error handling
  - Test JSON parsing
  - Test confidence scoring

- [ ] `tests/test_context_extractor.py` - Test context extraction
  - Mock pdfplumber
  - Mock BeautifulSoup
  - Test pattern matching
  - Test paragraph extraction
  - Test deduplication

- [ ] `tests/test_classifier.py` - Test classification pipeline
  - Mock LLM backend
  - Test batch processing
  - Test TSV updates
  - Test confidence filtering

- [ ] `tests/test_git_annex.py` - Test git-annex integration
  - Mock git-annex commands
  - Test metadata tagging
  - Test OA status handling

### 2.2 Integration Tests

- [ ] `tests/integration/test_full_workflow.py`
  - Discover → Fetch → Extract → Classify (end-to-end)
  - Use small test collection (2-3 dandisets)
  - Mock external APIs (CrossRef, Unpaywall, Ollama)

### 2.3 CLI Tests

- [ ] `tests/test_cli.py` - Add tests for new commands
  - Test `extract-contexts` command
  - Test `classify` command (when implemented)
  - Test `test-llm` command (when implemented)
  - Test error handling
  - Test dry-run modes

### 2.4 Test Coverage Goals

- Overall: 80%+ coverage
- New modules (llm/, context_extractor.py): 90%+ coverage
- CLI commands: 85%+ coverage

---

## Phase 3: Refactoring & Code Quality (Medium Priority)

### 3.1 Move Test Scripts to Proper Tests

**Current ad-hoc scripts** → **Proper pytest tests**:

| Script | Migrate to |
|--------|-----------|
| `scripts/test_ollama_connection.py` | `tests/test_llm_backends.py` + CLI command |
| `scripts/test_llm_backends.py` | `tests/test_llm_backends.py` |
| `scripts/test_context_extraction.py` | `tests/test_context_extractor.py` |

**After migration**:
- [ ] Delete ad-hoc scripts or move to `scripts/dev/` (dev utilities only)
- [ ] Update documentation to reference proper tests

### 3.2 Refactor Bash Scripts

**Current bash scripts** → **Python CLI commands**:

| Script | Migrate to |
|--------|-----------|
| `scripts/run-dandi-bib-workflow.sh` | Not needed - Makefile is sufficient |
| `scripts/setup-dandi-bib.sh` | Keep for now (project scaffolding) |
| `scripts/setup-ollama-tunnel.sh` | Keep (SSH tunnel setup is bash-appropriate) |

**Decision**: Bash scripts for infrastructure setup are OK, but Python CLI for data processing.

### 3.3 Configuration Validation

- [ ] Add Pydantic validators for LLM config in `schema/citations.yaml`
- [ ] Validate backend/model combinations
- [ ] Clear error messages for missing API keys
- [ ] Validate confidence thresholds (0.0-1.0)

### 3.4 Type Annotations

- [ ] Add full type hints to all new modules
- [ ] Run mypy on new code
- [ ] Fix any type errors

---

## Phase 4: Documentation (Medium Priority)

### 4.1 User Documentation

- [ ] Update main README with LLM classification examples
- [ ] Add tutorial: "Classifying Citations in 5 Minutes"
- [ ] Add API reference for LLM backends
- [ ] Document all CLI commands in sphinx/mkdocs

### 4.2 Developer Documentation

- [ ] Architecture diagram for LLM system
- [ ] Contributing guide for adding new LLM backends
- [ ] Adding new citation relationship types
- [ ] Extending pattern matching for new repositories

### 4.3 Examples

- [ ] Add example notebooks (Jupyter) showing:
  - Basic classification workflow
  - Custom LLM backend implementation
  - Analyzing classification results
  - Multi-dataset citation analysis

---

## Phase 5: Performance & Optimization (Low Priority)

### 5.1 Performance Improvements

- [ ] Batch LLM requests (multiple citations per API call)
- [ ] Cache LLM responses (avoid re-classifying same contexts)
- [ ] Parallel PDF processing
- [ ] Incremental extraction (only new/changed PDFs)

### 5.2 Rate Limiting

- [ ] Add configurable rate limits for LLM APIs
- [ ] Exponential backoff for API errors
- [ ] Track API usage/costs

### 5.3 Resume Support

- [ ] Save partial results during classification
- [ ] Resume from last checkpoint on failure
- [ ] Lock files to prevent concurrent runs

---

## Phase 6: Advanced Features (Future)

### 6.1 Active Learning

- [ ] Track curator corrections
- [ ] Fine-tune LLM on feedback
- [ ] Improve classification over time

### 6.2 Multi-modal Classification

- [ ] Extract context from figures/tables
- [ ] Use vision models for image analysis
- [ ] Combine text + visual context

### 6.3 Explainability

- [ ] Highlight which context snippet was most influential
- [ ] Show confidence breakdown by context
- [ ] Generate human-readable explanations

### 6.4 Integration with External Tools

- [ ] NeuroD3 export format
- [ ] find_reuse cross-validation
- [ ] DataCite metadata enrichment

---

## Migration Checklist

### Immediate (This Week)

- [ ] Implement `classify` CLI command
- [ ] Write basic tests for LLM backends (mock APIs)
- [ ] Write basic tests for context extractor
- [ ] Run tox and ensure all tests pass
- [ ] Update main README with new features

### Short-term (This Month)

- [ ] Complete test coverage (80%+)
- [ ] Add `test-llm` diagnostic command
- [ ] Refactor ad-hoc test scripts into proper tests
- [ ] Add type hints to all new code
- [ ] Write user tutorial/guide

### Medium-term (This Quarter)

- [ ] Performance optimization (batching, caching)
- [ ] Advanced error handling and recovery
- [ ] Integration tests with real APIs (optional)
- [ ] Comprehensive documentation

---

## Code Quality Standards

**Before considering "production ready":**
- ✅ All CLI commands implemented
- ✅ 80%+ test coverage
- ✅ All tests passing (pytest + tox)
- ✅ Type hints + mypy passing
- ✅ Linting (ruff) passing
- ✅ Documentation complete
- ✅ Example workflows documented
- ✅ No ad-hoc scripts in critical path

---

## Current vs Target Architecture

### Current (Working but Ad-hoc)

```
User → Makefile → Bash scripts → Python test scripts → LLM
                                                      → Context extractor
                                                      → Classifier (direct import)
```

### Target (Production)

```
User → CLI commands (Python) → Classifier class → LLM backend (factory)
                             → Context extractor
                             → TSV persistence
                             → Git-annex
                                 ↓
                            Full test coverage
                            Type-checked
                            Documented
```

---

## Files to Delete After Migration

**Once proper CLI/tests are done:**
- `scripts/test_ollama_connection.py` → migrate to tests + CLI
- `scripts/test_llm_backends.py` → migrate to tests
- `scripts/test_context_extraction.py` → migrate to tests
- `scripts/run-dandi-bib-workflow.sh` → Makefile is sufficient (or keep as example)

**Keep:**
- `scripts/setup-dandi-bib.sh` - useful scaffolding tool
- `scripts/setup-ollama-tunnel.sh` - infrastructure helper
- `Makefile` - convenience wrapper

---

## Success Criteria

**Phase 1 Complete** when:
- `citations-collector classify` command works end-to-end
- `citations-collector test-llm` provides diagnostics
- All new commands have tests

**Phase 2 Complete** when:
- 80%+ test coverage
- All tests pass in CI
- No ad-hoc scripts in workflow

**Production Ready** when:
- All phases 1-3 complete
- Documentation complete
- Deployed to dandi-bib successfully
- Used for ≥100 citations without issues

---

## Priority Summary

**P0 (Blocker)**: Implement `classify` CLI command
**P1 (High)**: Add proper tests (80% coverage)
**P2 (Medium)**: Refactor ad-hoc scripts, documentation
**P3 (Low)**: Performance optimization, advanced features

---

## Tracking

- **Created**: 2026-02-01
- **Status**: Planning
- **Owner**: TBD
- **Target**: Q1 2026 for phases 1-2

---

## Notes

- Keep working proof-of-concept scripts in `scripts/dev/` or `scripts/examples/`
- Makefile is acceptable as convenience wrapper (not all users want pure CLI)
- Bash scripts for infrastructure setup (SSH tunnels, etc.) are OK
- Focus on Python for data processing logic
