# LLM Integration Plan for Citation Relationship Classification

## Research Summary

### Related Projects' Approaches

**NeuroD3**: Plans to use "LLM-based citation identification" but hasn't implemented it yet. Mentions ODDPub's NLP methodology for discovering data citations.

**find_reuse**: Uses **pattern matching** with regular expressions, not LLMs. Identifies dataset IDs via regex patterns for DANDI, OpenNeuro, Figshare, PhysioNet (e.g., `"10.48324/dandi.{id}"`, `"DANDI: {id}"`).

**Key insight**: Neither project has implemented LLM-based citation *classification* (determining relationship types). find_reuse's pattern matching works for *finding* dataset IDs, but our task—classifying citation semantics (Uses vs Reviews vs CitesAsEvidence)—requires understanding context, making LLMs essential.

---

## LLM Backend Options

### Option 1: OpenRouter API

**Best models for classification:**

1. **GPT-4.1 Nano** (Recommended)
   - **Cost**: $0.10/M input tokens, $0.40/M output tokens
   - **Performance**: 80.1% on MMLU, 50.3% on GPQA
   - **Context**: 1M tokens
   - **Use case**: Fast, cheap classification tasks
   - **Why**: Optimized for data classification and low-latency text tasks

2. **Claude Opus 4.5** (For complex cases)
   - **Best for**: Deep analysis of ambiguous citations
   - **Context**: 200K tokens (entire papers)
   - **Use case**: High-confidence review of low-confidence classifications

**Sources:**
- [OpenRouter Models](https://openrouter.ai/models)
- [GPT-4.1 Nano details](https://openrouter.ai/openai/gpt-4.1-nano)
- [Top AI Models on OpenRouter 2026](https://www.teamday.ai/blog/top-ai-models-openrouter-2026)

### Option 2: Local Ollama

**Best models (2026):**

1. **Qwen2 7B** (Recommended)
   - **Size**: 7B parameters
   - **Why**: Robust for summarization and text generation
   - **Use case**: Local deployment, no API costs

2. **Gemma 2B** (Lightweight)
   - **Size**: 2B parameters
   - **Why**: High-performing, efficient
   - **Use case**: Resource-constrained environments

3. **Phi-3 Mini** (Alternative)
   - **Size**: 3B parameters
   - **Why**: State-of-the-art from Microsoft
   - **Use case**: Balanced performance/size

4. **Mistral 7B** (Fallback)
   - **Why**: Fast, efficient for resource-constrained environments

**Sources:**
- [Best Ollama Models 2025](https://collabnix.com/best-ollama-models-in-2025-complete-performance-comparison/)
- [Top Small Language Models for 2026](https://www.datacamp.com/blog/top-small-language-models)
- [How to Pick a Scientific LLM in Ollama](https://www.arsturn.com/blog/how-to-pick-the-right-scientific-model-in-ollama-for-your-research-project)

### Option 3: Dartmouth OpenAI Interface

**Model**: chat.dartmouth.edu provides OpenAI-compatible interface
- **Likely models**: GPT-4, GPT-3.5-turbo
- **Advantage**: Institutional access, no personal API costs
- **Use case**: Dartmouth users

---

## Multi-Backend Abstraction Design

### Architecture

```python
# src/citations_collector/llm/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

@dataclass
class ClassificationResult:
    """Result from LLM classification."""
    relationship_type: str  # CitationRelationship enum value
    confidence: float  # 0.0-1.0
    reasoning: str  # LLM's explanation
    context_used: list[str]  # Which paragraph contexts were analyzed

class LLMBackend(ABC):
    """Abstract base class for LLM backends."""

    @abstractmethod
    def classify_citation(
        self,
        contexts: list[str],  # Paragraph-level contexts mentioning dataset
        paper_metadata: dict,  # Title, journal, year, etc.
        dataset_id: str,
    ) -> ClassificationResult:
        """Classify citation relationship type based on context."""
        pass

    @abstractmethod
    def batch_classify(
        self,
        citations: list[tuple[list[str], dict, str]],
    ) -> list[ClassificationResult]:
        """Batch classification for efficiency."""
        pass
```

### Backend Implementations

#### 1. OpenRouter Backend

```python
# src/citations_collector/llm/openrouter.py

import os
import requests
from .base import LLMBackend, ClassificationResult

class OpenRouterBackend(LLMBackend):
    """OpenRouter API backend."""

    def __init__(
        self,
        model: str = "openai/gpt-4.1-nano",
        api_key: str | None = None,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY required")
        self.base_url = "https://openrouter.ai/api/v1"

    def classify_citation(
        self,
        contexts: list[str],
        paper_metadata: dict,
        dataset_id: str,
    ) -> ClassificationResult:
        """Classify using OpenRouter API."""
        prompt = self._build_classification_prompt(
            contexts, paper_metadata, dataset_id
        )

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": CLASSIFICATION_SYSTEM_PROMPT,
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,  # Low for consistency
            },
        )
        response.raise_for_status()

        return self._parse_response(response.json())

    def _build_classification_prompt(
        self, contexts: list[str], metadata: dict, dataset_id: str
    ) -> str:
        """Build classification prompt."""
        return f"""
Paper: {metadata.get('title', 'Unknown')}
Journal: {metadata.get('journal', 'Unknown')}
Year: {metadata.get('year', 'Unknown')}
Dataset: {dataset_id}

Context excerpts where dataset is mentioned:
{self._format_contexts(contexts)}

Classify the citation relationship type from these options:
- Uses: Paper analyzes or processes data from the dataset
- IsDocumentedBy: Paper is a data descriptor describing the dataset
- Reviews: Paper critically evaluates or reviews the dataset
- CitesAsEvidence: Paper uses dataset to validate methods or benchmark
- Compiles: Paper combines data from multiple datasets (meta-analysis)
- CitesAsDataSource: Paper explicitly cites as data source
- CitesForInformation: Background/contextual reference
- Cites: Generic reference (fallback)

Return JSON:
{{
    "relationship_type": "...",
    "confidence": 0.0-1.0,
    "reasoning": "explanation"
}}
"""

    def _format_contexts(self, contexts: list[str]) -> str:
        """Format context paragraphs."""
        return "\n\n".join(f"[{i+1}] {ctx}" for i, ctx in enumerate(contexts))

    def _parse_response(self, response_json: dict) -> ClassificationResult:
        """Parse OpenRouter response."""
        content = response_json["choices"][0]["message"]["content"]
        # Parse JSON from content
        import json
        result = json.loads(content)
        return ClassificationResult(
            relationship_type=result["relationship_type"],
            confidence=result["confidence"],
            reasoning=result["reasoning"],
            context_used=[]  # Could track which contexts influenced decision
        )
```

#### 2. Ollama Backend

```python
# src/citations_collector/llm/ollama_backend.py

import requests
from .base import LLMBackend, ClassificationResult

class OllamaBackend(LLMBackend):
    """Local Ollama backend."""

    def __init__(
        self,
        model: str = "qwen2:7b",  # Default to Qwen2 7B
        base_url: str = "http://localhost:11434",
    ):
        self.model = model
        self.base_url = base_url

    def classify_citation(
        self,
        contexts: list[str],
        paper_metadata: dict,
        dataset_id: str,
    ) -> ClassificationResult:
        """Classify using local Ollama."""
        prompt = self._build_classification_prompt(
            contexts, paper_metadata, dataset_id
        )

        response = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": CLASSIFICATION_SYSTEM_PROMPT,
                    },
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "options": {
                    "temperature": 0.1,
                },
            },
        )
        response.raise_for_status()

        return self._parse_response(response.json())

    # ... (same _build_classification_prompt and _parse_response as OpenRouter)
```

#### 3. Dartmouth/OpenAI Backend

```python
# src/citations_collector/llm/openai_backend.py

import os
from openai import OpenAI
from .base import LLMBackend, ClassificationResult

class OpenAIBackend(LLMBackend):
    """OpenAI-compatible backend (OpenAI, Dartmouth, etc.)."""

    def __init__(
        self,
        model: str = "gpt-4",
        api_key: str | None = None,
        base_url: str | None = None,  # For Dartmouth: chat.dartmouth.edu
    ):
        self.model = model
        self.client = OpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            base_url=base_url,  # Override for Dartmouth
        )

    def classify_citation(
        self,
        contexts: list[str],
        paper_metadata: dict,
        dataset_id: str,
    ) -> ClassificationResult:
        """Classify using OpenAI-compatible API."""
        prompt = self._build_classification_prompt(
            contexts, paper_metadata, dataset_id
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": CLASSIFICATION_SYSTEM_PROMPT,
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )

        return self._parse_response(response)

    # ... (same prompt building and parsing)
```

### Backend Factory

```python
# src/citations_collector/llm/factory.py

from typing import Literal
from .base import LLMBackend
from .openrouter import OpenRouterBackend
from .ollama_backend import OllamaBackend
from .openai_backend import OpenAIBackend

BackendType = Literal["openrouter", "ollama", "openai", "dartmouth"]

def create_backend(
    backend_type: BackendType,
    **kwargs,
) -> LLMBackend:
    """Factory for creating LLM backends."""
    if backend_type == "openrouter":
        return OpenRouterBackend(**kwargs)
    elif backend_type == "ollama":
        return OllamaBackend(**kwargs)
    elif backend_type == "openai":
        return OpenAIBackend(**kwargs)
    elif backend_type == "dartmouth":
        # Dartmouth uses OpenAI interface with custom base_url
        return OpenAIBackend(
            base_url="https://chat.dartmouth.edu/v1",  # Example URL
            **kwargs,
        )
    else:
        raise ValueError(f"Unknown backend: {backend_type}")
```

---

## Classification System Prompt

```python
# src/citations_collector/llm/prompts.py

CLASSIFICATION_SYSTEM_PROMPT = """You are an expert in scientific citation analysis, specializing in how research papers reference scientific datasets.

Your task is to classify the relationship between a paper and a dataset it cites.

Citation Relationship Types (CiTO Ontology):

1. **Uses** (cito:uses): Paper analyzes or processes data from the dataset
   - Example: "We analyzed neural recordings from DANDI:000003..."

2. **IsDocumentedBy** (cito:isDocumentedBy): Paper is a data descriptor describing the dataset
   - Example: Data descriptor in Scientific Data journal
   - Usually the paper itself creates/describes the dataset

3. **Reviews** (cito:reviews): Paper critically evaluates or reviews the dataset
   - Example: "We assessed the quality and completeness of DANDI:000108..."
   - Systematic reviews, dataset quality assessments

4. **CitesAsEvidence** (cito:citesAsEvidence): Paper uses dataset to validate methods or benchmark algorithms
   - Example: "We validated our spike sorting algorithm on DANDI:000003..."
   - Benchmarking, method validation

5. **Compiles** (cito:compiles): Paper combines data from multiple datasets (meta-analysis)
   - Example: "We performed federated analysis across DANDI:000003, 000020, and 000055..."
   - Multi-dataset studies, meta-analyses

6. **CitesAsDataSource** (cito:citesAsDataSource): Paper explicitly cites as data source
   - More specific than generic "Cites"
   - Acknowledges dataset as source without deep analysis

7. **CitesForInformation** (cito:citesForInformation): Background/contextual reference
   - Example: Tutorial mentioning dataset as example
   - Educational materials

8. **Cites** (cito:cites): Generic reference (use as fallback)
   - When none of the above fit

Guidelines:
- Papers can have MULTIPLE relationship types (e.g., both Uses and Reviews)
- Look for specific verbs: "analyzed", "validated", "combined", "describes", "reviewed"
- Journal name is a strong signal (Scientific Data → IsDocumentedBy)
- Be conservative: if uncertain, use confidence < 0.7

Return ONLY valid JSON with keys: relationship_type, confidence, reasoning.
"""
```

---

## Configuration Integration

### Add to Collection YAML

```yaml
llm:
  backend: openrouter  # openrouter | ollama | openai | dartmouth
  model: openai/gpt-4.1-nano
  # API key via OPENROUTER_API_KEY / OPENAI_API_KEY envvars
  # Or for Dartmouth:
  # backend: dartmouth
  # model: gpt-4

classify:
  confidence_threshold: 0.7  # Auto-accept if confidence > 0.7
  review_low_confidence: true  # Interactive review for < threshold
```

### Pydantic Models

```python
# In schema/citations.yaml, add:

class LLMConfig(ConfiguredBaseModel):
    backend: str = "openrouter"  # openrouter | ollama | openai | dartmouth
    model: str | None = None
    base_url: str | None = None  # For custom endpoints

class ClassifyConfig(ConfiguredBaseModel):
    confidence_threshold: float = 0.7
    review_low_confidence: bool = True

# Add to Collection:
llm: LLMConfig | None = None
classify: ClassifyConfig | None = None
```

---

## CLI Integration

### New Command: `classify`

```bash
# Classify citations using LLM
citations-collector classify collection.yaml \
    --backend openrouter \
    --model openai/gpt-4.1-nano \
    --confidence-threshold 0.7 \
    --review  # Interactive review for low-confidence
    --dry-run  # Show classifications without updating TSV

# Or use Ollama locally
citations-collector classify collection.yaml \
    --backend ollama \
    --model qwen2:7b

# Or use Dartmouth
citations-collector classify collection.yaml \
    --backend dartmouth \
    --model gpt-4
```

### Implementation

```python
# src/citations_collector/cli.py

@cli.command()
@click.argument("collection", type=click.Path(exists=True))
@click.option("--backend", type=click.Choice(["openrouter", "ollama", "openai", "dartmouth"]))
@click.option("--model", help="LLM model name")
@click.option("--confidence-threshold", type=float, default=0.7)
@click.option("--review/--no-review", default=True)
@click.option("--dry-run", is_flag=True)
def classify(collection, backend, model, confidence_threshold, review, dry_run):
    """Classify citation relationships using LLM."""
    from .llm.factory import create_backend
    from .classifier import CitationClassifier

    # Load collection config
    config = load_collection_yaml(collection)

    # Create LLM backend
    llm = create_backend(
        backend or config.llm.backend,
        model=model or config.llm.model,
    )

    # Load citations and extracted contexts
    citations = tsv_io.load_citations(config.output_tsv)

    # Run classifier
    classifier = CitationClassifier(llm, confidence_threshold)
    results = classifier.classify_all(citations, config.pdfs.output_dir)

    # Report
    click.echo(f"✓ {len([r for r in results if r.confidence > confidence_threshold])} high-confidence")
    click.echo(f"⚠ {len([r for r in results if r.confidence <= confidence_threshold])} need review")

    if review and not dry_run:
        # Interactive review
        for citation, result in zip(citations, results):
            if result.confidence <= confidence_threshold:
                review_classification(citation, result)

    if not dry_run:
        # Update TSV with new relationship types
        for citation, result in zip(citations, results):
            citation.citation_relationship = result.relationship_type
        tsv_io.save_citations(citations, config.output_tsv)
```

---

## Cost Estimates

### OpenRouter (GPT-4.1 Nano)

Assume:
- 1000 citations to classify
- Average 500 tokens/classification (contexts + prompt + response)
- Total: 500K tokens

**Cost**: 500K tokens × $0.10/1M = **$0.05** (negligible)

### Ollama (Local)

**Cost**: $0 (free after initial setup)
**Setup time**: ~10 minutes to install Ollama + download Qwen2:7b

### Dartmouth

**Cost**: $0 (institutional access)

---

## Recommended Default Configuration

```yaml
llm:
  backend: openrouter
  model: openai/gpt-4.1-nano  # Fast, cheap, accurate

classify:
  confidence_threshold: 0.7
  review_low_confidence: true
```

**Why GPT-4.1 Nano?**
- Optimized for classification tasks
- 10x cheaper than GPT-4
- Fast (low latency)
- Good balance of cost/performance for this task

**When to use Ollama?**
- Privacy concerns (data stays local)
- No internet/API access
- High volume (>10K citations where costs add up)

**When to use Dartmouth?**
- You have institutional access
- No personal API costs

---

## Next Steps

1. **Implement backend abstraction** (Task: create `src/citations_collector/llm/` module)
2. **Add LLM config to schema** (Task: update `schema/citations.yaml`)
3. **Build classifier** (Task: create `src/citations_collector/classifier.py`)
4. **Add CLI command** (Task: update `src/citations_collector/cli.py`)
5. **Write tests** (Task: create `tests/test_llm_backends.py` with mocked APIs)
6. **Test on real data** (Task: run on subset of dandi-bib citations)

---

## References

### OpenRouter
- [OpenRouter Models](https://openrouter.ai/models)
- [GPT-4.1 Nano](https://openrouter.ai/openai/gpt-4.1-nano)
- [Top AI Models on OpenRouter 2026](https://www.teamday.ai/blog/top-ai-models-openrouter-2026)

### Ollama
- [Best Ollama Models 2025](https://collabnix.com/best-ollama-models-in-2025-complete-performance-comparison/)
- [Scientific LLM Selection Guide](https://www.arsturn.com/blog/how-to-pick-the-right-scientific-model-in-ollama-for-your-research-project)
- [Top Small Language Models for 2026](https://www.datacamp.com/blog/top-small-language-models)

### Academic Citation Analysis
- [Best AI Tools for Scientific Literature Review](https://www.cypris.ai/insights/11-best-ai-tools-for-scientific-literature-review-in-2026)
- [Scite AI for Citation Analysis](https://scite.ai/)
