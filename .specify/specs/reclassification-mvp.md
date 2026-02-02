# Citation Reclassification MVP

## Overview

Build an agentic tool to automatically reclassify existing citations from generic "Cites" to specific relationship types (Uses, Reviews, CitesAsEvidence, etc.) using LLM-based analysis of citation context.

**Key features:**
- Extract context snippets from PDFs/HTMLs where datasets are mentioned
- Use LLM to classify relationship types based on context
- Store extracted contexts as `extracted_citations.json` alongside papers
- Handle git-annex with OA status metadata
- Interactive review for low-confidence classifications

---

## Architecture

### Data Flow

```
PDFs/HTMLs
    ↓
Context Extraction (paragraph-level)
    ↓
extracted_citations.json (per paper)
    ↓
LLM Classification
    ↓
Updated TSV with relationship types
```

### File Structure

```
pdfs/
├── 10.1038/
│   └── s41597-023-02214-y/
│       ├── article.pdf
│       ├── article.html (if available)
│       ├── article.bib
│       └── extracted_citations.json  ← NEW
├── 10.1101/
│   └── 2024.01.15.575901/
│       ├── article.pdf
│       └── extracted_citations.json
```

---

## Component 1: Context Extraction

### extracted_citations.json Format

```json
{
  "paper_doi": "10.1038/s41597-023-02214-y",
  "paper_title": "A comprehensive dataset of...",
  "paper_journal": "Scientific Data",
  "paper_year": 2023,
  "oa_status": "gold",
  "extraction_date": "2026-01-31T12:00:00Z",
  "extraction_method": "pdfplumber+beautifulsoup",
  "citations": [
    {
      "dataset_id": "DANDI:000003",
      "dataset_mentions": [
        {
          "context": "We analyzed neural recordings from the Allen Institute Neuropixels dataset (DANDI:000003) using custom spike sorting algorithms.",
          "page": 3,
          "section": "Methods",
          "source": "pdf"
        },
        {
          "context": "The DANDI:000003 dataset contains high-quality electrophysiological recordings from mouse visual cortex, making it ideal for validating our approach.",
          "page": 8,
          "section": "Results",
          "source": "pdf"
        }
      ],
      "classified_relationship": null,  // Filled by LLM
      "classification_confidence": null,
      "classification_reasoning": null
    },
    {
      "dataset_id": "DANDI:000020",
      "dataset_mentions": [
        {
          "context": "We also tested on the Patch-seq dataset (DANDI:000020) to demonstrate generalizability.",
          "page": 9,
          "section": "Results",
          "source": "pdf"
        }
      ]
    }
  ]
}
```

### Context Extractor Implementation

```python
# src/citations_collector/context_extractor.py

import json
from pathlib import Path
from typing import Any
import pdfplumber
from bs4 import BeautifulSoup
import re

class ContextExtractor:
    """Extract citation contexts from PDFs and HTMLs."""

    def __init__(self, dataset_patterns: dict[str, list[str]]):
        """
        Initialize with dataset ID patterns.

        Args:
            dataset_patterns: Mapping of dataset namespace to regex patterns
                Example: {"dandi": [r"DANDI:\s*(\d+)", r"dandiarchive\.org/dandiset/(\d+)"]}
        """
        self.dataset_patterns = dataset_patterns

    def extract_from_pdf(
        self,
        pdf_path: Path,
        target_datasets: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Extract citation contexts from PDF.

        Args:
            pdf_path: Path to PDF file
            target_datasets: List of dataset IDs to search for (e.g., ["DANDI:000003"])
                            If None, search for all known patterns

        Returns:
            extracted_citations.json structure
        """
        with pdfplumber.open(pdf_path) as pdf:
            # Extract metadata
            metadata = pdf.metadata or {}

            # Extract text by page
            citations = {}
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""

                # Search for dataset mentions
                for dataset_id in target_datasets or []:
                    matches = self._find_mentions(text, dataset_id)
                    for match in matches:
                        if dataset_id not in citations:
                            citations[dataset_id] = {
                                "dataset_id": dataset_id,
                                "dataset_mentions": [],
                            }

                        # Extract paragraph containing mention
                        context = self._extract_paragraph(text, match.start())

                        citations[dataset_id]["dataset_mentions"].append({
                            "context": context,
                            "page": page_num,
                            "section": None,  # TODO: extract section headers
                            "source": "pdf",
                        })

            return {
                "paper_doi": self._extract_doi(metadata.get("Title", "")),
                "paper_title": metadata.get("Title", "Unknown"),
                "paper_journal": metadata.get("Creator", "Unknown"),
                "paper_year": None,  # From metadata elsewhere
                "oa_status": None,  # Set externally
                "extraction_date": datetime.now().isoformat(),
                "extraction_method": "pdfplumber",
                "citations": list(citations.values()),
            }

    def extract_from_html(
        self,
        html_path: Path,
        target_datasets: list[str],
    ) -> dict[str, Any]:
        """Extract citation contexts from HTML."""
        with open(html_path) as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # Remove script/style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Extract by paragraph
        citations = {}
        for p in soup.find_all("p"):
            text = p.get_text()

            for dataset_id in target_datasets:
                if dataset_id in text:
                    if dataset_id not in citations:
                        citations[dataset_id] = {
                            "dataset_id": dataset_id,
                            "dataset_mentions": [],
                        }

                    # Try to find section header
                    section = self._find_section_header(p)

                    citations[dataset_id]["dataset_mentions"].append({
                        "context": text.strip(),
                        "page": None,
                        "section": section,
                        "source": "html",
                    })

        return {
            "extraction_method": "beautifulsoup",
            "citations": list(citations.values()),
            # ... metadata
        }

    def _find_mentions(self, text: str, dataset_id: str) -> list[re.Match]:
        """Find all mentions of dataset ID in text."""
        # Simple regex for now
        pattern = re.escape(dataset_id)
        return list(re.finditer(pattern, text, re.IGNORECASE))

    def _extract_paragraph(self, text: str, position: int) -> str:
        """
        Extract paragraph containing the position.

        Paragraph = text between two newlines or up to 500 chars.
        """
        # Find paragraph boundaries
        start = text.rfind("\n\n", 0, position)
        if start == -1:
            start = max(0, position - 250)

        end = text.find("\n\n", position)
        if end == -1:
            end = min(len(text), position + 250)

        paragraph = text[start:end].strip()

        # Clean up
        paragraph = re.sub(r"\s+", " ", paragraph)  # Normalize whitespace

        return paragraph

    def _find_section_header(self, element) -> str | None:
        """Find nearest section header before element."""
        # Look backwards for h1, h2, h3
        for sibling in element.find_previous_siblings():
            if sibling.name in ["h1", "h2", "h3", "h4"]:
                return sibling.get_text().strip()
        return None
```

### Git-Annex Integration

```python
# src/citations_collector/git_annex.py

import subprocess
from pathlib import Path

class GitAnnexHelper:
    """Helper for git-annex operations."""

    @staticmethod
    def add_with_metadata(
        file_path: Path,
        oa_status: str,  # gold | green | hybrid | closed
        url: str | None = None,
    ) -> None:
        """
        Add extracted_citations.json to git-annex with metadata.

        Args:
            file_path: Path to extracted_citations.json
            oa_status: Open access status from TSV
            url: Original PDF URL (for provenance)
        """
        if oa_status in ["gold", "green", "hybrid"]:
            # Open access - no distribution restrictions
            subprocess.run(
                ["git", "annex", "add", str(file_path)],
                check=True,
            )
            subprocess.run(
                ["git", "annex", "metadata", str(file_path),
                 "-s", f"oa_status={oa_status}"],
                check=True,
            )
        else:
            # Closed access - add distribution restriction tag
            subprocess.run(
                ["git", "annex", "add", str(file_path)],
                check=True,
            )
            subprocess.run(
                ["git", "annex", "metadata", str(file_path),
                 "-s", f"oa_status={oa_status}",
                 "-t", "distribution-restricted"],  # Tag for closed access
                check=True,
            )

        # Add URL if available (for open access PDFs)
        if url and oa_status in ["gold", "green", "hybrid"]:
            subprocess.run(
                ["git", "annex", "metadata", str(file_path),
                 "-s", f"url={url}"],
                check=True,
            )
```

---

## Component 2: LLM Classification

See [llm-integration-plan.md](./llm-integration-plan.md) for full LLM backend details.

### Classifier Implementation

```python
# src/citations_collector/classifier.py

from pathlib import Path
import json
from .llm.base import LLMBackend, ClassificationResult
from .models import CitationRecord

class CitationClassifier:
    """Classify citations using LLM."""

    def __init__(
        self,
        llm_backend: LLMBackend,
        confidence_threshold: float = 0.7,
    ):
        self.llm = llm_backend
        self.confidence_threshold = confidence_threshold

    def classify_all(
        self,
        citations: list[CitationRecord],
        pdfs_dir: Path,
    ) -> list[ClassificationResult]:
        """
        Classify all citations.

        Args:
            citations: List of citation records from TSV
            pdfs_dir: Directory containing PDFs with extracted_citations.json

        Returns:
            List of classification results
        """
        results = []

        for citation in citations:
            # Find extracted_citations.json for this paper
            extracted_json = self._find_extracted_json(
                citation.citation_doi, pdfs_dir
            )

            if not extracted_json:
                # No context available - skip or use fallback
                results.append(ClassificationResult(
                    relationship_type="Cites",
                    confidence=0.0,
                    reasoning="No extracted context available",
                    context_used=[],
                ))
                continue

            # Load extracted contexts
            with open(extracted_json) as f:
                extracted = json.load(f)

            # Find contexts for this specific dataset
            contexts = self._get_contexts_for_dataset(
                extracted, citation.item_id
            )

            if not contexts:
                results.append(ClassificationResult(
                    relationship_type="Cites",
                    confidence=0.0,
                    reasoning="Dataset not mentioned in extracted contexts",
                    context_used=[],
                ))
                continue

            # Classify using LLM
            paper_metadata = {
                "title": extracted.get("paper_title"),
                "journal": extracted.get("paper_journal"),
                "year": extracted.get("paper_year"),
            }

            result = self.llm.classify_citation(
                contexts=contexts,
                paper_metadata=paper_metadata,
                dataset_id=citation.item_id,
            )

            # Update extracted_citations.json with classification
            self._update_extracted_json(
                extracted_json, citation.item_id, result
            )

            results.append(result)

        return results

    def _find_extracted_json(
        self, doi: str, pdfs_dir: Path
    ) -> Path | None:
        """Find extracted_citations.json for a DOI."""
        # DOI to path: 10.1038/s41597-023-02214-y → pdfs/10.1038/s41597-023-02214-y/
        doi_path = pdfs_dir / doi / "extracted_citations.json"
        return doi_path if doi_path.exists() else None

    def _get_contexts_for_dataset(
        self, extracted: dict, dataset_id: str
    ) -> list[str]:
        """Extract context paragraphs for specific dataset."""
        for citation in extracted.get("citations", []):
            if citation["dataset_id"] == dataset_id:
                return [
                    mention["context"]
                    for mention in citation.get("dataset_mentions", [])
                ]
        return []

    def _update_extracted_json(
        self,
        json_path: Path,
        dataset_id: str,
        result: ClassificationResult,
    ) -> None:
        """Update extracted_citations.json with classification result."""
        with open(json_path) as f:
            data = json.load(f)

        # Find and update citation
        for citation in data.get("citations", []):
            if citation["dataset_id"] == dataset_id:
                citation["classified_relationship"] = result.relationship_type
                citation["classification_confidence"] = result.confidence
                citation["classification_reasoning"] = result.reasoning
                break

        # Save updated JSON
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)
```

---

## Component 3: CLI Commands

### 1. Extract Contexts

```bash
# Extract citation contexts from PDFs
citations-collector extract-contexts collection.yaml \
    --output-dir pdfs/ \
    --git-annex  # Add to git-annex with oa_status metadata
    --overwrite  # Re-extract even if extracted_citations.json exists
```

Implementation:

```python
@cli.command()
@click.argument("collection", type=click.Path(exists=True))
@click.option("--output-dir", type=click.Path(), default="pdfs/")
@click.option("--git-annex/--no-git-annex", default=True)
@click.option("--overwrite", is_flag=True)
def extract_contexts(collection, output_dir, git_annex, overwrite):
    """Extract citation contexts from PDFs/HTMLs."""
    from .context_extractor import ContextExtractor
    from .git_annex import GitAnnexHelper

    config = load_collection_yaml(collection)
    citations = tsv_io.load_citations(config.output_tsv)

    # Group by DOI
    papers = {}
    for citation in citations:
        if citation.citation_doi:
            if citation.citation_doi not in papers:
                papers[citation.citation_doi] = []
            papers[citation.citation_doi].append(citation.item_id)

    extractor = ContextExtractor(dataset_patterns={
        "dandi": [r"DANDI:\s*(\d+)", r"dandiarchive\.org/dandiset/(\d+)"],
    })

    for doi, dataset_ids in papers.items():
        pdf_path = Path(output_dir) / doi / "article.pdf"
        html_path = Path(output_dir) / doi / "article.html"
        json_path = Path(output_dir) / doi / "extracted_citations.json"

        if json_path.exists() and not overwrite:
            click.echo(f"⊘ {doi} (already extracted)")
            continue

        # Extract from PDF or HTML
        if pdf_path.exists():
            extracted = extractor.extract_from_pdf(pdf_path, dataset_ids)
        elif html_path.exists():
            extracted = extractor.extract_from_html(html_path, dataset_ids)
        else:
            click.echo(f"✗ {doi} (no PDF/HTML found)")
            continue

        # Add OA status from TSV
        oa_status = citations[0].oa_status  # Assume same for all citations of paper
        extracted["oa_status"] = oa_status

        # Save
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w") as f:
            json.dump(extracted, f, indent=2)

        # Git-annex
        if git_annex:
            GitAnnexHelper.add_with_metadata(
                json_path,
                oa_status=oa_status,
                url=citations[0].pdf_url,
            )

        click.echo(f"✓ {doi} ({len(extracted['citations'])} datasets)")
```

### 2. Classify Citations

```bash
# Classify using LLM (see llm-integration-plan.md)
citations-collector classify collection.yaml \
    --backend openrouter \
    --model openai/gpt-4.1-nano \
    --confidence-threshold 0.7 \
    --review  # Interactive review for low-confidence
```

(Implementation in llm-integration-plan.md)

---

## Workflow

### Step 1: Extract Contexts (One-time)

```bash
cd /home/yoh/proj/dandi/dandi-bib

# Extract contexts from all PDFs
citations-collector extract-contexts collection.yaml \
    --output-dir citations/pdfs/ \
    --git-annex

# Result: extracted_citations.json for each paper
# Git-annex: Files tagged with oa_status metadata
```

### Step 2: Classify (Batch)

```bash
# Run LLM classification
citations-collector classify collection.yaml \
    --backend openrouter \
    --model openai/gpt-4.1-nano

# Output:
# ✓ 150 citations classified (confidence > 0.7)
# ⚠ 30 citations need review (confidence < 0.7)
```

### Step 3: Review Low-Confidence (Interactive)

```bash
citations-collector classify collection.yaml --review

# Interactive prompt:
# ─────────────────────────────────────────────────────
# Paper: "A comprehensive dataset of..."
# Journal: Scientific Data
# Dataset: DANDI:000003
#
# Contexts:
# [1] "We analyzed neural recordings from..."
# [2] "The DANDI:000003 dataset contains..."
#
# LLM Classification: Uses (confidence: 0.65)
# Reasoning: "Paper analyzes data but confidence low due to ambiguous wording"
#
# Accept? [y/n/1-8 to select different type]: y
# ─────────────────────────────────────────────────────
```

---

## Implementation Timeline (3 weeks)

### Week 1: Context Extraction
- **Day 1-2**: Implement ContextExtractor (PDF + HTML)
- **Day 3**: Add git-annex integration with oa_status metadata
- **Day 4**: Build extract-contexts CLI command
- **Day 5**: Test on subset of dandi-bib PDFs (~50 papers)

### Week 2: LLM Classification
- **Day 1-2**: Implement LLM backend abstraction (OpenRouter, Ollama, OpenAI)
- **Day 3**: Build CitationClassifier
- **Day 4**: Add classify CLI command
- **Day 5**: Test classification on extracted contexts

### Week 3: Integration & Testing
- **Day 1-2**: Interactive review mode
- **Day 3**: Write tests (mocked APIs, context extraction)
- **Day 4**: Documentation
- **Day 5**: Run on full dandi-bib corpus (~200 papers)

---

## Success Metrics

### Context Extraction
- **Coverage**: Extract contexts for >90% of papers with PDFs
- **Accuracy**: Dataset mentions captured in >95% of cases
- **Speed**: Process 100 PDFs in <10 minutes

### Classification
- **Accuracy**: >80% agreement with manual classification
- **Confidence**: >70% of classifications have confidence >0.7
- **Cost**: <$5 for 1000 citations (using GPT-4.1 Nano)

### User Experience
- **Review speed**: Curators can review 50 low-confidence classifications in <30 minutes
- **Ease of use**: Single command to extract + classify

---

## Future Enhancements

1. **Section header extraction**: Improve context by identifying Methods/Results/Discussion
2. **Multi-modal analysis**: Use vision models to extract context from figures/tables
3. **Active learning**: Fine-tune LLM on curator feedback
4. **Batch optimization**: Cache LLM results, deduplicate similar contexts
5. **Integration with find_reuse**: Cross-validate discovered citations

---

## References

- [LLM Integration Plan](./llm-integration-plan.md) - Full LLM backend details
- [Tooling Integration Plan](./tooling-integration-plan.md) - Original tooling roadmap
- [Phase 1 Completion Summary](./phase1-completion-summary.md) - Schema changes
