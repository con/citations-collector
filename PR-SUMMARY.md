# PR Summary: LLM-Based Citation Classification System

This PR adds a complete LLM-based citation classification system with multi-model comparison, per-paper provenance tracking, and flexible storage architecture.

## Major Features

### 1. LLM Classification System
- **classify** command for automated citation relationship classification
- Support for 4 LLM backends: Ollama, Dartmouth, OpenRouter, OpenAI
- Interactive review mode for low-confidence classifications
- Short-context mode (extracted paragraphs) and full-text mode

### 2. Classification Metadata Schema
- 4 metadata fields: `classification_method`, `classification_model`, `classification_confidence`, `classification_reviewed`
- Per-paper storage in `pdfs/{doi}/classifications.json` with full provenance (reasoning, timestamp, mode, backend)
- Enables multi-model comparison and ensemble voting

### 3. Context Extraction
- **extract-contexts** command extracts citation contexts from PDFs/HTMLs
- Expanded context window (±400 chars, max 1000) with paragraph boundary detection
- Stores extracted contexts in `pdfs/{doi}/extracted_citations.json`

### 4. Multi-Model Comparison
- Store results from multiple models per paper
- Compare relationship types, confidence scores, and agreement rates
- Scripts for systematic model evaluation and analysis

### 5. Git-annex Integration
- Automatic detection and management of annexed PDFs
- Prevents "file not found" errors when working with git-annex repositories

## Statistics

**Code:**
- Core library modules: `classifier.py`, `context_extractor.py`, `classifications_storage.py`, `git_annex.py`, `llm/*` backends
- Schema updates: Added `ClassificationMethod` enum and 4 metadata fields to `CitationRecord`
- CLI commands: `extract-contexts`, `classify` with interactive review mode

**Documentation:**
- 7 user-facing guides in `docs/`: CLASSIFICATION-WORKFLOW, CLASSIFICATION-METADATA, AVAILABLE-MODELS, MODEL-COMPARISON, SETUP-LLM, CONTEXT-EXTRACTION, README
- Points to [dandi-bib](https://github.com/dandi/dandi-bib) for operational deployment example

**Testing:**
- 6 example/test scripts: backend connectivity, context extraction, classification, model comparison

## Real-World Testing

Tested on [dandi-bib](https://github.com/dandi/dandi-bib) (DANDI Archive citations):
- **47 citations classified** with actual LLM (google.gemma-3-27b-it via Dartmouth)
- Relationship types: `IsDocumentedBy` (0.95), `Uses` (0.80-0.90), `CitesAsDataSource` (0.75), `CitesForInformation` (0.75)
- **Zero low-confidence results** (all ≥ 0.70 threshold)
- **Zero errors**

Example real classification:
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

See [dandi-bib repository](https://github.com/dandi/dandi-bib) for operational workflows and automation setup.

## Usage

```bash
# Source API keys
source /home/yoh/proj/dandi/citations-collector/.git/secrets

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

## Architecture Highlights

**Two-level storage:**
1. **Main TSV** - 4 minimal metadata fields for quick filtering/queries
2. **Per-paper JSON** - Full details (reasoning, timestamp, mode) for audit trail

**Benefits:**
- Clean main table with only essential fields
- Multiple models stored together for comparison
- Ensemble voting and selection strategies supported
- Complete audit trail co-located with paper data
- Flexible: add new models without losing old results

## Key Commits

- dbfaa2b Improve context extraction: expand window to capture full paragraphs
- a85bde3 Add classify command for LLM-based classification
- df29adc Add systematic LLM model comparison framework
- 1e79859 Add LLM classification metadata to schema
- 25d73e3 Simplify classification metadata to 4 fields + per-paper storage
- 511fceb Add classification workflow with per-paper storage
- 624b2a3 Clean up documentation: remove outdated docs
- (current) Remove dandi-bib specific files - operational setup belongs in dandi-bib repo

## Ready for Release

All features complete and tested:
- ✅ LLM classification working (4 backends)
- ✅ Multi-model comparison implemented
- ✅ Per-paper provenance storage
- ✅ Real-world testing on 94 dandi-bib citations (47 classified)
- ✅ Comprehensive documentation (8 guides)
- ✅ Test scripts and automation ready
- ✅ Git-annex integration working
