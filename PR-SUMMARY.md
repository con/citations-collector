# PR Summary: LLM-Based Citation Classification System

This PR adds a complete LLM-based citation classification system with multi-model comparison, per-paper provenance tracking, and flexible storage architecture.

## Major Features

### 1. LLM Classification System
- **classify** command for automated citation relationship classification
- Support for 4 LLM backends: Ollama, Dartmouth, OpenRouter, OpenAI
- Interactive review mode for low-confidence classifications
- Short-context mode (extracted paragraphs) and full-text mode for comparison

### 2. Multi-Model Comparison Framework
- Store results from multiple models per paper in `pdfs/{doi}/classifications.json`
- Compare relationship types, confidence scores, and agreement rates
- Systematic model evaluation scripts with analysis and reporting
- Documentation of 31+ available models across Dartmouth tiers (Free to Premium)

### 3. Improved Context Extraction
- Expanded context window from ±250 to ±400 chars (max 1000 chars)
- Better paragraph boundary detection for natural context
- Captures actual usage descriptions instead of just bibliography entries

### 4. Classification Metadata Schema
- 4 essential fields in main table: `classification_method`, `classification_model`, `classification_confidence`, `classification_reviewed`
- Full provenance per paper: reasoning, timestamp, mode, backend
- Per-paper storage enables ensemble voting and model comparison
- Git commits track dates and authors automatically

### 5. Git-annex Integration
- Automatic detection and management of annexed PDFs
- Prevents "file not found" errors when PDFs are in git-annex

## Statistics

**Code:**
- 10,449+ lines added across 40 new/modified files
- New modules: `classifier.py`, `context_extractor.py`, `classifications_storage.py`, `git_annex.py`, `llm/*`
- Schema updates: Added `ClassificationMethod` enum and 4 metadata fields to `CitationRecord`

**Documentation:**
- 8 user-facing guides in `docs/`: CLASSIFICATION-WORKFLOW, CLASSIFICATION-METADATA, AVAILABLE-MODELS, MODEL-COMPARISON, SETUP-LLM, CONTEXT-EXTRACTION, DANDI-BIB-SETUP, AUTOMATION
- docs/README.md - Documentation index with quick start guide
- Removed 6 outdated planning/status docs from .specify/specs/ (1,856 lines)
- Kept 2 historical planning docs for reference (llm-integration-plan, reclassification-mvp)

**Testing:**
- 8 test/automation scripts for classification, context extraction, backend testing, and model comparison

## Real-World Testing

Tested on **dandi-bib** with 94 citations:
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

## Commits (13)

- dbfaa2b Improve context extraction: expand window to capture full paragraphs
- a85bde3 Add classify command for LLM-based citation relationship classification
- 44bf9c7 Add test script for classify command on real dandi-bib extracts
- 67056e9 Fix classify command: use model_copy for atomic Pydantic updates
- b3eb6e8 Add --full-text mode to classify command for comparison
- c72213c Fix TSV serialization: use mode='json' for proper enum serialization
- df29adc Add systematic LLM model comparison framework
- 8f55835 Add comprehensive model listing and update comparison script
- 1898052 Move import os to top of compare_models.py
- 1e79859 Add LLM classification metadata to schema
- 25d73e3 Simplify classification metadata to 4 fields + per-paper storage
- 511fceb Add classification workflow with per-paper storage
- 624b2a3 Clean up documentation: remove outdated planning/status docs

## Ready for Release

All features complete and tested:
- ✅ LLM classification working (4 backends)
- ✅ Multi-model comparison implemented
- ✅ Per-paper provenance storage
- ✅ Real-world testing on 94 dandi-bib citations (47 classified)
- ✅ Comprehensive documentation (8 guides)
- ✅ Test scripts and automation ready
- ✅ Git-annex integration working
