# Citation Analysis & Reclassification Tooling Plan

## Context

We've added 5 new dataset-specific citation relationship types to improve classification beyond generic "Cites". Now we need tools to:

1. **Reclassify** existing citations from generic "Cites" to specific relationships
2. **Analyze** citation patterns and multi-dataset usage
3. **Integrate** with related projects in the neuroscience data ecosystem

## Related Projects

### 1. [Neuro-D3](https://github.com/Neuro-D3/neurod3)

**What it does:**
- **Dataset Discovery Platform**: Aggregates datasets from DANDI, Kaggle, OpenNeuro, PhysioNet
- **Citation Tracking**: Monitors how shared datasets are cited and reused
- **Dark Data Identification**: Finds papers sharing/reusing datasets

**Architecture:**
- Apache Airflow pipelines for metadata ingestion
- PostgreSQL database for datasets + citations
- FastAPI backend + React frontend dashboard

**Relationship to our tool:**
- **NeuroD3 is a consumer** of citation data
- Our citations-collector could **feed NeuroD3's database**
- They track citations at **platform level** (cross-repository)
- We track citations at **dataset level** (granular, relationship-typed)

**Integration opportunity:**
- Export our TSV → NeuroD3 PostgreSQL schema
- Share classification heuristics
- Provide API for their citation ingestion pipeline

---

### 2. [find_reuse](https://github.com/catalystneuro/find_reuse)

**What it does:**
- **Forward tracking**: Given paper DOI → finds what datasets it mentions
- Extracts dataset IDs from DANDI, OpenNeuro, Figshare, PhysioNet
- Follows citation chains (e.g., to data descriptor papers)
- Searches Europe PMC, PubMed Central, CrossRef, publisher HTMLs

**Relationship to our tool:**
- **Complementary direction**:
  - find_reuse: **paper → datasets** (what does this paper use?)
  - our tool: **dataset → papers** (what cites this dataset?)
- **Overlapping discovery**: Both find the same relationships from different angles
- **Different granularity**: find_reuse finds mentions; we classify citation types

**Integration opportunity:**
- **Bidirectional validation**: Cross-check discoveries
- **Citation type inference**: Use find_reuse's text extraction to auto-classify relationships
- **Mutual enrichment**: Combine forward + backward tracking for complete picture

**Example integration:**
```python
# Paper 10.1234/example mentions DANDI:000003 (from find_reuse)
# DANDI:000003 is cited by 10.1234/example (from citations-collector)
# → Merge: We have the relationship, they have the full text context
```

---

## Proposed Tooling Architecture

### Tool 1: Citation Reclassification Assistant

**Purpose**: Help curators migrate existing "Cites" relationships to specific types

**Approach**: **Hybrid** (automated suggestions + human review)

**Components**:

#### 1a. Heuristic Classifier

```python
# scripts/classify_citations.py

def suggest_relationship(citation: CitationRecord) -> list[tuple[CitationRelationship, float]]:
    """
    Suggest relationship types with confidence scores.

    Returns:
        List of (relationship, confidence) tuples, ordered by confidence
    """
    suggestions = []

    # High-confidence rules (80-95% confidence)
    if citation.citation_journal == "Scientific Data":
        suggestions.append((CitationRelationship.IsDocumentedBy, 0.95))

    if "review" in citation.citation_title.lower():
        suggestions.append((CitationRelationship.Reviews, 0.85))

    # Medium-confidence rules (60-80% confidence)
    if re.search(r"algorithm|method|framework", citation.citation_title, re.I):
        suggestions.append((CitationRelationship.CitesAsEvidence, 0.70))

    # Check for multi-dataset patterns
    if has_same_doi_citations(citation):
        suggestions.append((CitationRelationship.Compiles, 0.75))

    # Default: Use (moderate confidence)
    if not suggestions:
        suggestions.append((CitationRelationship.Uses, 0.50))

    return sorted(suggestions, key=lambda x: x[1], reverse=True)
```

**Rules** (from citation-pattern-analysis.md):
- Journal="Scientific Data" → IsDocumentedBy (95%)
- Journal="Nature Reviews *" → Reviews (90%)
- Title contains "dataset|resource|atlas" + high-impact journal → IsDocumentedBy (80%)
- Title contains "method|algorithm|framework" → CitesAsEvidence (70%)
- Title contains "review|survey" → Reviews (85%)
- Same DOI, multiple datasets → Compiles (75%)
- Default → Uses (50%)

#### 1b. find_reuse Integration (Text-based)

```python
# Enhance classification using find_reuse's text extraction

from find_reuse import extract_datasets_from_paper

def enhanced_classification(citation: CitationRecord) -> CitationRelationship:
    """
    Use find_reuse to extract full text context and improve classification.
    """
    # Get paper full text via find_reuse
    mentions = extract_datasets_from_paper(citation.citation_doi)

    # Analyze context around dataset mention
    for mention in mentions:
        if mention.dataset_id == citation.item_id:
            context = mention.surrounding_text

            # Look for key phrases
            if "we analyzed" in context or "using data from" in context:
                return CitationRelationship.Uses
            elif "this dataset describes" in context:
                return CitationRelationship.IsDocumentedBy
            elif "we validated" in context:
                return CitationRelationship.CitesAsEvidence

    # Fallback to heuristic
    return suggest_relationship(citation)[0][0]
```

**Usage**:
```bash
# Classify all "Cites" relationships in a TSV
python scripts/classify_citations.py \
    dandi-citations.tsv \
    --output dandi-classified.tsv \
    --confidence-threshold 0.70 \
    --use-find-reuse  # Optional: use text extraction
    --review-ambiguous  # Interactive review for low-confidence

# Output:
# ✓ 60 citations auto-classified (confidence > 0.70)
# ⚠ 20 citations need review (confidence < 0.70)
# → Review mode: press 1-5 to select relationship type
```

---

### Tool 2: Multi-Dataset Analysis Utilities

**Purpose**: Discover and analyze patterns in how papers cite multiple datasets

**Components**:

#### 2a. Co-Citation Network Builder

```python
# scripts/analyze_co_citations.py

def build_co_citation_network(citations: list[CitationRecord]) -> nx.Graph:
    """
    Build network of datasets co-cited in papers.

    Returns NetworkX graph where:
    - Nodes = datasets
    - Edges = papers citing both (weight = count)
    """
    G = nx.Graph()

    # Group citations by paper DOI
    papers = defaultdict(list)
    for c in citations:
        if c.citation_doi:
            papers[c.citation_doi].append(c.item_id)

    # Create edges for co-cited pairs
    for doi, datasets in papers.items():
        if len(datasets) > 1:
            for ds1, ds2 in combinations(sorted(datasets), 2):
                if G.has_edge(ds1, ds2):
                    G[ds1][ds2]['weight'] += 1
                    G[ds1][ds2]['papers'].append(doi)
                else:
                    G.add_edge(ds1, ds2, weight=1, papers=[doi])

    return G

# Usage:
# python scripts/analyze_co_citations.py dandi-citations.tsv --output co_citation_network.json
# → Generates network for visualization in Cytoscape, Gephi, etc.
```

#### 2b. Meta-Analysis Pattern Detector

```python
# scripts/find_meta_analyses.py

def find_multi_dataset_papers(citations: list[CitationRecord]) -> pd.DataFrame:
    """
    Find papers citing multiple datasets (meta-analyses, federated studies).
    """
    df = pd.DataFrame([c.model_dump() for c in citations])

    multi = df.groupby('citation_doi').agg({
        'item_id': list,
        'citation_title': 'first',
        'citation_relationships': lambda x: list(x)[0],
        'citation_journal': 'first',
    }).query('item_id.str.len() > 1')

    # Add analysis columns
    multi['dataset_count'] = multi['item_id'].str.len()
    multi['has_compiles'] = multi['citation_relationships'].apply(
        lambda x: 'Compiles' in str(x) if x else False
    )

    return multi.sort_values('dataset_count', ascending=False)

# Usage:
# python scripts/find_meta_analyses.py dandi-citations.tsv
#
# Output:
# DOI                        Title                           Datasets                      Count
# 10.1234/meta-2024         "Federated analysis of..."      [000003, 000020, 000055]      3
# 10.5678/multi-site        "Multi-site validation..."      [000108, 000126]              2
```

#### 2c. Citation Timeline Analyzer

```python
# scripts/timeline_analysis.py

def analyze_citation_timeline(citations: list[CitationRecord]) -> pd.DataFrame:
    """
    Analyze how citation patterns evolve over time.
    """
    df = pd.DataFrame([c.model_dump() for c in citations])

    # Citations by year and relationship type
    timeline = df.groupby(['citation_year', 'citation_relationships']).size()

    # Identify trends
    # - Are more recent papers using specific relationship types?
    # - Which datasets have sustained vs. declining citation rates?
    # - Do relationship types correlate with journal prestige?

    return timeline

# Usage:
# python scripts/timeline_analysis.py dandi-citations.tsv --plot timeline.png
```

---

### Tool 3: NeuroD3 Integration Exporter

**Purpose**: Export citation data in format compatible with NeuroD3 platform

**Components**:

#### 3a. TSV → PostgreSQL Schema Mapper

```python
# scripts/export_to_neurod3.py

def export_for_neurod3(
    citations: list[CitationRecord],
    output_format: str = "json"
) -> None:
    """
    Export citations in NeuroD3-compatible format.

    NeuroD3 schema (inferred):
    - datasets table: id, name, repository, doi, created_date
    - papers table: doi, title, authors, journal, year
    - citations table: paper_doi, dataset_id, relationship_type, discovered_date
    """
    # Generate three files matching NeuroD3 structure
    datasets = extract_unique_datasets(citations)
    papers = extract_unique_papers(citations)
    citation_links = [
        {
            "paper_doi": c.citation_doi,
            "dataset_id": c.item_id,
            "relationship_type": str(c.citation_relationship),
            "discovered_date": c.discovered_date,
            "sources": c.citation_sources,
        }
        for c in citations
    ]

    # Export in requested format
    if output_format == "json":
        with open("neurod3_export.json", "w") as f:
            json.dump({
                "datasets": datasets,
                "papers": papers,
                "citations": citation_links,
            }, f, indent=2)
    elif output_format == "sql":
        generate_postgres_inserts(datasets, papers, citation_links)

# Usage:
# python scripts/export_to_neurod3.py dandi-citations.tsv --format json
# → Produces neurod3_export.json for NeuroD3 ingestion pipeline
```

---

### Tool 4: Bidirectional Citation Validator

**Purpose**: Cross-validate with find_reuse discoveries

**Workflow**:

```python
# scripts/validate_with_find_reuse.py

def cross_validate(our_citations: list[CitationRecord]) -> ValidationReport:
    """
    Compare our discoveries with find_reuse to identify:
    - Papers we found that find_reuse didn't (missing forward references)
    - Papers find_reuse found that we didn't (missing backward citations)
    - Discrepancies in dataset IDs
    """
    from find_reuse import run_discovery

    # Get all unique paper DOIs from our citations
    our_dois = {c.citation_doi for c in our_citations if c.citation_doi}

    # For each paper, check what find_reuse discovers
    discrepancies = []
    for doi in our_dois:
        our_datasets = {c.item_id for c in our_citations if c.citation_doi == doi}
        their_datasets = set(run_discovery(doi))

        # Check for mismatches
        if our_datasets != their_datasets:
            discrepancies.append({
                "doi": doi,
                "we_found": our_datasets - their_datasets,
                "they_found": their_datasets - our_datasets,
            })

    return ValidationReport(discrepancies)

# Usage:
# python scripts/validate_with_find_reuse.py dandi-citations.tsv
#
# Output:
# ⚠️  Found 5 discrepancies:
#
# DOI: 10.1234/example
#   We found: DANDI:000108 (from CrossRef metadata)
#   They found: DANDI:000109 (from full text)
#   → Investigate: Are both correct? Different datasets mentioned?
```

---

## Recommended Implementation Sequence

### Phase 1: Core Tools (2-3 weeks)

**Week 1**: Citation Reclassification Assistant
- Implement heuristic classifier
- Test on example TSV files
- Measure accuracy vs. manual classification
- Build interactive review mode

**Week 2**: Multi-Dataset Analysis
- Build co-citation network tool
- Implement meta-analysis detector
- Add timeline analysis

**Week 3**: Testing & Documentation
- Integration tests with real data
- User documentation
- Tutorial notebooks

### Phase 2: External Integration (2-3 weeks)

**Week 4**: find_reuse Integration
- Set up find_reuse as dependency
- Implement text-based enhancement
- Cross-validation script

**Week 5**: NeuroD3 Export
- Define export schema
- Implement converters
- Test with NeuroD3 team

**Week 6**: Feedback & Iteration
- Gather feedback from DANDI curators
- Refine classification rules
- Improve accuracy

### Phase 3: Automation (optional, 1-2 weeks)

**Week 7-8**: Continuous Integration
- GitHub Actions for auto-classification
- Scheduled runs on DANDI citation updates
- API endpoints for real-time classification

---

## Collaboration Opportunities

### With NeuroD3 Team

1. **Data Sharing**: Export our classified citations → their platform
2. **Feedback Loop**: Their curation insights → improve our classifiers
3. **Unified Ontology**: Align on relationship type vocabulary
4. **Cross-Repository**: Extend our tools to OpenNeuro, PhysioNet

### With find_reuse Team

1. **Bidirectional Discovery**: Combine forward + backward tracking
2. **Text Context**: Use their extraction to improve classification
3. **Coverage Comparison**: Identify gaps in both tools
4. **Shared Heuristics**: Pool classification rules

### With DANDI Team

1. **Curator Workflows**: Design tools around their needs
2. **Quality Metrics**: Track citation data quality over time
3. **Incentive Metrics**: Show researchers citation impact
4. **Public API**: Expose citation data for community use

---

## Open Questions

1. **Classification accuracy targets**: What's acceptable auto-classification accuracy? 70%? 80%?

2. **Human-in-the-loop**: Should reclassification always require curator approval, or trust high-confidence predictions?

3. **find_reuse integration depth**:
   - Option A: Light integration (just cross-validation)
   - Option B: Deep integration (use their text extraction in our pipeline)
   - Recommendation: Start with A, move to B if valuable

4. **NeuroD3 schema compatibility**: Do they want raw TSV, JSON, or direct PostgreSQL inserts?

5. **Multi-dataset citation comments**: Should we enforce structured format (JSON in citation_comment field) or free text?

6. **Community standards**: Should we propose relationship types to broader neuroscience data community (e.g., via INCF, NWB)?

---

## Success Metrics

### For Tools

- **Reclassification accuracy**: >75% match with curator decisions
- **Coverage**: Classify >90% of citations with confidence >0.6
- **Speed**: Process 1000 citations in <1 minute
- **Usability**: Curators can reclassify 100 citations in <30 minutes

### For Integration

- **NeuroD3**: Successfully export >5000 classified citations
- **find_reuse**: Cross-validation identifies <5% discrepancies
- **Community**: 3+ external users/teams adopt tools

### For Impact

- **Data quality**: Reduce generic "Cites" from 100% → <20%
- **Insights**: Identify top 10 multi-dataset papers
- **Reuse tracking**: Measure dataset reuse rates by type

---

## Next Steps

1. **Review with stakeholders** (DANDI, NeuroD3, find_reuse teams)
2. **Prioritize tools** based on immediate curator needs
3. **Build MVP** of reclassification assistant (1-2 weeks)
4. **Test on real data** with 10-20 curators
5. **Iterate** based on feedback
6. **Scale** to full citation corpus

---

## References

- NeuroD3: https://github.com/Neuro-D3/neurod3
- find_reuse: https://github.com/catalystneuro/find_reuse
- Our plan: `.specify/specs/dataset-citation-relationships.md`
- Our analysis: `.specify/specs/citation-pattern-analysis.md`
