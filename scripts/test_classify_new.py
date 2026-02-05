#!/usr/bin/env python3
"""Test new classification metadata architecture on dandi-bib data."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from citations_collector.classifications_storage import (
    ClassificationsStorage,
)
from citations_collector.llm.base import ClassificationResult
from citations_collector.models import (
    CitationRelationship,
    ClassificationMethod,
)
from citations_collector.persistence import tsv_io


def test_classification_workflow():
    """Demonstrate the new classification workflow."""
    print("=" * 80)
    print("Testing New Classification Metadata Architecture")
    print("=" * 80)
    print()

    # Setup paths
    dandi_bib_dir = Path("/home/yoh/proj/dandi/dandi-bib/citations")
    tsv_path = dandi_bib_dir / "dandi-full-citations.tsv"
    pdfs_dir = dandi_bib_dir / "pdfs"

    # Load existing citations
    print(f"Loading citations from {tsv_path}...")
    citations = tsv_io.load_citations(tsv_path)
    print(f"✓ Loaded {len(citations)} citations")
    print()

    # Find a citation to update
    test_doi = "10.64898/2026.01.08.698522"
    test_item_id = "dandi.000020"

    test_citation = next(
        (c for c in citations if c.citation_doi == test_doi and c.item_id == test_item_id),
        None,
    )

    if not test_citation:
        print(f"Error: Test citation not found ({test_doi}, {test_item_id})")
        return

    print(f"Test citation: {test_doi}")
    print(f"  Item: {test_item_id} ({test_citation.item_flavor})")
    print(f"  Current relationship: {test_citation.citation_relationship}")
    print(f"  Current method: {test_citation.classification_method}")
    print()

    # Simulate LLM classification
    print("Simulating LLM classification...")
    mock_result = ClassificationResult(
        relationship_type="Uses",
        confidence=0.92,
        reasoning=(
            "Paper analyzes neural recordings from the Patch-seq dataset "
            "to study low-dimensional manifolds organizing neuronal responses."
        ),
        context_used=[
            (
                "Allen Institute for Brain Science (2021) Patch-seq recordings "
                "from mouse visual cortex..."
            ),
            (
                "Electrophysiological recordings were obtained from the publicly "
                "available Allen Institute for Brain Science Patch-seq dataset..."
            ),
        ],
    )

    print(f"  Classified as: {mock_result.relationship_type}")
    print(f"  Confidence: {mock_result.confidence:.2f}")
    print(f"  Reasoning: {mock_result.reasoning[:100]}...")
    print()

    # Save to classifications.json
    print("Saving detailed result to classifications.json...")
    storage = ClassificationsStorage(pdfs_dir)

    storage.add_classification(
        doi=test_doi,
        item_id=test_item_id,
        item_flavor=test_citation.item_flavor,
        result=mock_result,
        model="google.gemma-3-27b-it",
        backend="dartmouth",
        mode="short_context",
    )

    classifications_file = storage.get_classifications_file(test_doi)
    print(f"✓ Saved to: {classifications_file}")
    print()

    # Load and display
    print("Reading back classifications.json...")
    classifications = storage.get_classifications_for_item(
        test_doi, test_item_id, test_citation.item_flavor
    )

    for c in classifications:
        print(f"  Model: {c.model}")
        print(f"  Backend: {c.backend}")
        print(f"  Relationship: {c.relationship_type}")
        print(f"  Confidence: {c.confidence}")
        print(f"  Mode: {c.mode}")
        print(f"  Timestamp: {c.timestamp}")
        print(f"  Reasoning: {c.reasoning[:80]}...")
    print()

    # Update citation record with metadata
    print("Updating citation record with classification metadata...")
    updated_citation = test_citation.model_copy(
        update={
            "citation_relationship": CitationRelationship.Uses,
            "citation_relationships": [CitationRelationship.Uses],
            "classification_method": ClassificationMethod.llm,
            "classification_model": "google.gemma-3-27b-it",
            "classification_confidence": 0.92,
            "classification_reviewed": False,
        }
    )

    # Replace in list
    idx = citations.index(test_citation)
    citations[idx] = updated_citation

    print("✓ Updated citation record")
    print()

    # Save TSV
    output_tsv = dandi_bib_dir / "dandi-full-citations-test.tsv"
    print(f"Saving updated TSV to {output_tsv}...")
    tsv_io.save_citations(citations, output_tsv)
    print("✓ Saved")
    print()

    # Verify saved TSV
    print("Verifying saved TSV...")
    reloaded = tsv_io.load_citations(output_tsv)
    test_reloaded = next(
        (c for c in reloaded if c.citation_doi == test_doi and c.item_id == test_item_id),
        None,
    )

    if test_reloaded:
        print(f"✓ Reloaded citation for {test_doi}")
        print(f"  classification_method: {test_reloaded.classification_method}")
        print(f"  classification_model: {test_reloaded.classification_model}")
        print(f"  classification_confidence: {test_reloaded.classification_confidence}")
        print(f"  classification_reviewed: {test_reloaded.classification_reviewed}")
    print()

    # Check TSV columns
    print("Checking TSV structure...")
    with open(output_tsv) as f:
        header = f.readline().strip().split("\t")

    classification_cols = [col for col in header if col.startswith("classification_")]
    print(f"✓ Classification columns in TSV ({len(classification_cols)}):")
    for col in classification_cols:
        print(f"    - {col}")
    print()

    # Simulate adding another model's result
    print("Simulating second model classification (Claude Haiku)...")
    mock_result2 = ClassificationResult(
        relationship_type="CitesAsDataSource",
        confidence=0.85,
        reasoning="Work explicitly cites the Patch-seq dataset as a data source for analysis.",
        context_used=[""],
    )

    storage.add_classification(
        doi=test_doi,
        item_id=test_item_id,
        item_flavor=test_citation.item_flavor,
        result=mock_result2,
        model="anthropic.claude-haiku-4-5",
        backend="dartmouth",
        mode="short_context",
    )

    print("✓ Added second model result")
    print()

    # Show model comparison
    print("Comparing models for this citation...")
    all_classifications = storage.get_classifications_for_item(
        test_doi, test_item_id, test_citation.item_flavor
    )

    print(f"Found {len(all_classifications)} classifications:")
    for c in all_classifications:
        print(f"  {c.model:35} → {c.relationship_type:20} (conf: {c.confidence:.2f})")
    print()

    # Demonstrate selection strategies
    print("Selection strategies:")
    print("  1. Highest confidence:")
    best_by_conf = max(all_classifications, key=lambda x: x.confidence)
    print(
        f"     → {best_by_conf.model}: {best_by_conf.relationship_type} "
        f"({best_by_conf.confidence:.2f})"
    )
    print()

    print("  2. Model priority (prefer Gemma):")
    preferred = next(
        (c for c in all_classifications if "gemma" in c.model.lower()),
        all_classifications[0],
    )
    print(
        f"     → {preferred.model}: {preferred.relationship_type} " f"({preferred.confidence:.2f})"
    )
    print()

    print("=" * 80)
    print("✓ Test Complete!")
    print("=" * 80)
    print()
    print("Files created:")
    print(f"  - {classifications_file}")
    print(f"  - {output_tsv}")
    print()


if __name__ == "__main__":
    try:
        test_classification_workflow()
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
