# Dataset Citation Relationships: Schema Extension Plan

## Executive Summary

Our current schema supports basic citation relationships but needs extension to accurately capture the rich variety of ways scientific papers interact with datasets. This plan proposes adding dataset-specific relationship types aligned with CiTO (Citation Typing Ontology) and DataCite, based on analysis of actual DANDI citations and neuroscience data sharing practices.

**Current State**: All 94 DANDI citations are classified as generic "Cites"
**Proposed State**: 6 new specific relationship types covering data descriptor papers, reuse patterns, validation, reviews, and multi-dataset aggregation

**Key Design Decision**: Multi-dataset citations are handled through **multiple TSV rows** sharing the same `citation_doi`, not through schema complexity. This leverages the natural structure of the data for maximum flexibility.

## Motivation

### Real-World Citation Patterns from DANDI

Analysis of `/home/yoh/proj/dandi/dandi-bib/citations/dandi-full-citations.tsv` (94 citations, 35 PDFs/HTMLs collected) reveals:

1. **Data Descriptor Papers** (~40%): Scientific Data journal papers describing new datasets that cite DANDI datasets
   - Example: "AJILE12: Long-term naturalistic human intracranial neural recordings and pose"
   - Current: Classified as "Cites"
   - Should be: "IsDocumentedBy" or "Describes"

2. **Data Reuse for Analysis** (~45%): Papers using DANDI data for new scientific findings
   - Example: "An emerging view of neural geometry in motor cortex supports high-performance decoding"
   - Current: Classified as "Cites"
   - Should be: "Uses" or "UsesDataFrom"

3. **Tool/Tutorial Papers** (~10%): Educational or infrastructure papers
   - Example: "nwb4edu: an Online Textbook for Teaching and Learning with NWB Datasets"
   - Current: Classified as "Cites"
   - Should be: "References" or "CitesForInformation"

4. **Method Validation** (~5%): Papers benchmarking algorithms on public datasets
   - Example: "Combining SNNs with filtering for efficient neural decoding in implantable brain-machine interfaces"
   - Current: Classified as "Cites"
   - Should be: "CitesAsEvidence" or "UsesMethodIn"

### Key Findings from Literature

From [Data Citation in Neuroimaging (2016)](https://www.frontiersin.org/journals/neuroinformatics/articles/10.3389/fninf.2016.00034/full):

- **Three levels of data identification**: Image level, Project level, Functional level
- **Two primary reuse patterns**: Subsetting existing projects, Aggregating across multiple sources
- **Attribution inheritance**: Functional-level collections must maintain attribution chains from constituent images
- **Critical need**: "Measurable, standardized citations—comparable to publication references"

From [FAIR neuroscience data sharing (2024)](https://www.frontiersin.org/journals/neuroinformatics/articles/10.3389/fninf.2023.1276407/full):

- DANDI housed nearly a petabyte of data as of mid-2025
- Support for data citation through landing pages and DOIs
- Need for both item-level and source-level identifiers

From [Federated neuroimaging (2024-2025)](https://www.frontiersin.org/journals/aging-neuroscience/articles/10.3389/fnagi.2024.1324032/full):

- Multi-site collaborative analysis without centralizing data
- Aggregating data across institutions increases heterogeneity
- Need to track provenance when combining datasets from multiple sources

## Gap Analysis

### Missing Relationship Types

Our current schema has these CitationRelationship values:
- ✅ **Cites** - Generic citation (too broad)
- ✅ **IsDocumentedBy** - Item documented by work
- ✅ **Describes** - Work describes item
- ✅ **IsSupplementedBy** - Item supplemented by work
- ✅ **References** - Work references item
- ✅ **Uses** - Work uses data from item
- ✅ **IsDerivedFrom** - Work derived from item

### Missing but Critical for Datasets

From CiTO ontology ([sparontologies.github.io/cito](https://sparontologies.github.io/cito/)):

1. ❌ **CitesAsDataSource** (`cito:citesAsDataSource`)
   - "The citing entity cites the cited entity as source of data"
   - More specific than generic "Cites" for explicit data reuse
   - DataCite equivalent: `References`

2. ❌ **UsesDataFrom** (`cito:usesDataFrom`) - Already have "Uses"
   - ✅ We have this! Mapped to our "Uses" relationship
   - Should keep as primary for data analysis papers

3. ❌ **Reviews** (`cito:reviews`)
   - "The citing entity reviews statements, ideas or conclusions presented in the cited entity"
   - Critical for dataset evaluation papers
   - DataCite equivalent: `Reviews` / `IsReviewedBy`

4. ❌ **CitesAsSourceDocument** (`cito:citesAsSourceDocument`)
   - "The citing entity cites the cited entity as being the entity from which the citing entity is derived"
   - For papers creating derived/processed datasets
   - DataCite equivalent: `IsDerivedFrom` (we have this!)

5. ❌ **CitesAsEvidence** (`cito:citesAsEvidence`)
   - "The citing entity cites the cited entity as source of factual evidence"
   - For validation and benchmarking
   - Use case: "We validated our algorithm on DANDI:000003"

6. ❌ **Compiles** (`cito:compiles`)
   - "The citing entity is used to create or compile the cited entity"
   - Inverse: `isCompiledBy`
   - **Critical for multi-dataset aggregation**
   - Use case: "We combined data from DANDI:000003, 000020, and 000055"

7. ❌ **CitesForInformation** (`cito:citesForInformation`)
   - "The citing entity cites the cited entity as a source of information on the subject under discussion"
   - For background/contextual references
   - More specific than generic "References"

8. ❌ **Documents** - We have "Describes"
   - DataCite uses both `Documents` and `IsDocumentedBy`
   - ✅ We have "Describes" which maps to `cito:documents`

### Multi-Dataset Citation Challenges

**Problem**: Current schema assumes **one citing work → one cited dataset**

**Reality**: Papers increasingly:
1. **Aggregate multiple datasets** for meta-analysis ([Federated Learning papers 2024-2025](https://arxiv.org/html/2508.06589))
2. **Subset portions** of larger datasets ([Neuroimaging best practices](https://pmc.ncbi.nlm.nih.gov/articles/PMC4981598/))
3. **Create derivative collections** combining data from multiple sources

**Current approach works naturally**: Our `CitationRecord` model already handles this!

```
Paper 10.1234/meta-analysis → DANDI:000003  (row 1)
Paper 10.1234/meta-analysis → DANDI:000020  (row 2)
Paper 10.1234/meta-analysis → DANDI:000055  (row 3)
```

**The TSV already has a natural grouping key**: `citation_doi`

Finding multi-dataset papers is trivial with post-hoc analysis:
```python
import pandas as pd

# Find papers citing multiple datasets
multi_dataset = df.groupby('citation_doi').agg({
    'item_id': list,
    'citation_title': 'first'
}).query('item_id.str.len() > 1')

# Co-citation network
co_cited = df.groupby('citation_doi')['item_id'].apply(set)
```

**Solution**: Use existing fields creatively:
- **`citation_relationships`** = "Compiles" (indicates multi-dataset aggregation)
- **`citation_comment`** = "Combined with DANDI:000020, 000055" (documents co-citation)
- **Post-hoc grouping** by `citation_doi` discovers patterns without schema changes

**Advantage**: No schema complexity, maximum flexibility for analysis.

## Proposed Schema Extensions

### Phase 1: Add Missing CiTO Relationship Types

Add to `CitationRelationship` enum in `schema/citations.yaml`:

```yaml
CitationRelationship:
  permissible_values:
    # ... existing values ...

    CitesAsDataSource:
      description: >-
        The citing work explicitly cites the item as a source of data.
        More specific than generic Cites for data reuse scenarios.
      meaning: cito:citesAsDataSource
      exact_mappings:
        - datacite:References
      comments:
        - Use for papers that explicitly acknowledge using data from a dataset
        - Distinguishes data reuse from general citation

    Reviews:
      description: >-
        The citing work reviews or critically evaluates the cited dataset.
      meaning: cito:reviews
      exact_mappings:
        - datacite:Reviews
      comments:
        - Use for systematic reviews, dataset evaluations, quality assessments
        - Example: "A comprehensive review of publicly available EEG datasets"

    CitesAsEvidence:
      description: >-
        The citing work uses the cited dataset as evidence to support claims.
      meaning: cito:citesAsEvidence
      comments:
        - Use for validation studies, benchmarking, method comparison
        - Example: "We validated our algorithm against DANDI:000003"
        - Distinguishes from active data reuse (Uses/UsesDataFrom)

    Compiles:
      description: >-
        The citing work compiles or aggregates data from multiple datasets including this one.
      meaning: cito:compiles
      inverse: cito:isCompiledBy
      comments:
        - Use for meta-analyses combining multiple datasets
        - Should be combined with citation_comment listing other datasets
        - Example: "Meta-analysis combining DANDI:000003, 000020, 000055"

    CitesForInformation:
      description: >-
        The citing work cites the dataset as background information or context.
      meaning: cito:citesForInformation
      comments:
        - Use for contextual/background references
        - More specific than generic References
        - Example: Tutorial mentioning dataset availability

    ObtainsSupportFrom:
      description: >-
        The citing work obtains data, conclusions, or support from the cited dataset.
      meaning: cito:obtainsSupportFrom
      broad_mappings:
        - datacite:IsDerivedFrom
      comments:
        - Use when work builds upon or extends dataset findings
        - Less specific than IsDerivedFrom but broader than Uses
```

### Phase 2: Data Provenance for Derived Datasets (Future)

When papers **describe new datasets derived from DANDI**, track the derivation:

```yaml
CitationRecord:
  attributes:
    # ... existing fields ...

    derives_dataset:
      description: >-
        DOI or identifier of a new dataset created by the citing work
        that is derived from the cited item.
      range: string
      pattern: "^10\\..+/.+$"
      examples:
        - "10.5281/zenodo.1234567"
      comments:
        - Use when paper describes a derived/processed dataset
        - Maintains provenance chain: Original → Derived

    derivation_type:
      description: >-
        How the derived dataset relates to the source.
      range: DerivationType

DerivationType:
  description: >-
    Type of derivation from source dataset to new dataset.
  permissible_values:
    Subset:
      description: Selected portion of original data (e.g., specific subjects, sessions)
    Processed:
      description: Transformed/processed version (e.g., spike-sorted, preprocessed)
    Aggregated:
      description: Combined with other datasets
    Analyzed:
      description: Analysis outputs derived from source data
    Annotated:
      description: Original data with added annotations/labels
```

## Implementation Plan

### Step 1: Research & Validation (Current)

- [x] Review CiTO ontology for dataset-specific relationships
- [x] Review DataCite relationship types
- [x] Analyze actual DANDI citations (94 citations in TSV)
- [x] Review neuroscience data sharing literature
- [ ] **Sample PDF/HTML analysis** - Manually review 20 collected papers to validate relationship type classification

### Step 2: PDF/HTML Content Analysis

**Task**: Manually review collected papers to understand citation context

**Method**:
1. Sample 20 papers (mix of Scientific Data, eLife, J Neuroscience, JOSS)
2. For each, extract:
   - How is DANDI dataset mentioned? (Methods, Results, Introduction, Data Availability)
   - What verbs describe dataset use? ("analyzed", "used", "validated against", "describes")
   - Is it primary data source or background reference?
   - Does it combine multiple datasets?
3. Create mapping of language patterns → relationship types

**Expected patterns**:
- "We analyzed data from DANDI:000003" → **Uses/UsesDataFrom**
- "This dataset is available at DANDI:000003" → **IsDocumentedBy**
- "We validated our method on DANDI:000003" → **CitesAsEvidence**
- "We combined datasets DANDI:000003, 000020" → **Compiles** + citation_comment

**Deliverable**: `dataset-citation-patterns.md` with examples

### Step 3: Schema Updates

1. Add new `CitationRelationship` values (Phase 1)
2. Regenerate Pydantic models
3. Update TSV column validation
4. Add migration notes to README

### Step 4: Bulk Reclassification Tool

Create tool to help reclassify existing "Cites" relationships:

```python
# scripts/reclassify_citations.py

def suggest_relationship(citation: CitationRecord) -> list[CitationRelationship]:
    """Suggest relationship types based on heuristics."""
    suggestions = []

    # Data descriptor journals → IsDocumentedBy
    if citation.citation_journal in ["Scientific Data", "Data in Brief"]:
        suggestions.append(CitationRelationship.IsDocumentedBy)

    # Method/tool papers → CitesAsEvidence or References
    if citation.citation_journal in ["JOSS", "Neuromorphic Computing"]:
        suggestions.append(CitationRelationship.CitesAsEvidence)

    # Title contains "dataset", "data descriptor" → IsDocumentedBy
    if re.search(r"dataset|data descriptor", citation.citation_title, re.I):
        suggestions.append(CitationRelationship.IsDocumentedBy)

    # Title contains "analysis", "decoding", "model" → Uses
    if re.search(r"analysis|decoding|neural dynamics|population", citation.citation_title, re.I):
        suggestions.append(CitationRelationship.Uses)

    # Multiple datasets in comment → Compiles
    if citation.citation_comment and "DANDI:" in citation.citation_comment:
        suggestions.append(CitationRelationship.Compiles)

    return suggestions or [CitationRelationship.Cites]
```

### Step 5: Documentation & Examples

Update README with:
- Expanded relationship type guide
- Examples for each relationship type
- Multi-dataset citation best practices
- Migration guide for old TSV files

Example table:

| Scenario | Relationship(s) | Example |
|----------|----------------|---------|
| Paper describes new dataset released on DANDI | `IsDocumentedBy` | Scientific Data descriptor paper |
| Paper uses DANDI data for new analysis | `Uses` | "We analyzed motor cortex data from DANDI:000003" |
| Paper validates algorithm on DANDI dataset | `CitesAsEvidence` | "Benchmarked on DANDI:000020" |
| Paper combines multiple DANDI datasets | `Compiles` (+ citation_comment) | 3 TSV rows, same DOI, comment: "Combined with 000020, 000055" |
| Paper mentions DANDI in background | `References` or `CitesForInformation` | Tutorial or review mentioning availability |
| Paper reviews/evaluates DANDI datasets | `Reviews` | "Quality assessment of public EEG data" |
| Paper creates derived dataset from DANDI | `IsDerivedFrom` (+ derives_dataset) | Spike-sorted version of raw data |
| Paper uses data AND describes its methodology | `Uses`, `Describes` | Both analyze and document methods |

### Step 6: Testing

1. Create test cases for all new relationship types
2. Test TSV round-trip with new relationships
3. Test multi-relationship combinations
4. Validate CiTO/DataCite mappings

### Step 6b: Multi-Dataset Analysis Utilities (Optional)

Provide helper functions to discover multi-dataset patterns:

```python
# scripts/analyze_multi_dataset.py

def find_multi_dataset_papers(citations: list[CitationRecord]) -> pd.DataFrame:
    """Find papers citing multiple datasets."""
    df = pd.DataFrame([c.model_dump() for c in citations])

    multi = df.groupby('citation_doi').agg({
        'item_id': list,
        'citation_title': 'first',
        'citation_relationships': 'first'
    }).query('item_id.str.len() > 1')

    return multi

def build_co_citation_network(citations: list[CitationRecord]) -> dict:
    """Build dataset co-citation network."""
    from collections import defaultdict
    from itertools import combinations

    co_citations = defaultdict(int)

    # Group by paper DOI
    papers = {}
    for c in citations:
        if c.citation_doi:
            papers.setdefault(c.citation_doi, []).append(c.item_id)

    # Count co-citations
    for datasets in papers.values():
        if len(datasets) > 1:
            for pair in combinations(sorted(datasets), 2):
                co_citations[pair] += 1

    return dict(co_citations)

# Example usage:
# python -m scripts.analyze_multi_dataset dandi-citations.tsv
```

**Example output**:
```
Multi-dataset papers found: 12

DOI: 10.1234/meta-analysis-2024
  Datasets: DANDI:000003, DANDI:000020, DANDI:000055
  Relationship: Compiles

DOI: 10.5678/federated-study
  Datasets: DANDI:000108, DANDI:000126, DANDI:000140
  Relationship: Compiles

Co-citation network:
  (DANDI:000003, DANDI:000020): 8 papers
  (DANDI:000003, DANDI:000055): 8 papers
  (DANDI:000020, DANDI:000055): 8 papers
```

**Rationale**: The TSV structure naturally supports this analysis. No schema changes needed.

### Step 7: Community Feedback

1. Share plan with DANDI team
2. Review with data citation experts
3. Validate against real curator workflows
4. Refine based on feedback

## Research Sources

### Ontologies & Standards
- [CiTO (Citation Typing Ontology)](https://sparontologies.github.io/cito/) - SPAR ontologies for scholarly communication
- [DataCite Metadata Schema v4.5](https://datacite-metadata-schema.readthedocs.io/en/4.5/) - Relationship types for research data
- [DataCite relationTypes](https://datacite-metadata-schema.readthedocs.io/en/4.5/appendices/appendix-1/relationType/) - Full list of relation types

### Neuroscience Data Citation
- [Data Citation in Neuroimaging (2016)](https://www.frontiersin.org/journals/neuroinformatics/articles/10.3389/fninf.2016.00034/full) - Best practices for neuroimaging data
- [FAIR neuroscience data sharing (2024)](https://www.frontiersin.org/journals/neuroinformatics/articles/10.3389/fninf.2023.1276407/full) - Current state of FAIR practices
- [Twenty Years of Neuroinformatics (2025)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11735507/) - Bibliometric analysis

### Multi-Dataset Analysis
- [Federated Learning for Alzheimer's Detection (2024)](https://www.frontiersin.org/journals/aging-neuroscience/articles/10.3389/fnagi.2024.1324032/full)
- [Federated Learning in Distributed Neuroimaging (2024)](https://www.frontiersin.org/journals/neuroinformatics/articles/10.3389/fninf.2024.1430987/full)
- [Scientific Data for Machine Learning (2025)](https://www.nature.com/articles/s41597-025-04402-4)

### Dataset Examples
- DANDI Archive citations: `/home/yoh/proj/dandi/dandi-bib/citations/dandi-full-citations.tsv`
- Collected papers: `/home/yoh/proj/dandi/dandi-bib/citations/pdfs/` (35 PDFs/HTMLs)

## Next Steps

1. **Manual PDF Review** (2-3 hours)
   - Review 20 papers from `/home/yoh/proj/dandi/dandi-bib/citations/pdfs/`
   - Document citation language patterns
   - Validate proposed relationship types against real usage

2. **Community Discussion** (async)
   - Share this plan with DANDI team
   - Get feedback from data curators
   - Validate relationship type definitions

3. **Schema Implementation** (1-2 days)
   - Add Phase 1 relationship types
   - Create migration documentation
   - Build reclassification helper tool

4. **Testing & Validation** (1 day)
   - Test all relationship types
   - Validate ontology mappings
   - Ensure TSV backward compatibility

5. **Deployment** (ongoing)
   - Update DANDI citations with better classification
   - Monitor usage patterns
   - Iterate based on curator feedback

## Questions for Discussion

1. **Granularity**: Are 6 new relationship types sufficient, or should we add more specific types (e.g., separate "Benchmarks" from "CitesAsEvidence")?

2. **Backward compatibility**: How should we handle bulk reclassification of existing 94 "Cites" relationships? Manual curation or automated suggestions?

3. **Derivation tracking**: Is tracking `derives_dataset` important for DANDI, or should we defer Phase 2 (future work)?

4. **Multi-dataset validation**: Should we add helper functions to validate/enforce citation_comment when using "Compiles" relationship?

5. **Analysis tools**: Should we provide built-in utilities to discover multi-dataset patterns from TSV files, or leave this to users?

## Timeline Estimate

- **Step 1** (Research): ✅ Complete
- **Step 2** (PDF Analysis): 3-4 hours
- **Step 3** (Schema Updates): 2-3 hours
- **Step 4** (Reclassification Tool): 4-6 hours
- **Step 5** (Documentation): 2-3 hours
- **Step 6** (Testing): 3-4 hours
- **Step 7** (Feedback): Async, 1-2 weeks

**Total development time**: ~2-3 days of focused work
**Total calendar time**: 2-3 weeks including feedback cycles
