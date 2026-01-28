# citations-collector

Discover and curate scholarly citations of datasets and software.

## Features

- **Citation Discovery**: Query CrossRef, OpenCitations, DataCite for citing papers
- **Hierarchical Collections**: Organize citations by project/version (e.g., DANDI dandisets)
- **Git-Friendly**: YAML collections + TSV citation records for version control
- **Curation Workflow**: Mark citations as ignored, merge preprints with published versions
- **PDF Acquisition**: Automatically download open-access PDFs via Unpaywall with optional git-annex tracking
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

# Source items to track
source:
  items:
    - item_id: dandi-000055
      name: "AJILE12: Long-term naturalistic human intracranial neural recordings"
      flavors:
        - flavor_id: "0.220113.0400"
          refs:
            - ref_type: doi
              ref_value: "10.48324/dandi.000055/0.220113.0400"

# Citation discovery settings
discover:
  sources:
    - crossref
    - opencitations
  email: your@email.org  # For CrossRef polite pool
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

## Examples

See the `examples/` directory for:
- **dandi-collection.yaml**: DANDI Archive dandisets with versioned DOIs
- **repronim-tools.yaml**: ReproNim neuroimaging tools with RRIDs
- **simple-resources.yaml**: Basic collection without versioning
- **citations-example.tsv**: Example citation records with curation

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
  - `discovery/`: Citation API clients (CrossRef, OpenCitations, DataCite)
  - `persistence/`: YAML/TSV I/O
  - `importers/`: DANDI API, Zenodo, GitHub integrations
  - `unpaywall.py`: Unpaywall API client for OA PDF URLs
  - `pdf.py`: PDF acquisition with git-annex support
  - `merge_detection.py`: Preprint/published version detection
  - `zotero_sync.py`: Zotero hierarchical sync with merged item handling
  - `core.py`: Main orchestration API
  - `cli.py`: Click-based CLI (thin wrapper)

## Citation Sources

- **CrossRef**: Most comprehensive, best for DOI citations
- **OpenCitations**: Open index, may lag behind CrossRef
- **DataCite**: Good for dataset citations
- **Europe PMC**: PubMed-indexed papers (future)
- **Semantic Scholar**: AI-powered citation discovery (future)

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
