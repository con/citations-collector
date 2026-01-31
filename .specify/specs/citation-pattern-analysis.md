# Citation Pattern Analysis (Manual Review)

## Data Source

Analyzed citations from example TSV files:
- `examples/microns-citations.tsv` (largest dataset, best titles)
- `examples/repronim-tools-citations.tsv`
- `examples/dandi-citations.tsv`

**Current state**: All citations classified as generic "Cites"

## Observed Patterns

### Pattern 1: Data Descriptor Papers (~15-20%)

**Journals**: Nature, Scientific Data, Nature Communications, Nature Methods

**Title patterns**:
- Contains "dataset", "connectome", "resource", "atlas"
- Published in data-focused journals

**Examples**:
- "An fMRI dataset in response to 'The Grand Budapest Hotel', a socially-rich, naturalistic movie" (Scientific Data)
- "A connectomic resource for neural cataloguing and circuit dissection of the larval zebrafish brain"
- "A Developmental Atlas of the Drosophila Nerve Cord"

**Proposed relationship**: `IsDocumentedBy` or `Describes`

**Rationale**: These papers ARE the dataset or describe datasets that cite/use the infrastructure

---

### Pattern 2: Data Analysis/Research Papers (~60-70%)

**Journals**: Nature, Cell, Neuron, PNAS, eLife

**Title patterns**:
- Contains analysis verbs: "reveals", "traces", "predicts", "identifies"
- Scientific findings about neural function, circuits, behavior
- NO mention of "dataset" or "resource"

**Examples**:
- "Inhibitory specificity from a connectomic census of mouse visual cortex" (Nature)
- "Foundation model of neural activity predicts response to new stimulus types" (Nature)
- "Functional connectomics reveals general wiring rule in mouse visual cortex" (Nature)
- "Distinct circuit motifs evaluate opposing innate values of odors" (Cell)
- "Distinct dendritic integration strategies control dynamics of inhibition in the neocortex" (Neuron)

**Proposed relationship**: `Uses` / `UsesDataFrom` or `CitesAsDataSource`

**Rationale**: These papers actively analyze/use the dataset to generate new scientific insights

---

### Pattern 3: Method/Tool Papers (~10-15%)

**Journals**: Nature Methods, Bioinformatics, various technical journals

**Title patterns**:
- Contains "method", "approach", "framework", "tool", "algorithm"
- Focus on technical advancement rather than biological findings

**Examples**:
- "VSOT: volume-surface optimization for accurate ultrastructure analysis of dendritic spines" (Bioinformatics)
- "InterpolAI: deep learning-based optical flow interpolation and restoration of biomedical images for improved 3D tissue mapping" (Nature Methods)
- "SmartEM: machine-learning guided electron microscopy"
- "PyReconstruct: A fully open-source, collaborative successor to Reconstruct" (PNAS)

**Proposed relationship**: `CitesAsEvidence` (if validated on dataset) or `Uses` (if applied to dataset)

**Rationale**: These papers use datasets for method validation/demonstration

---

### Pattern 4: Review/Survey Papers (~5-10%)

**Title patterns**:
- Contains "review", "survey", "perspectives", "advances"
- Broader scope than individual studies

**Examples**:
- "Synaptic connectomics: status and prospects" (Nature Reviews Neuroscience)
- "Advancements in neuromorphic computing for bio-inspired artificial vision: A review" (Neurocomputing)
- "Complicated architecture of cortical microcircuit: a comprehensive review" (Anatomical Science International)

**Proposed relationship**: `Reviews` or `References` / `CitesForInformation`

**Rationale**: These papers survey the field and mention datasets as context

---

### Pattern 5: Modeling/Theoretical Papers (~5%)

**Title patterns**:
- Contains "model", "theory", "simulation", "computational"
- Mathematical/theoretical focus

**Examples**:
- "Statistical mechanics for networks of real neurons" (Reviews of Modern Physics)
- "Bridging macroscopic and microscopic modeling of electric field by brain stimulation" (Brain Stimulation)
- "Importance of considering microscopic structures in modeling brain stimulation"

**Proposed relationship**: `Uses` (if model uses dataset) or `References` (if dataset mentioned for context)

**Rationale**: May use dataset for model building or cite it as relevant context

---

## Classification Heuristics

Based on this analysis, here are suggested rules for automated classification:

### High-confidence rules:

1. **Journal = "Scientific Data"** → `IsDocumentedBy`
   - Scientific Data exclusively publishes data descriptor papers

2. **Journal = "Nature Reviews *"** → `Reviews`
   - Review journals primarily synthesize literature

3. **Title contains "dataset" OR "resource" OR "atlas" OR "collection"**
   - AND Journal in {Nature, Cell, PNAS, Nature Communications}
   - → `IsDocumentedBy`

4. **Title contains method/tool keywords**:
   - "algorithm", "method", "approach", "framework", "tool", "software", "package"
   - → `CitesAsEvidence` (if validation focus) or `Uses` (if application focus)

5. **Title contains "review" OR "survey" OR "perspectives"**
   - → `Reviews`

### Medium-confidence rules:

6. **Title contains analysis verbs + no dataset keywords**:
   - "reveals", "identifies", "predicts", "traces", "demonstrates", "shows"
   - → `Uses` / `UsesDataFrom`

7. **Title about neural circuits/function + high-impact journal**:
   - Journals: Nature, Cell, Neuron, Science
   - → `Uses` / `UsesDataFrom`

### Ambiguous cases:

Need human review when:
- Title is generic or unclear
- Journal is not in known categories
- Multiple patterns match

## Validation Against Proposed Relationship Types

### ✅ Strongly Validated:

1. **Uses/UsesDataFrom** - 60-70% of citations fit this pattern
   - Clear evidence of papers actively analyzing datasets

2. **IsDocumentedBy/Describes** - 15-20% of citations
   - Data descriptor papers are common

3. **CitesAsEvidence** - 10-15% of citations
   - Method papers frequently validate on datasets

4. **Reviews** - 5-10% of citations
   - Review papers regularly cite datasets

### ⚠️ Partially Validated:

5. **CitesAsDataSource** - Overlaps heavily with "Uses"
   - May be redundant with UsesDataFrom
   - **Recommendation**: Consider merging or making UsesDataFrom more specific

6. **CitesForInformation** - Similar to "References"
   - Background/contextual citations
   - **Recommendation**: Keep for tutorials, background mentions

### ❓ Not Observed (Yet):

7. **Compiles** - Multi-dataset aggregation
   - Not visible in single-TSV analysis
   - Need to check for papers citing multiple datasets with same DOI
   - **Recommendation**: Keep for meta-analyses (validated in literature review)

8. **ObtainsSupportFrom** - Building on dataset findings
   - Unclear distinction from "Uses"
   - **Recommendation**: Consider deferring or merging with IsDerivedFrom

## Recommendations for Phase 1 Implementation

### Must Add (High Priority):

1. **CitesAsDataSource** - Rename/clarify as more specific than generic "Cites"
2. **Reviews** - Clear pattern in data
3. **CitesAsEvidence** - Method validation pattern

### Should Add (Medium Priority):

4. **Compiles** - For multi-dataset papers (validated in literature)
5. **CitesForInformation** - For background/tutorial references

### Consider Deferring:

6. **ObtainsSupportFrom** - Unclear distinction, overlap with Uses/IsDerivedFrom
   - Defer to Phase 2 if needed

## Next Steps

1. **Implement 5 core relationship types** (skip ObtainsSupportFrom for now):
   - CitesAsDataSource
   - Reviews
   - CitesAsEvidence
   - Compiles
   - CitesForInformation

2. **Create classification heuristic tool** based on rules above

3. **Test on example TSV files** to measure accuracy

4. **Gather curator feedback** on ambiguous cases
