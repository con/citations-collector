# DANDI-BIB Setup Guide

Complete guide for applying the LLM-based citation classification system to DANDI Archive citations.

## Quick Start

### 1. Create DANDI-BIB Project

```bash
cd /home/yoh/proj/dandi/citations-collector-enh-zotero
./scripts/setup-dandi-bib.sh /home/yoh/proj/dandi/dandi-bib
```

This creates a complete project structure at `/home/yoh/proj/dandi/dandi-bib/`:

```
dandi-bib/
├── collection.yaml              # Configuration
├── Makefile                     # Workflow automation
├── README.md                    # Project documentation
├── .gitignore                   # Git ignore rules
├── citations/
│   ├── data/
│   │   └── dandi-citations.tsv  # Main output (created)
│   └── pdfs/
│       └── {DOI}/
│           ├── article.pdf      # Downloaded PDFs (created)
│           ├── article.bib      # BibTeX metadata (created)
│           └── extracted_citations.json  # Contexts (created)
└── logs/
    └── workflow-*.log           # Workflow logs (created)
```

### 2. Start Ollama SSH Tunnel

**In a separate terminal** (keep running):

```bash
ssh -L 0.0.0.0:11434:localhost:11434 typhon -N
```

**Verify connection**:
```bash
uv run scripts/test_ollama_connection.py
```

### 3. Run Complete Workflow

```bash
cd /home/yoh/proj/dandi/dandi-bib
make all
```

This will:
1. **Discover** citations from CrossRef, OpenCitations, DataCite (~30-60 min)
2. **Fetch** PDFs via Unpaywall (~2-4 hours for 500 papers)
3. **Extract** dataset mentions from PDFs (~30-60 min)
4. **Classify** relationship types with LLM (~30-60 min for 1000 citations)

---

## What Gets Created

### Configuration File

**`collection.yaml`** - Complete configuration:

```yaml
name: DANDI Citations (Full Archive)
output_tsv: citations/data/dandi-citations.tsv

source:
  type: dandi              # Import from DANDI API
  include_draft: false

discover:
  sources: [crossref, opencitations, datacite]
  email: team@dandiarchive.org

pdfs:
  output_dir: citations/pdfs/
  git_annex: true

llm:
  backend: ollama
  model: qwen2:7b

classify:
  confidence_threshold: 0.7

zotero:
  group_id: 5774211
  collection_key: UHK47FKX
```

### Makefile Workflow

**`Makefile`** - Automation targets:

```bash
make help              # Show all targets
make all               # Run full workflow
make discover          # Find citations
make fetch-pdfs        # Download PDFs
make extract-contexts  # Extract dataset mentions
make classify          # Classify with LLM
make classify-review   # Interactive review
make sync-zotero       # Sync to Zotero
make stats             # Show statistics
make clean             # Remove generated files
```

### Workflow Script

**`scripts/run-dandi-bib-workflow.sh`** - Automated workflow for cron/systemd:

```bash
# Run manually
./scripts/run-dandi-bib-workflow.sh /home/yoh/proj/dandi/dandi-bib

# Skip steps
SKIP_DISCOVER=1 SKIP_PDFS=1 ./scripts/run-dandi-bib-workflow.sh

# Dry run
DRY_RUN=1 ./scripts/run-dandi-bib-workflow.sh

# Enable Zotero sync
SYNC_ZOTERO=1 ./scripts/run-dandi-bib-workflow.sh
```

---

## Individual Workflow Steps

### Step 1: Discover Citations

```bash
make discover
```

**What it does**:
- Queries CrossRef, OpenCitations, DataCite APIs
- Finds papers citing DANDI datasets
- Saves to `citations/data/dandi-citations.tsv`

**Output**:
```tsv
item_id	citation_doi	citation_title	citation_journal	citation_year	citation_relationship	citation_source
dandi:000003	10.1038/s41593-024-12345	Advanced spike sorting...	Nature Neuroscience	2024	Cites	crossref
dandi:000003	10.1101/2024.01.15.575901	Novel analysis methods...	bioRxiv	2024	Cites	crossref
```

### Step 2: Fetch PDFs

```bash
make fetch-pdfs
```

**What it does**:
- Queries Unpaywall API for open access PDFs
- Downloads PDFs to `citations/pdfs/{DOI}/article.pdf`
- Fetches BibTeX metadata
- Tracks OA status (gold/green/hybrid/closed)

**Directory structure**:
```
citations/pdfs/
├── 10.1038/
│   └── s41593-024-12345/
│       ├── article.pdf
│       └── article.bib
├── 10.1101/
│   └── 2024.01.15.575901/
│       ├── article.pdf
│       └── article.bib
```

### Step 3: Extract Contexts

```bash
make extract-contexts
```

**What it does**:
- Opens each PDF/HTML
- Finds dataset mentions (e.g., "DANDI:000003")
- Extracts paragraph-level contexts
- Saves as `extracted_citations.json` per paper
- Adds to git-annex with OA metadata

**Output (`extracted_citations.json`)**:
```json
{
  "paper_doi": "10.1038/s41593-024-12345",
  "paper_title": "Advanced spike sorting...",
  "oa_status": "gold",
  "citations": [
    {
      "dataset_id": "dandi:000003",
      "dataset_mentions": [
        {
          "context": "We analyzed neural recordings from DANDI:000003...",
          "page": 3,
          "source": "pdf"
        }
      ]
    }
  ]
}
```

### Step 4: Classify Citations

```bash
make classify
```

**What it does**:
- Loads extracted contexts
- Sends to LLM (Ollama/Dartmouth)
- Classifies relationship type
- Updates TSV with classifications

**LLM prompt includes**:
- Paper metadata (title, journal, year)
- All contexts where dataset mentioned
- 8 relationship type options (Uses, IsDocumentedBy, etc.)

**Output** (updated TSV):
```tsv
item_id	citation_doi	citation_relationship	citation_relationships
dandi:000003	10.1038/s41593-024-12345	Uses	Uses
dandi:000003	10.1101/2024.01.15.575901	IsDocumentedBy	IsDocumentedBy
dandi:000020	10.1038/s41592-024-56789	CitesAsEvidence	CitesAsEvidence
```

---

## Relationship Types

Based on CiTO ontology:

| Type | Description | Example |
|------|-------------|---------|
| **Uses** | Analyzes/processes data | "We analyzed recordings from DANDI:000003..." |
| **IsDocumentedBy** | Data descriptor paper | Journal="Scientific Data" |
| **CitesAsEvidence** | Method validation | "We validated on DANDI:000020..." |
| **Compiles** | Meta-analysis | "We combined DANDI:000003, 000020, 000055..." |
| **Reviews** | Critical evaluation | "We assessed quality of DANDI:000108..." |
| **CitesAsDataSource** | Explicit source | "Data from DANDI:000003..." |
| **CitesForInformation** | Background reference | "...such as DANDI:000003..." |
| **Cites** | Generic (fallback) | When unclear |

---

## Automation

### Cron Job (Weekly Updates)

Add to `crontab -e`:

```bash
# Run every Sunday at 2 AM
0 2 * * 0 /home/yoh/proj/dandi/citations-collector-enh-zotero/scripts/run-dandi-bib-workflow.sh /home/yoh/proj/dandi/dandi-bib >> /home/yoh/proj/dandi/dandi-bib/logs/cron.log 2>&1
```

### Systemd Timer

See [docs/AUTOMATION.md](docs/AUTOMATION.md) for systemd timer setup.

---

## Monitoring & Statistics

### View Statistics

```bash
cd /home/yoh/proj/dandi/dandi-bib
make stats
```

Output:
```
Total citations: 1523
Unique papers: 487
Unique datasets: 156

Relationship types:
    456 Uses
    189 IsDocumentedBy
    123 CitesAsEvidence
    ...

OA status:
    678 gold
    234 green
    ...
```

### View Logs

```bash
# Latest workflow log
tail -f /home/yoh/proj/dandi/dandi-bib/logs/workflow-*.log

# All logs
ls -lht /home/yoh/proj/dandi/dandi-bib/logs/
```

### Git-Annex Queries

```bash
cd /home/yoh/proj/dandi/dandi-bib

# Find gold OA papers
git annex find --metadata oa_status=gold

# Find distribution-restricted
git annex find --metadata tag=distribution-restricted

# View metadata
git annex metadata citations/pdfs/10.1038/.../extracted_citations.json
```

---

## Configuration Options

### Different LLM Backend

**Ollama (default)** - Free, local:
```yaml
llm:
  backend: ollama
  model: qwen2:7b
```

**Dartmouth** - Free, cloud:
```yaml
llm:
  backend: dartmouth
  model: anthropic.claude-sonnet-4-5-20250929
```

**OpenRouter** - Paid, fast:
```yaml
llm:
  backend: openrouter
  model: openai/gpt-4.1-nano
```

### Confidence Threshold

```yaml
classify:
  confidence_threshold: 0.7  # Auto-accept if > 0.7
  review_low_confidence: true  # Interactive review for < 0.7
```

### Git-Annex

```yaml
pdfs:
  git_annex: true  # Enable git-annex for PDFs and contexts
```

---

## File Locations

| File | Location | Description |
|------|----------|-------------|
| Collection config | `collection.yaml` | Main configuration |
| Citations TSV | `citations/data/dandi-citations.tsv` | All citations |
| PDFs | `citations/pdfs/{DOI}/article.pdf` | Downloaded PDFs |
| BibTeX | `citations/pdfs/{DOI}/article.bib` | Metadata |
| Contexts | `citations/pdfs/{DOI}/extracted_citations.json` | Dataset mentions |
| Logs | `logs/workflow-*.log` | Workflow logs |

---

## Troubleshooting

### Ollama Not Reachable

```bash
# Test connection
curl http://localhost:11434/api/version

# If fails, start tunnel:
ssh -L 0.0.0.0:11434:localhost:11434 typhon -N
```

### PDFs Not Downloading

**Most papers are closed access** (expected). Check:

```bash
# Count by OA status
awk -F'\t' '{print $9}' citations/data/dandi-citations.tsv | sort | uniq -c
```

Typically 30-50% are open access.

### Git-Annex Not Initialized

```bash
cd /home/yoh/proj/dandi/dandi-bib
git init
git annex init "dandi-bib-$(hostname)"
```

---

## Cost Analysis

**Ollama (Recommended)**:
- Cost: $0
- Setup: 5 min (SSH tunnel)
- Speed: ~3-5s per citation
- Total for 1000 citations: $0

**Dartmouth**:
- Cost: $0 (institutional)
- Setup: 2 min (get API token)
- Speed: ~2-4s per citation
- Total for 1000 citations: $0

**Both are FREE** - no API costs!

---

## Performance

**For ~500 DANDI datasets citing ~1000 papers:**

| Step | Time | Output |
|------|------|--------|
| Discover | 30-60 min | 1000 citations |
| Fetch PDFs | 2-4 hours | 300-500 PDFs (30-50% OA) |
| Extract | 30-60 min | 1000 contexts |
| Classify | 30-60 min | 1000 classifications |
| **Total** | **4-6 hours** | Complete workflow |

**Subsequent runs** (incremental):
- Discover: 5-10 min (only new citations)
- Fetch: 10-30 min (only new PDFs)
- Extract: 5-10 min (only new PDFs)
- Classify: 10-20 min (only new citations)
- **Total**: **30-60 min** for weekly update

---

## Next Steps

1. **Create dandi-bib project**:
   ```bash
   ./scripts/setup-dandi-bib.sh /home/yoh/proj/dandi/dandi-bib
   ```

2. **Start Ollama tunnel**:
   ```bash
   ssh -L 0.0.0.0:11434:localhost:11434 typhon -N
   ```

3. **Run workflow**:
   ```bash
   cd /home/yoh/proj/dandi/dandi-bib
   make all
   ```

4. **Set up automation** (optional):
   - See [docs/AUTOMATION.md](docs/AUTOMATION.md)

5. **Sync to Zotero** (optional):
   ```bash
   make sync-zotero
   ```

---

## Documentation

- **[Makefile](Makefile)** - All workflow targets
- **[SETUP-LLM.md](SETUP-LLM.md)** - LLM backend setup
- **[docs/CONTEXT-EXTRACTION.md](docs/CONTEXT-EXTRACTION.md)** - Context extraction guide
- **[docs/AUTOMATION.md](docs/AUTOMATION.md)** - Automation setup (cron/systemd)
- **[.specify/specs/IMPLEMENTATION-COMPLETE.md](.specify/specs/IMPLEMENTATION-COMPLETE.md)** - Implementation summary

---

## Support

**Common commands**:
```bash
make help              # Show all targets
make stats             # View statistics
make test-llm          # Test LLM connection
make test-extraction   # Test extraction
make clean             # Remove generated files
```

**Dry run mode**:
```bash
make extract-contexts-dry-run  # Preview without changes
DRY_RUN=1 make all             # Dry run full workflow
```

**Interactive classification**:
```bash
make classify-review   # Review low-confidence classifications
```

---

**Ready to start!** Run `./scripts/setup-dandi-bib.sh` to create the project.
