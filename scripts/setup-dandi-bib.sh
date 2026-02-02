#!/bin/bash
# Setup script for applying citation classification to dandi-bib project
#
# Usage:
#   ./scripts/setup-dandi-bib.sh /path/to/dandi-bib

set -e

TARGET_DIR="${1:-/home/yoh/proj/dandi/dandi-bib}"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  DANDI-BIB Citation Classification Setup                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Target directory: $TARGET_DIR"
echo ""

# Create directory if it doesn't exist
if [ ! -d "$TARGET_DIR" ]; then
    echo "Creating directory: $TARGET_DIR"
    mkdir -p "$TARGET_DIR"
fi

cd "$TARGET_DIR"

# Create directory structure
echo "Setting up directory structure..."
mkdir -p citations/pdfs
mkdir -p citations/data
mkdir -p .git

# Create collection.yaml
if [ ! -f "collection.yaml" ]; then
    echo "Creating collection.yaml..."
    cat > collection.yaml <<'EOF'
name: DANDI Citations (Full Archive)
description: All citations for DANDI Archive dandisets
homepage: https://dandiarchive.org

output_tsv: citations/data/dandi-citations.tsv

source:
  type: dandi
  include_draft: false
  update_items: add  # Add new dandisets, keep existing

discover:
  sources: [crossref, opencitations, datacite]
  email: team@dandiarchive.org

pdfs:
  output_dir: citations/pdfs/
  unpaywall_email: team@dandiarchive.org
  git_annex: true

llm:
  backend: ollama
  model: qwen2:7b

classify:
  confidence_threshold: 0.7
  review_low_confidence: true

zotero:
  group_id: 5774211
  collection_key: UHK47FKX
  # api_key via ZOTERO_API_KEY envvar

# Items will be populated from DANDI API
# or can be manually specified:
# items:
#   - item_id: "dandi:000003"
#     item_flavor: "0.210812.1448"
EOF
    echo "✓ Created collection.yaml"
else
    echo "⊘ collection.yaml already exists (skipping)"
fi

# Create Makefile symlink
if [ ! -f "Makefile" ]; then
    echo "Creating Makefile..."
    cat > Makefile <<'EOF'
# Makefile for DANDI-BIB Citation Collection
# This uses the citations-collector tool

include $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))/../citations-collector-enh-zotero/Makefile

# Override defaults
COLLECTION = collection.yaml
OUTPUT_TSV = citations/data/dandi-citations.tsv
PDFS_DIR = citations/pdfs

.PHONY: init

init: ## Initialize dandi-bib with dandisets from API
	@echo "Fetching dandisets from DANDI API..."
	uv run citations-collector discover $(COLLECTION) --full-refresh
EOF
    echo "✓ Created Makefile"
else
    echo "⊘ Makefile already exists (skipping)"
fi

# Create .gitignore
if [ ! -f ".gitignore" ]; then
    echo "Creating .gitignore..."
    cat > .gitignore <<'EOF'
# Citation data
citations/data/*.tsv
citations/pdfs/

# Git-annex
.git/annex/

# Python
__pycache__/
*.pyc
.venv/
venv*/

# Secrets
.env
secrets
EOF
    echo "✓ Created .gitignore"
fi

# Create README
if [ ! -f "README.md" ]; then
    echo "Creating README.md..."
    cat > README.md <<'EOF'
# DANDI Citations Collection

Citation collection and classification for DANDI Archive datasets.

## Quick Start

### 1. Setup Environment

```bash
# Install citations-collector from parent directory
cd ../citations-collector-enh-zotero
make setup
```

### 2. Start Ollama SSH Tunnel (for LLM classification)

In a separate terminal:
```bash
ssh -L 0.0.0.0:11434:localhost:11434 typhon -N
```

### 3. Run Full Workflow

```bash
make all
```

This runs:
1. **discover** - Find citations for all DANDI datasets
2. **fetch-pdfs** - Download PDFs for citations
3. **extract-contexts** - Extract dataset mentions from PDFs
4. **classify** - Classify citations using LLM

## Individual Steps

### Discover Citations

```bash
make discover
```

Queries CrossRef, OpenCitations, and DataCite for papers citing DANDI datasets.

Output: `citations/data/dandi-citations.tsv`

### Fetch PDFs

```bash
make fetch-pdfs
```

Downloads PDFs via Unpaywall API (open access) or scraping.

Output: `citations/pdfs/{DOI}/article.pdf`

### Extract Contexts

```bash
make extract-contexts
```

Finds dataset mentions in PDFs and extracts paragraph-level contexts.

Output: `citations/pdfs/{DOI}/extracted_citations.json`

### Classify Citations

```bash
make classify
```

Uses LLM to classify citation relationship types:
- **Uses**: Paper analyzes data
- **IsDocumentedBy**: Data descriptor paper
- **CitesAsEvidence**: Method validation
- **Compiles**: Meta-analysis
- **Reviews**: Critical evaluation
- etc.

Updates: `citations/data/dandi-citations.tsv` with relationship types

### Sync to Zotero

```bash
make sync-zotero
```

Syncs classified citations to Zotero group library with hierarchical collections.

## Configuration

Edit `collection.yaml` to configure:
- Citation sources (CrossRef, OpenCitations, DataCite)
- PDF download settings
- LLM backend (Ollama, Dartmouth, OpenRouter)
- Zotero sync target

## Statistics

```bash
make stats
```

Shows citation counts, relationship type distribution, OA status, etc.

## Git-Annex

PDFs and extracted contexts are managed with git-annex:

```bash
# View metadata
git annex metadata citations/pdfs/10.1038/.../extracted_citations.json

# Find by OA status
git annex find --metadata oa_status=gold

# Find distribution-restricted
git annex find --metadata tag=distribution-restricted
```

## Directory Structure

```
dandi-bib/
├── collection.yaml                 # Configuration
├── Makefile                        # Workflow automation
├── citations/
│   ├── data/
│   │   └── dandi-citations.tsv    # Main output
│   └── pdfs/
│       └── {DOI}/
│           ├── article.pdf         # Downloaded PDF
│           ├── article.bib         # BibTeX metadata
│           └── extracted_citations.json  # Dataset mentions
```

## Help

```bash
make help
```
EOF
    echo "✓ Created README.md"
fi

# Initialize git-annex if git repo exists
if [ -d ".git" ] && command -v git-annex &> /dev/null; then
    if ! git annex version &> /dev/null 2>&1; then
        echo "Initializing git-annex..."
        git annex init "dandi-bib-$(hostname)"
        echo "✓ Initialized git-annex"
    else
        echo "⊘ git-annex already initialized"
    fi
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Setup Complete!                                               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo ""
echo "1. Start Ollama SSH tunnel (in separate terminal):"
echo "   ssh -L 0.0.0.0:11434:localhost:11434 typhon -N"
echo ""
echo "2. Run full workflow:"
echo "   cd $TARGET_DIR"
echo "   make all"
echo ""
echo "Or run individual steps:"
echo "   make discover       # Find citations"
echo "   make fetch-pdfs     # Download PDFs"
echo "   make extract-contexts  # Extract dataset mentions"
echo "   make classify       # Classify with LLM"
echo ""
echo "For help:"
echo "   make help"
echo ""
