# LLM Backends - Working Configuration

## ✅ Status: Both Backends Operational

### Ollama (Typhon via SSH Tunnel)

**Connection**: `http://host.containers.internal:11434`

**SSH Tunnel Command**:
```bash
ssh -L 0.0.0.0:11434:localhost:11434 typhon -N
```

**Available Models** (6 total):
- `mistral:7b` (4.1 GB)
- `gemma:2b` (1.6 GB)
- `qwen2:7b` (4.1 GB) ⭐ **Recommended**
- `qwen2.5:14b` (8.4 GB)
- `qwen2.5:32b` (18.5 GB)
- `gemma3:27b` (16.2 GB)

**Test Result**:
```
Relationship Type: Uses
Confidence: 0.95
Reasoning: The paper mentions analyzing neural recordings from the specified
dataset and validates its spike sorting algorithms on this data, indicating
a direct use of the dataset for research purposes.
```

**Usage**:
```python
from citations_collector.llm import create_backend

backend = create_backend('ollama', model='qwen2:7b')
# Auto-detects container and uses host.containers.internal
```

---

### Dartmouth Chat

**Connection**: `https://chat.dartmouth.edu/api`

**API Key**: Stored in `/home/yoh/proj/dandi/citations-collector/.git/secrets` as `OPENAI_API_KEY`

**Available Models** (42 total, notable ones):

**OpenAI**:
- `openai.gpt-oss-120b` - GPT-OSS 120b
- `openai.gpt-4.1-mini-2025-04-14` - GPT 4.1 mini
- `openai.gpt-4.1-2025-04-14` - GPT 4.1
- `openai_responses.gpt-5-mini-2025-08-07` - GPT-5 mini
- `openai_responses.gpt-5-2025-08-07` - GPT-5
- `openai_responses.gpt-5.1-chat-latest` - GPT-5.1 Instant
- `openai_responses.gpt-5.2-chat-latest` - GPT-5.2 Instant ⭐

**Anthropic**:
- `anthropic.claude-3-5-haiku-20241022` - Claude 3.5 Haiku
- `anthropic.claude-haiku-4-5-20251001` - Claude Haiku 4.5
- `anthropic.claude-3-7-sonnet-20250219` - Claude 3.7 Sonnet
- `anthropic.claude-opus-4-5-20251101` - Claude Opus 4.5 ⭐
- `anthropic.claude-sonnet-4-20250514` - Claude Sonnet 4
- `anthropic.claude-sonnet-4-5-20250929` - Claude Sonnet 4.5 ⭐ **Used for testing**

**Google**:
- `google.gemma-3-27b-it` - Gemma 3 27b
- `vertex_ai.gemini-2.0-flash-001` - Gemini 2.0 Flash
- `vertex_ai.gemini-2.5-flash` - Gemini 2.5 Flash

**Meta**:
- `meta.llama-3.2-11b-vision-instruct` - Llama 3.2 11b

**Qwen**:
- `qwen.qwen3-vl-32b-instruct-fp8` - Qwen3-VL 32b

**Test Result** (with Claude Sonnet 4.5):
```
Relationship Type: Uses
Confidence: 0.95
Reasoning: Context 1 explicitly states 'We analyzed neural recordings from
DANDI:000003 using spike sorting', which directly indicates the paper processed
and analyzed data from the dataset. The verb 'analyzed' is a strong indicator
of the 'Uses' relationship. Context 2 provides additional description of the
dataset content but doesn't change the primary relationship. The paper is
published in Nature Neuroscience (a methods/research journal, not a data
descriptor journal), and the contexts show active data analysis rather than
dataset description, validation, or review.
```

**Usage**:
```python
from citations_collector.llm import create_backend

# Use Claude Sonnet 4.5
backend = create_backend(
    'dartmouth',
    model='anthropic.claude-sonnet-4-5-20250929'
)

# Or GPT-5.2
backend = create_backend(
    'dartmouth',
    model='openai_responses.gpt-5.2-chat-latest'
)
```

---

## Classification Test Cases

All three tests passed with correct classifications:

### Test 1: Paper Analyzing Data → "Uses"
```
Contexts:
- "We analyzed neural recordings from DANDI:000003 using spike sorting."
- "The dataset contains high-quality electrophysiology data."

Paper: "Advanced spike sorting methods" (Nature Neuroscience)

Result: Uses (0.95 confidence) ✅
```

### Test 2: Data Descriptor Paper → "IsDocumentedBy"
```
Contexts:
- "Here we present a comprehensive dataset (DANDI:000108)..."
- "This dataset includes recordings from 532 neurons..."

Paper: "A comprehensive dataset..." (Scientific Data)

Result: IsDocumentedBy (0.95 confidence) ✅
```

### Test 3: Method Validation → "CitesAsEvidence"
```
Contexts:
- "To validate our algorithm, we benchmarked on DANDI:000020"
- "Our method achieved 95% accuracy when tested on DANDI:000020"

Paper: "A novel algorithm for cell type classification" (Nature Methods)

Result: CitesAsEvidence (0.95 confidence) ✅
```

---

## Cost Comparison

| Backend | Model | Cost per 1000 citations | Speed |
|---------|-------|-------------------------|-------|
| **Ollama (typhon)** | qwen2:7b | $0 | ~3-5s/citation |
| **Dartmouth** | Claude Sonnet 4.5 | $0 (institutional) | ~2-4s/citation |
| **Dartmouth** | GPT-5.2 | $0 (institutional) | ~2-3s/citation |
| OpenRouter | gpt-4.1-nano | ~$0.05 | ~1-2s/citation |

---

## Recommendations

### For Development/Testing
Use **Ollama (qwen2:7b)**:
- Free
- Works offline
- Good quality classifications
- Fast enough for development

### For Production/Bulk Classification
Use **Dartmouth (Claude Sonnet 4.5)**:
- Free (institutional)
- Excellent reasoning quality
- Faster than Ollama
- Access to latest models

### For High-Confidence Review
Use **Dartmouth (Claude Opus 4.5)** for low-confidence cases requiring deeper analysis.

---

## Dependencies Added

Updated `pyproject.toml`:
```toml
[project.optional-dependencies]
llm = [
    "openai>=1.0.0",  # For OpenAI and Dartmouth backends
]
```

Install with:
```bash
uv pip install -e ".[llm]"
```

---

## Next Steps

1. ✅ Ollama backend working
2. ✅ Dartmouth backend working
3. ⏭️ Implement context extraction from PDFs/HTMLs
4. ⏭️ Build classification pipeline
5. ⏭️ Add CLI commands
6. ⏭️ Test on real dandi-bib citations

---

## Files Created/Modified

**Created**:
- `src/citations_collector/llm/` - Full LLM backend module
- `scripts/test_ollama_connection.py` - Connection test
- `scripts/test_llm_backends.py` - Full backend test suite
- `scripts/setup-ollama-tunnel.sh` - Helper script
- `docs/SETUP-LLM.md` - Setup guide

**Modified**:
- `pyproject.toml` - Added `llm` optional dependencies
