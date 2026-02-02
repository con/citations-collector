# Implementation Status: LLM-Based Citation Classification

## ✅ Completed

### 1. LLM Backend Infrastructure

**Location**: `src/citations_collector/llm/`

**Files created:**
- `base.py` - Abstract base class and ClassificationResult dataclass
- `prompts.py` - System prompt with CiTO relationship types
- `ollama_backend.py` - Local Ollama backend
- `openai_backend.py` - OpenAI-compatible backend (OpenAI, Dartmouth)
- `openrouter.py` - OpenRouter API backend
- `factory.py` - Backend factory with 4 backends
- `README.md` - Usage documentation

**Features:**
- ✅ Multi-backend abstraction (Ollama, OpenAI, Dartmouth, OpenRouter)
- ✅ Comprehensive CiTO-based system prompt
- ✅ JSON response parsing with fallbacks
- ✅ Error handling and logging
- ✅ Confidence scoring
- ✅ Context tracking

### 2. Test Scripts

**Files created:**
- `scripts/test_ollama_connection.py` - Standalone connection test
- `scripts/test_llm_backends.py` - Full backend test suite

---

## 🔧 Setup Required

### A. Ollama on Typhon (via SSH Tunnel)

**On typhon server:**
```bash
ssh typhon

# Verify ollama is running
systemctl status ollama

# List available models
ollama list

# If models not pulled yet:
ollama pull qwen2:7b     # Recommended (7B params)
ollama pull gemma:2b     # Lightweight alternative
ollama pull mistral:7b   # Fallback
```

**On your local machine (keep running in separate terminal):**
```bash
# Create SSH tunnel
ssh -L 11434:localhost:11434 typhon -N

# This tunnels localhost:11434 → typhon's ollama
# Keep this terminal open!
```

**Test connection:**
```bash
cd /home/yoh/proj/dandi/citations-collector-enh-zotero
uv run scripts/test_ollama_connection.py
```

Expected output:
```
Testing Ollama connection at http://localhost:11434...

1. Checking Ollama version...
   ✓ Ollama version: 0.x.x

2. Listing available models...
   ✓ Found 3 model(s):
      - qwen2:7b (4.2 GB)
      - gemma:2b (1.5 GB)
      - mistral:7b (4.1 GB)

3. Testing text generation...
   Using model: qwen2:7b
   ✓ Generation successful
   Response: {"greeting": "hello"}...

✓ All tests passed!
```

### B. Dartmouth Chat API

**Get JWT token:**
1. Go to https://chat.dartmouth.edu
2. Log in
3. Click **Settings** (top-right)
4. Go to **Account** section
5. **Copy JWT token**

**Token is already in:**
```bash
/home/yoh/proj/dandi/citations-collector/.git/secrets
export OPENAI_API_KEY=sk-e9169a478744478092bfb673727f8f54
```

**Test API endpoint (need to determine correct base_url):**
```bash
source .git/secrets

# Try different endpoints:
curl https://chat.dartmouth.edu/api/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Or:
curl https://chat.dartmouth.edu/api/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Or try OpenAI-compatible endpoint:
curl -X POST https://chat.dartmouth.edu/api/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4", "messages": [{"role": "user", "content": "hello"}]}'
```

**Note**: Currently getting "Internal Server Error" - need to determine correct API path.

---

## 🧪 Testing

### Quick Test (Ollama)

```bash
cd /home/yoh/proj/dandi/citations-collector-enh-zotero

# Start SSH tunnel in separate terminal
ssh -L 11434:localhost:11434 typhon -N

# Run connection test
uv run scripts/test_ollama_connection.py

# If successful, test classification:
python3 -c "
import sys
sys.path.insert(0, 'src')
from citations_collector.llm import create_backend

backend = create_backend('ollama', model='qwen2:7b')
result = backend.classify_citation(
    contexts=['We analyzed neural data from DANDI:000003 using spike sorting.'],
    paper_metadata={'title': 'Test', 'journal': 'Nature', 'year': 2024},
    dataset_id='dandi:000003',
)
print(f'Type: {result.relationship_type}')
print(f'Confidence: {result.confidence}')
print(f'Reasoning: {result.reasoning}')
"
```

### Full Test Suite

```bash
# Source secrets
source .git/secrets

# Run all backend tests
uv run scripts/test_llm_backends.py
```

---

## 📋 Next Steps

### Immediate (to verify backends work)

1. **Start SSH tunnel**:
   ```bash
   ssh -L 11434:localhost:11434 typhon -N
   ```

2. **Run Ollama test**:
   ```bash
   uv run scripts/test_ollama_connection.py
   ```

3. **Determine Dartmouth API path**:
   - Try different base URLs
   - Check Open WebUI documentation for your instance
   - Or just use Ollama for now (works offline, no costs)

### Phase 2: Context Extraction

- [ ] Implement `ContextExtractor` class (PDF + HTML parsing)
- [ ] Extract dataset mentions at paragraph level
- [ ] Create `extracted_citations.json` format
- [ ] Git-annex integration with oa_status metadata

### Phase 3: CLI Integration

- [ ] Add `extract-contexts` command
- [ ] Add `classify` command
- [ ] Interactive review mode for low-confidence
- [ ] Batch processing

### Phase 4: End-to-End Testing

- [ ] Test on subset of dandi-bib citations (~10 papers)
- [ ] Measure classification accuracy
- [ ] Tune confidence thresholds
- [ ] Document curated workflow

---

## 💰 Cost Estimates

| Backend | Model | Setup | Per 1000 Citations |
|---------|-------|-------|--------------------|
| **Ollama (typhon)** | qwen2:7b | 5 min | $0 |
| **Dartmouth** | gpt-4 | 2 min | $0 (institutional) |
| OpenRouter | gpt-4.1-nano | 2 min | ~$0.05 |
| OpenAI | gpt-4 | 2 min | ~$5-10 |

**Recommendation**: Use Ollama on typhon (via SSH tunnel) as primary backend. Fast, free, works offline.

---

## 🐛 Current Issues

1. **SSH tunnel not active**: Need to run `ssh -L 11434:localhost:11434 typhon -N`
2. **Dartmouth API path unknown**: Need to determine correct base_url
3. **Dependencies not installed in environment**: Use `uv run` for testing

---

## 📚 Documentation

See:
- `src/citations_collector/llm/README.md` - Backend usage guide
- `.specify/specs/llm-integration-plan.md` - Full design document
- `.specify/specs/reclassification-mvp.md` - Overall MVP plan
