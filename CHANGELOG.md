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
