# 0.2.2 (Fri Jan 30 2026)

#### 🐛 Bug Fix

- Add auto-release automation [#1](https://github.com/con/citation-collector/pull/1) ([@yarikoptic](https://github.com/yarikoptic) [@yarikoptic-gitmate](https://github.com/yarikoptic-gitmate))

#### ⚠️ Pushed to `master`

- Add auto-release integration plan ([@yarikoptic](https://github.com/yarikoptic))
- Comment out sources in examples - default uses all available sources ([@yarikoptic](https://github.com/yarikoptic))
- Fix mypy type errors in DANDI and OpenAlex discoverers ([@yarikoptic](https://github.com/yarikoptic))
- Remove last_updated from Collection schema - derive from TSV instead ([@yarikoptic](https://github.com/yarikoptic))
- Add tox environment for updating example citations ([@yarikoptic](https://github.com/yarikoptic))
- Fix test: account for CrossRef metadata API call ([@yarikoptic](https://github.com/yarikoptic))
- Merge enh-zotero branch: Add OpenAlex support and multi-source tracking ([@yarikoptic](https://github.com/yarikoptic))
- Enable OpenAlex by default and fix example YAML structure ([@yarikoptic](https://github.com/yarikoptic))
- Fix OpenAlex discoverer to use OpenAlex IDs instead of DOIs in filter ([@yarikoptic](https://github.com/yarikoptic))
- Fix DataCite Event Data API query parameters ([@yarikoptic](https://github.com/yarikoptic))
- Add OpenAlex as a citation discovery source ([@yarikoptic](https://github.com/yarikoptic))
- Add multi-source citation tracking with coherence validation ([@yarikoptic](https://github.com/yarikoptic))
- Add CrossRef metadata coverage check and warnings ([@yarikoptic](https://github.com/yarikoptic))
- Add dynamic source population for DANDI dandisets ([@yarikoptic](https://github.com/yarikoptic))
- Add support for importing specific DANDI dandisets ([@yarikoptic](https://github.com/yarikoptic))
- Merge branch 'enh-zotero' into master ([@yarikoptic](https://github.com/yarikoptic))
- Add Zotero Related Items links between merged and published versions ([@yarikoptic](https://github.com/yarikoptic))
- Add tests for Zotero preprint vs journal article field mapping ([@yarikoptic](https://github.com/yarikoptic))
- Fix preprint field mapping in Zotero sync ([@yarikoptic](https://github.com/yarikoptic))
- Fix mypy type errors in merge_detection.py ([@yarikoptic](https://github.com/yarikoptic))
- Fix detect-merges CLI command configuration loading ([@yarikoptic](https://github.com/yarikoptic))
- Update documentation for PDF acquisition, merge detection, and Zotero sync ([@yarikoptic](https://github.com/yarikoptic))
- Handle previously-synced items transitioning to merged status ([@yarikoptic](https://github.com/yarikoptic))
- Add preprint/published version merge detection ([@yarikoptic](https://github.com/yarikoptic))
- Fix mypy type errors in CLI and Zotero sync ([@yarikoptic](https://github.com/yarikoptic))
- Dual-assign active citations to item + flavor Zotero collections ([@yarikoptic](https://github.com/yarikoptic))
- Use bare item ID for Zotero collection names, not item_name ([@yarikoptic](https://github.com/yarikoptic))
- Fix Zotero sync idempotency: recurse subcollections for existing items ([@yarikoptic](https://github.com/yarikoptic))
- Add Zotero sync, PDF acquisition, and unified YAML config ([@yarikoptic](https://github.com/yarikoptic))
- Add coverage reporting to py312 tox run ([@yarikoptic](https://github.com/yarikoptic))
- Fix CLI tests modifying simple.yaml fixture ([@yarikoptic](https://github.com/yarikoptic))
- Include datacite in default discovery sources ([@yarikoptic](https://github.com/yarikoptic))
- Stop tracking auto-generated _version.py ([@yarikoptic](https://github.com/yarikoptic))
- Fix typing issues across discovery and importer modules ([@yarikoptic](https://github.com/yarikoptic))
- rename dandi example collection ([@yarikoptic](https://github.com/yarikoptic))
- fixup and extend examples/dandi-collection.yaml ([@yarikoptic](https://github.com/yarikoptic))
- Add DANDI and Zotero importers with CLI commands ([@yarikoptic](https://github.com/yarikoptic))
- Sanitize metadata text and enhance DataCite discoverer ([@yarikoptic](https://github.com/yarikoptic))
- added one more sample dandiset for which there must be a citation ([@yarikoptic](https://github.com/yarikoptic))
- MAJOR FIX: Correct citation discovery - was backwards! ([@yarikoptic](https://github.com/yarikoptic))
- Fix API authentication and date filter bugs ([@yarikoptic](https://github.com/yarikoptic))
- Handle Zenodo API 403 errors gracefully in integration tests ([@yarikoptic](https://github.com/yarikoptic))
- Set up pre-commit with ruff and add usage documentation ([@yarikoptic](https://github.com/yarikoptic))
- Add integration tests with live external API calls ([@yarikoptic](https://github.com/yarikoptic))
- Phase 6 Part 2: Reference importers for non-DOI refs expansion ([@yarikoptic](https://github.com/yarikoptic))
- Phase 6 Part 1: Implement DataCite discoverer for DANDI citations ([@yarikoptic](https://github.com/yarikoptic))
- Phase 5: Validation & Assessment - All tox environments passing ([@yarikoptic](https://github.com/yarikoptic))
- Phase 4: Implement Click-based CLI ([@yarikoptic](https://github.com/yarikoptic))
- Phase 3: Implement core CitationCollector orchestration ([@yarikoptic](https://github.com/yarikoptic))
- Phase 2: Implement citation discovery APIs ([@yarikoptic](https://github.com/yarikoptic))
- Phase 1: Implement YAML/TSV persistence layer ([@yarikoptic](https://github.com/yarikoptic))
- Phase 0: Bootstrap project structure and build system ([@yarikoptic](https://github.com/yarikoptic))
- Add feature specification, LinkML schema, and examples ([@yarikoptic](https://github.com/yarikoptic))
- [DATALAD RUNCMD] yolo '/speckit.constitution A simple FO... ([@yarikoptic](https://github.com/yarikoptic))
- [DATALAD RUNCMD] specify init --ai claude --script sh --h... ([@yarikoptic](https://github.com/yarikoptic))
- [DATALAD] new dataset ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 2

- GitMate for @yarikoptic ([@yarikoptic-gitmate](https://github.com/yarikoptic-gitmate))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# CHANGELOG

This changelog is automatically generated using [auto](https://github.com/intuit/auto).

## 0.2.1 (Fri Jan 30 2026)

#### 🚀 Enhancement

- Add OpenAlex as a citation discovery source - Fourth discovery source for broader citation coverage
- Add dynamic source population for DANDI dandisets - Fetch items from DANDI API automatically
- Add multi-source citation tracking with coherence validation - Track which sources found each citation
- Add tox environment for updating example citations - Automated script to update all examples

#### 🐛 Bug Fix

- Fix DataCite Event Data API query parameters - Use correct relation type and DOI format
- Fix CrossRef metadata API call handling - Account for metadata checks in tests

#### 🏠 Internal

- Remove last_updated from Collection schema - Derive 'since' date from TSV instead, clean git history
- Comment out sources in examples - Default uses all available sources, clearer documentation
- Merge enh-zotero branch - OpenAlex support and multi-source tracking
- Fix mypy type errors in DANDI and OpenAlex discoverers

#### 📝 Documentation

- Add auto-release integration plan - Comprehensive guide for CI/CD automation

#### Authors: 1

- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

## 0.2.0 (Wed Jan 29 2026)

Initial tagged release with:

#### 🚀 Enhancement

- Zotero sync with merge detection - Sync citations to Zotero groups with preprint/published tracking
- PDF acquisition via Unpaywall - Automated PDF download with git-annex support
- DANDI and Zotero importers - Auto-generate collections from external sources
- Citation discovery from CrossRef, OpenCitations, and DataCite

#### 🏠 Internal

- Unified YAML configuration - Single source config for all features
- Coverage reporting in tox - 78% test coverage
- Comprehensive test suite - 101 tests across Python 3.10, 3.11, 3.12

#### Authors: 1

- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))
