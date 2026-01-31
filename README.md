# citations-collector

Discover and curate scholarly citations of datasets and software.

## Features

- **Multi-Source Citation Discovery**: Query CrossRef, OpenCitations, DataCite, and OpenAlex - automatically merges results from multiple sources
- **External Item Management**: Track items via BibTeX files or dynamically fetch from DANDI Archive API
- **Hierarchical Collections**: Organize citations by project/version (e.g., DANDI dandisets, dataset releases)
- **Git-Friendly**: YAML collections + TSV citation records for version control
- **Progress Monitoring**: Real-time progress bars with tqdm for long-running discovery tasks
- **Intelligent Retry Logic**: Respects rate limits with exponential backoff and Retry-After headers
- **PDF Acquisition**: Automatically download open-access PDFs via Unpaywall with intelligent HTML/PDF detection
- **Merge Detection**: Auto-detect preprints with published versions using CrossRef relationships
- **Zotero Integration**: Sync citations to hierarchical Zotero collections with automatic merged item relocation
- **Incremental Updates**: Efficiently discover only new citations since last run

## Installation

```bash
# Using uv (recommended)
uv venv
source .venv/bin/activate
uv pip install citations-collector

# Or using pip
pip install citations-collector
```

## Quick Start

### 1. Create a Collection

Create `collection.yaml`:

```yaml
name: My Research Tools
description: Software tools used in our lab
items:
  - item_id: my-tool
    name: "My Analysis Tool"
    flavors:
      - flavor_id: "1.0.0"
        refs:
          - ref_type: doi
            ref_value: "10.5281/zenodo.1234567"
```

### 2. Discover Citations

```bash
# Discover citations for all items in collection
citations-collector discover collection.yaml --output citations.tsv

# Use CrossRef polite pool (better rate limits)
citations-collector discover collection.yaml --email your@email.org
```

### 3. View Results

Citations are saved to `citations.tsv` - a tab-separated file you can open in Excel or edit manually for curation.

**TSV columns include**:
- Item identifiers (`item_id`, `item_flavor`, `item_ref_type`, `item_ref_value`)
- Citation metadata (`citation_doi`, `citation_title`, `citation_authors`, `citation_year`)
- `citation_sources`: Comma-separated list when found by multiple discoverers (e.g., "crossref, openalex")
- Curation fields (`citation_status`, `citation_comment`, `curated_by`)
- Open access tracking (`oa_status`, `pdf_url`, `pdf_path`)

## Source Types

### BibTeX Source

Maintain your items externally in BibTeX format and use citations-collector for discovery:

```yaml
name: DANDI Archive Dandisets
source:
  type: bibtex
  bibtex_file: ../dandi.bib  # Relative or absolute path
  bib_field: doi
  ref_type: doi
  ref_regex: '10\.48324/(?P<item_id>dandi\.\d{6})/(?P<flavor_id>[\d.]+)'
  # update_items omitted - items read from BibTeX, not saved to YAML

items: []  # Empty - populated from BibTeX file
```

The regex extracts `item_id` and `flavor_id` from the reference field. Perfect for maintaining items in existing bibliography managers!

### DANDI Source

Dynamically fetch dandiset metadata from DANDI Archive:

```yaml
source:
  type: dandi
  dandiset_ids:
    - '000402'  # MICrONS dataset
  include_draft: false  # Only published versions
```

Items and versions are automatically populated from the DANDI API - no manual YAML editing required!

## Advanced Workflows

### PDF Acquisition

Automatically download open-access PDFs using Unpaywall:

```bash
# Fetch PDFs for discovered citations
citations-collector fetch-pdfs --config collection.yaml

# Use git-annex for provenance tracking
citations-collector fetch-pdfs --config collection.yaml --git-annex

# Dry run to see what would be downloaded
citations-collector fetch-pdfs --config collection.yaml --dry-run
```

PDFs are stored at `pdfs/{doi}/article.pdf` with accompanying `article.bib` BibTeX files.

**Smart Features**:
- **Content-Type Detection**: Automatically detects when server returns HTML instead of PDF and saves with `.html` extension
- **Retry Logic**: Respects `Retry-After` headers and uses exponential backoff for rate-limited servers (bioRxiv, etc.)
- **Rate Limiting**: 2-second delay between downloads to avoid triggering bot detection
- **Skip Existing**: Won't re-download files that already exist (checks both `.pdf` and `.html` extensions)

### Merge Detection

Detect preprints that have published versions:

```bash
# Detect merges via CrossRef relationships
citations-collector detect-merges --config collection.yaml

# Also run fuzzy title matching (use with caution)
citations-collector detect-merges --config collection.yaml --fuzzy-match

# Preview without updating
citations-collector detect-merges --config collection.yaml --dry-run
```

Detected preprints are marked with `citation_status=merged` and `citation_merged_into={published_doi}`.

### Zotero Sync

Sync citations to Zotero for collaborative browsing:

```bash
# Sync to Zotero (requires API key in config or env)
citations-collector sync-zotero --config collection.yaml

# Dry run to preview structure
citations-collector sync-zotero --config collection.yaml --dry-run
```

Zotero hierarchy:
```
Top Collection/
  ├── {item_id}/
  │   ├── {flavor}/
  │   │   ├── <active citations>
  │   │   └── Merged/
  │   │       └── <preprints and old versions>
```

### Unified Configuration

Create a unified `collection.yaml` with all settings:

```yaml
name: My Research Collection
description: Tools and datasets from our lab

# Option 1: BibTeX source (external item management)
source:
  type: bibtex
  bibtex_file: ../my-items.bib
  bib_field: doi
  ref_type: doi
  ref_regex: '(?P<item_id>[\w.-]+)/(?P<flavor_id>[\d.]+)'

# Option 2: DANDI source (dynamic API fetch)
# source:
#   type: dandi
#   dandiset_ids: ['000055']
#   include_draft: false

# Option 3: Manual items
# items:
#   - item_id: my-tool
#     name: "My Analysis Tool"
#     flavors:
#       - flavor_id: "1.0.0"
#         refs:
#           - ref_type: doi
#             ref_value: "10.5281/zenodo.1234567"

# Citation discovery settings (uses all 4 sources by default)
discover:
  email: your@email.org  # For CrossRef/OpenAlex polite pool
  incremental: true

# PDF acquisition settings (optional)
pdfs:
  output_dir: pdfs/
  unpaywall_email: your@email.org
  git_annex: false

# Zotero sync settings (optional)
zotero:
  library_type: group
  library_id: "12345"
  api_key: "YOUR_API_KEY"  # Or set ZOTERO_API_KEY env var
  top_collection_key: "ABCD1234"
```

Then run the full workflow:

```bash
# 1. Discover citations
citations-collector discover collection.yaml

# 2. Fetch open-access PDFs
citations-collector fetch-pdfs --config collection.yaml

# 3. Detect merged preprints
citations-collector detect-merges --config collection.yaml

# 4. Sync to Zotero
citations-collector sync-zotero --config collection.yaml
```

## Library Usage

```python
from citations_collector import CitationCollector

# Load collection
collector = CitationCollector.from_yaml("collection.yaml")

# Discover citations (incremental by default)
collector.discover_all(incremental=True, email="your@email.org")

# Save results
collector.save("collection.yaml", "citations.tsv")
```

## Real-World Examples

See the `examples/` directory for production configurations:

### DANDI Archive (`dandi-collection.yaml`)
Tracks all 850+ DANDI dandisets via external BibTeX file maintained by `dandi-citations` tool. Items are extracted from versioned DOIs like `10.48324/dandi.000003/0.210812.1448` using regex parsing. Perfect example of external item management - the YAML stays clean while the BibTeX file is the source of truth.

**Key features**: BibTeX source, regex extraction, external maintenance

### MICrONS Dataset (`microns-collection.yaml`)
Machine Intelligence from Cortical Networks - a cubic millimeter of mouse visual cortex. Demonstrates **dynamic source fetching** from DANDI API for dandiset 000402, plus manually curated items for the Nature paper and BOSS database entry. Shows how to mix DANDI source with manual items.

**Key features**: DANDI API source, mixed item sources, multi-resource tracking

### StudyForrest (`studyforrest.yaml`)
High-resolution 7-Tesla fMRI dataset with complex naturalistic stimulation. Tracks 11 papers (dataset papers, analysis papers, protocols) all citing back to the main dataset. Real example of tracking a dataset with multiple associated publications.

**Key features**: Multiple papers for single dataset, manual item definition

### ReproNim Tools (`repronim-tools.yaml`)
Neuroimaging software tools tracked via RRIDs (Research Resource Identifiers), GitHub repos, Zenodo releases, and DOIs. Demonstrates tracking software across multiple identifier types and versions. **Over 2500 citations** discovered!

**Key features**: RRIDs, GitHub repos, Zenodo, multi-identifier tracking

### Simple Resources (`simple-resources.yaml`)
Basic example for getting started - minimal configuration without versioning complexities.

### Sample Collections
- **dandi-sample-collection.yaml**: Small subset of DANDI dandisets for testing
- **citations-example.tsv**: Curated citation records showing merge detection, status flags

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/dandi/citations-collector.git
cd citations-collector

# Setup development environment
uv venv
source .venv/bin/activate
uv pip install -e ".[devel]"
```

### Running Tests

```bash
# Run all tests, linting, and type checking
tox

# Run specific environment
tox -e py312      # Tests on Python 3.12
tox -e lint       # Ruff linting
tox -e type       # Mypy type checking
tox -e cov        # Coverage report
```

### Regenerating LinkML Models

When `schema/citations.yaml` changes:

```bash
# Install linkml tools
uv pip install -e ".[linkml]"

# Regenerate Pydantic models
gen-pydantic schema/citations.yaml > src/citations_collector/models/generated.py

# Regenerate JSON Schema
gen-json-schema schema/citations.yaml > schema/citations.schema.json

# Commit generated files
git add src/citations_collector/models/generated.py schema/citations.schema.json
git commit -m "Regenerate LinkML models"
```

## Architecture

- **Library-First Design**: All functionality accessible programmatically
- **LinkML Schema**: Validated data models from `schema/citations.yaml`
- **Modular Structure**:
  - `discovery/`: Citation API clients (CrossRef, OpenCitations, DataCite, OpenAlex)
  - `persistence/`: YAML/TSV I/O with multi-source support
  - `importers/`: DANDI API, BibTeX, Zenodo, GitHub integrations
  - `unpaywall.py`: Unpaywall API client for OA PDF URLs
  - `pdf.py`: PDF acquisition with retry logic, Retry-After support, and git-annex tracking
  - `merge_detection.py`: Preprint/published version detection
  - `zotero_sync.py`: Zotero hierarchical sync with merged item handling
  - `core.py`: Main orchestration API with progress bars
  - `cli.py`: Click-based CLI (thin wrapper)

**Recent Improvements**:
- Multi-source citation deduplication and tracking
- Retry logic with exponential backoff and Retry-After header support
- HTML vs PDF content detection for downloads
- Progress bars with real-time logging
- BibTeX import for external item management

## Citation Sources

All four sources are queried in parallel, and results are automatically deduplicated and merged:

- **CrossRef**: Most comprehensive, best for journal articles and conference papers
- **OpenCitations**: Open citation index, community-maintained
- **DataCite**: Specialized for dataset citations and research data
- **OpenAlex**: Broad academic coverage including preprints, with additional metadata

**Multi-Source Tracking**: When the same citation is found by multiple sources (e.g., both CrossRef and OpenAlex), it's stored as a single row in the TSV with `citation_sources: "crossref, openalex"`. This helps verify citation coverage and identify which sources are most useful for your domain.

**Future Sources**: Europe PMC (PubMed-indexed papers), Semantic Scholar (AI-powered discovery)

## License

MIT License - see LICENSE file for details.

## Contributing

See CONSTITUTION.md for:
- Code standards (Ruff, mypy, type hints)
- Testing requirements (pytest, 100 lines max, mock HTTP)
- Architecture principles (library-first, reliability, simplicity)

Pull requests welcome!

## Citation

If you use citations-collector in your research, please cite:

```bibtex
@software{citations_collector,
  title = {citations-collector: Discover and curate scholarly citations},
  author = {{DANDI Team}},
  url = {https://github.com/dandi/citations-collector},
  license = {MIT}
}
```
