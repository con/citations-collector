# Documentation Overview

## Quick Start

1. **[SETUP-LLM.md](SETUP-LLM.md)** - Set up LLM backends (Ollama, Dartmouth, OpenRouter, OpenAI)
2. **[CLASSIFICATION-WORKFLOW.md](CLASSIFICATION-WORKFLOW.md)** - Complete workflow from extraction to classification
3. **[DANDI-BIB-SETUP.md](DANDI-BIB-SETUP.md)** - Apply to DANDI Archive citations (complete example)

## Reference Guides

### Core Functionality
- **[CLASSIFICATION-METADATA.md](CLASSIFICATION-METADATA.md)** - Schema, architecture, and metadata fields
- **[CONTEXT-EXTRACTION.md](CONTEXT-EXTRACTION.md)** - How context extraction works from PDFs/HTMLs
- **[AVAILABLE-MODELS.md](AVAILABLE-MODELS.md)** - Catalog of 31+ available models across Dartmouth tiers

### Advanced Topics
- **[MODEL-COMPARISON.md](MODEL-COMPARISON.md)** - Compare multiple models for quality assessment
- **[AUTOMATION.md](AUTOMATION.md)** - Set up automated scheduled runs with cron/systemd

## Typical Workflow

```bash
# 1. Set up LLM backend (see SETUP-LLM.md)
source /path/to/secrets
# or: ssh -L 11434:localhost:11434 server -N

# 2. Extract contexts from PDFs
citations-collector extract-contexts collection.yaml

# 3. Classify with LLM
citations-collector classify collection.yaml \
  --backend dartmouth \
  --model google.gemma-3-27b-it \
  --confidence-threshold 0.7

# 4. (Optional) Compare multiple models
python scripts/compare_models.py collection.yaml
python scripts/analyze_model_comparison.py
```

## Getting Help

- Check the relevant guide above for your use case
- For DANDI Archive specifically: see **DANDI-BIB-SETUP.md**
- For planning documents: see `.specify/specs/` directory
