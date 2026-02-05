# PR Summary: LLM-Based Citation Classification System

This PR adds a complete LLM-based citation classification system with multi-model comparison, per-paper provenance tracking, and flexible storage architecture.

## Core Library Additions

### Modules (src/citations_collector/)
- **classifier.py** - LLM-based citation classification engine
- **context_extractor.py** - Extract citation contexts from PDFs/HTMLs
- **classifications_storage.py** - Per-paper classification file management
- **git_annex.py** - Git-annex integration for annexed PDFs
- **llm/** - Multi-backend LLM framework (Ollama, Dartmouth, OpenRouter, OpenAI)

### CLI Commands (cli.py)
- **extract-contexts** - Extract citation contexts from PDFs/HTMLs
- **classify** - Classify citation relationships using LLM with interactive review mode

### Schema Changes (schema/citations.yaml)
- Added `ClassificationMethod` enum (manual, llm)
- Added 4 metadata fields: `classification_method`, `classification_model`, `classification_confidence`, `classification_reviewed`
- Per-paper storage format: `pdfs/{doi}/classifications.json` with full provenance

## Features

### 1. LLM Classification
- Support for 4 backends: Ollama, Dartmouth, OpenRouter, OpenAI
- Interactive review mode for low-confidence classifications
- Short-context mode (extracted paragraphs) and full-text mode

### 2. Per-Paper Provenance
- Store detailed results in `pdfs/{doi}/classifications.json`
- Full context: reasoning, timestamp, mode, backend
- Enables multi-model comparison and ensemble voting

### 3. Context Extraction
- Extract citation contexts from PDFs/HTMLs
- Expanded context window (±400 chars, max 1000) with paragraph boundary detection
- Store contexts in `pdfs/{doi}/extracted_citations.json`

### 4. Multi-Model Comparison
- Store results from multiple models per paper
- Compare relationship types, confidence scores, and agreement rates
- Scripts for systematic evaluation

### 5. Git-annex Support
- Automatic detection and management of annexed PDFs
- Prevents "file not found" errors in git-annex repositories

## Documentation (7 guides)

- **README.md** - Documentation index with quick start
- **CLASSIFICATION-WORKFLOW.md** - Complete workflow from extraction to classification
- **CLASSIFICATION-METADATA.md** - Schema, architecture, and metadata fields
- **SETUP-LLM.md** - Backend setup (Ollama, Dartmouth, OpenRouter, OpenAI)
- **AVAILABLE-MODELS.md** - Catalog of 31+ models across Dartmouth tiers
- **CONTEXT-EXTRACTION.md** - Technical details of context extraction
- **MODEL-COMPARISON.md** - Multi-model evaluation guide

## Example Scripts (7 tools)

- **test_classify.py** - Classification usage example
- **test_context_extraction.py** - Context extraction example
- **test_llm_backends.py** - Backend connectivity testing
- **test_ollama_connection.py** - Simple connectivity test
- **compare_models.py** - Multi-model comparison tool
- **analyze_model_comparison.py** - Comparison analysis tool
- **setup-ollama-tunnel.sh** - SSH tunnel helper for Ollama

## Real-World Testing

Tested on [dandi-bib](https://github.com/dandi/dandi-bib) (DANDI Archive citations):
- **47 citations classified** using google.gemma-3-27b-it via Dartmouth
- Relationship types: `IsDocumentedBy` (0.95), `Uses` (0.80-0.90), `CitesAsDataSource` (0.75), `CitesForInformation` (0.75)
- **Zero low-confidence results** (all ≥ 0.70 threshold)
- **Zero errors**

Example classification:
```json
{
  "relationship_type": "Uses",
  "confidence": 0.9,
  "reasoning": "The paper explicitly states that electrophysiological recordings were
               'obtained from' the Allen Institute Patch-seq dataset (Dandiset 000020).",
  "model": "google.gemma-3-27b-it",
  "timestamp": "2026-02-05T11:14:14.236553"
}
```

See [dandi-bib repository](https://github.com/dandi/dandi-bib) for operational workflows and automation.

## Usage Example

```bash
# Set up LLM backend
source /path/to/secrets  # or use SSH tunnel for Ollama

# Extract contexts from PDFs
citations-collector extract-contexts collection.yaml

# Classify with LLM
citations-collector classify collection.yaml \
  --backend dartmouth \
  --model google.gemma-3-27b-it \
  --confidence-threshold 0.7 \
  --review

# Compare multiple models
python scripts/compare_models.py collection.yaml
python scripts/analyze_model_comparison.py
```

## Architecture

**Two-level storage:**
1. **Main TSV** - 4 minimal metadata fields for quick filtering
2. **Per-paper JSON** - Full provenance for audit trail and model comparison

**Benefits:**
- Clean main table with only essential fields
- Multiple models stored together for comparison
- Ensemble voting and selection strategies supported
- Complete audit trail co-located with paper data

## Statistics

- **37 files changed**: 5,761 insertions, 377 deletions
- **Core library**: 5 new modules + LLM backend framework
- **CLI**: 2 new commands (extract-contexts, classify)
- **Schema**: ClassificationMethod enum + 4 metadata fields
- **Docs**: 7 focused guides
- **Scripts**: 7 example/test tools

## Ready for Release

- ✅ LLM classification working (4 backends)
- ✅ Multi-model comparison implemented
- ✅ Per-paper provenance storage
- ✅ Real-world testing (47 citations classified, 0 errors)
- ✅ Comprehensive documentation
- ✅ Example scripts and tools
- ✅ Git-annex integration
- ✅ Clean focused PR (removed 3,304 lines of dandi-bib specific code)
