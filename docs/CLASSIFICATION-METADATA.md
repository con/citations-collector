# Classification Metadata

## Overview

The schema now includes comprehensive metadata fields to track LLM classification provenance. This enables:

- **Reproducibility**: Track which model classified each relationship
- **Quality control**: Filter by confidence, identify classifications needing review
- **Model comparison**: Evaluate different models' performance over time
- **Audit trail**: Full provenance from classification through human review
- **Incremental updates**: Skip already-classified citations

## New Schema Fields

### `classification_method` (enum)
How the citation relationship was determined.

**Values:**
- `manual` - Manually classified by human curator
- `llm` - Classified by Large Language Model
- `rule` - Classified by automated rule/heuristic
- `imported` - Imported from external source with existing classification

### `classification_model` (string)
LLM model identifier if `classification_method` is `llm`.

**Examples:**
- `google.gemma-3-27b-it` (Dartmouth)
- `anthropic.claude-sonnet-4-5-20250929` (Dartmouth)
- `qwen2:7b` (Ollama)
- `gpt-4-turbo` (OpenAI)

### `classification_confidence` (float, 0.0-1.0)
Confidence score from LLM classification.

**Usage:**
- Filter low-confidence classifications for review: `< 0.7`
- Identify high-confidence classifications: `>= 0.9`
- Track model calibration over time

### `classification_date` (date, ISO 8601)
When the classification was performed.

### `classification_mode` (string)
Classification mode used.

**Values:**
- `short_context` - Extracted paragraph contexts (~800 chars)
- `full_text` - Full paper text (up to 50K chars)

**Recommendation:** Use `short_context` - comparison shows it performs better than full text.

### `classification_reasoning` (string)
Brief reasoning from LLM for the classification decision. Truncated to ~200 chars for storage efficiency.

### `classification_reviewed` (boolean, default: false)
Whether a human has reviewed and approved the LLM classification.

**Workflow:**
1. LLM classifies → `classification_reviewed=false`
2. Human reviews → Update to `classification_reviewed=true`
3. Filter for unreviewed: `WHERE classification_reviewed=false AND classification_confidence<0.8`

### `classification_reviewed_by` (string)
Who reviewed the LLM classification.

### `classification_reviewed_date` (date, ISO 8601)
When the LLM classification was reviewed.

## TSV Column Order

New columns added between `curated_date` and `oa_status`:

```
...
curated_by
curated_date
classification_method          ← NEW
classification_model           ← NEW
classification_confidence      ← NEW
classification_date            ← NEW
classification_mode            ← NEW
classification_reasoning       ← NEW
classification_reviewed        ← NEW
classification_reviewed_by     ← NEW
classification_reviewed_date   ← NEW
oa_status
pdf_url
pdf_path
```

## Backward Compatibility

- **Old TSVs** without these columns load fine (fields are optional)
- **Empty values** in TSV are treated as `None`/`null`
- **Default values**:
  - `classification_reviewed` defaults to `false`
  - All other fields default to `None`

## Usage Examples

### Filter by confidence threshold
```python
from citations_collector.persistence import tsv_io

citations = tsv_io.load_citations("citations.tsv")

# Find low-confidence classifications needing review
needs_review = [
    c for c in citations
    if c.classification_method == "llm"
    and c.classification_confidence
    and c.classification_confidence < 0.7
    and not c.classification_reviewed
]

print(f"{len(needs_review)} citations need review")
```

### Compare models
```python
from collections import defaultdict

by_model = defaultdict(list)
for c in citations:
    if c.classification_model:
        by_model[c.classification_model].append(c.classification_confidence)

for model, confidences in by_model.items():
    avg_conf = sum(confidences) / len(confidences)
    print(f"{model}: {avg_conf:.2f} avg confidence ({len(confidences)} classifications)")
```

### Track review progress
```python
llm_classified = [c for c in citations if c.classification_method == "llm"]
reviewed = [c for c in llm_classified if c.classification_reviewed]

print(f"Review progress: {len(reviewed)}/{len(llm_classified)} ({len(reviewed)/len(llm_classified)*100:.1f}%)")
```

## CLI Integration

The `classify` command will be updated to populate these fields:

```bash
# Classification metadata will be automatically saved:
# - classification_method: "llm"
# - classification_model: backend-specific identifier
# - classification_confidence: from LLM response (0.0-1.0)
# - classification_date: today
# - classification_mode: "short_context" or "full_text" (--full-text flag)
# - classification_reasoning: from LLM response (truncated)

citations-collector classify collection.yaml \
  --backend dartmouth \
  --model google.gemma-3-27b-it \
  --confidence-threshold 0.7

# Manual review workflow:
citations-collector classify collection.yaml --review
# For low-confidence results, prompts for human input
# Sets classification_reviewed=true after review
```

## Model Comparison Results

Based on systematic testing (see `docs/MODEL-COMPARISON.md`):

| Model | Backend | Avg Confidence | Performance |
|-------|---------|----------------|-------------|
| **google.gemma-3-27b-it** | Dartmouth (FREE) | 0.84 | ✓ Best |
| anthropic.claude-haiku-4-5 | Dartmouth ($) | 0.82 | Good |
| openai.gpt-oss-120b | Dartmouth (FREE) | 0.78 | Fair (short), Poor (full) |
| qwen2:7b | Ollama | 0.92 | Good (short only) |

**Recommendation:** Use `google.gemma-3-27b-it` with `short_context` mode for production classification.

## Migration

### Existing TSVs
No migration needed - old TSVs load fine with new schema. New fields will be `None` for existing records.

### Adding metadata to existing classifications
If you have citations already classified but without metadata:

```python
from citations_collector.persistence import tsv_io
from citations_collector.models import ClassificationMethod
from datetime import date

citations = tsv_io.load_citations("citations.tsv")

for c in citations:
    if c.citation_relationship and not c.classification_method:
        # Assume manual classification if no metadata
        c.classification_method = ClassificationMethod.manual
        c.classification_reviewed = True
        c.classification_date = date(2026, 2, 4)  # Set to appropriate date

tsv_io.save_citations(citations, "citations.tsv")
```

## Future Enhancements

Potential additions:
- `classification_prompt_version` - Track prompt template versions
- `classification_cost` - API cost per classification
- `classification_latency` - Response time in seconds
- `classification_alternatives` - Store top-N predictions with scores
