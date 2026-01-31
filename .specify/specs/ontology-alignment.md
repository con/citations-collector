# Ontology Alignment Documentation

## Overview

The citations-collector schema is aligned with established scholarly communication ontologies to enable semantic interoperability, RDF export, and integration with knowledge graphs. This document describes the alignment strategy, mappings, and benefits.

## Aligned Ontologies

### Primary Ontologies

1. **CiTO - Citation Typing Ontology**
   - **URI:** http://purl.org/spar/cito/
   - **Purpose:** Citation relationships and characterizations
   - **Source:** https://github.com/sparontologies/cito
   - **Used for:** CitationRelationship enum values

2. **FaBiO - FRBR-aligned Bibliographic Ontology**
   - **URI:** http://purl.org/spar/fabio/
   - **Purpose:** Bibliographic resource types
   - **Source:** https://sparontologies.github.io/fabio/
   - **Used for:** CitationType enum values

3. **DataCite Metadata Schema**
   - **URI:** https://purl.org/datacite/v4.4/
   - **Purpose:** Research data identifiers and relationships
   - **Source:** https://schema.datacite.org/
   - **Used for:** DOI identifiers and relationship types

4. **schema.org**
   - **URI:** http://schema.org/
   - **Purpose:** General web semantics and structured data
   - **Source:** https://schema.org
   - **Used for:** Core classes and properties

5. **Dublin Core Metadata Terms**
   - **URI:** http://purl.org/dc/terms/
   - **Purpose:** Core metadata vocabulary
   - **Source:** https://www.dublincore.org/specifications/dublin-core/dcmi-terms/
   - **Used for:** Basic metadata properties

6. **FOAF - Friend of a Friend**
   - **URI:** http://xmlns.com/foaf/0.1/
   - **Purpose:** People and organizations
   - **Source:** http://xmlns.com/foaf/spec/
   - **Used for:** Homepage URLs

## Mapping Mechanisms

### LinkML Mapping Types

The schema uses three levels of semantic binding:

1. **`class_uri` / `slot_uri`** (Strong Binding)
   - Direct reuse of the ontology term URI
   - Use when LinkML element has identical semantics
   - Example: `class_uri: schema:Collection`

2. **`meaning`** (Primary Mapping)
   - Primary semantic interpretation for enum values
   - Example: `meaning: cito:cites` for the "Cites" relationship

3. **`exact_mappings`** (Equivalent Terms)
   - Multiple equivalent terms from different vocabularies
   - Use when there are synonymous concepts
   - Example: `exact_mappings: [schema:name, dcterms:title]`

4. **`broad_mappings` / `related_mappings`** (Hierarchical/Related)
   - Approximate or hierarchical relationships
   - Use when match is not exact
   - Example: `broad_mappings: [schema:CreativeWork]`

## Class Mappings

### Collection

```yaml
class_uri: schema:Collection
exact_mappings:
  - dcterms:Collection
```

**Rationale:** Represents a curated collection of scholarly resources, aligned with schema.org's Collection type.

### Item

```yaml
class_uri: schema:CreativeWork
exact_mappings:
  - dcterms:Resource
```

**Rationale:** Items are creative works (datasets, software, publications) that can be cited. CreativeWork is the most general type in schema.org that encompasses all these.

### CitationRecord

```yaml
class_uri: cito:CitationAct
exact_mappings:
  - datacite:Relation
```

**Rationale:** A citation record represents an act of citation (CiTO) and a relationship between resources (DataCite).

## Enum Mappings

### CitationRelationship

Maps scholarly citation relationships to CiTO properties:

| Value | CiTO URI | DataCite | Description |
|-------|----------|----------|-------------|
| **Cites** | `cito:cites` | `datacite:Cites` | General citation |
| **IsDocumentedBy** | `cito:isDocumentedBy` | `datacite:IsDocumentedBy` | Data descriptor relationship |
| **Describes** | `cito:documents` | `datacite:Describes` | Work documents the item |
| **IsSupplementedBy** | `cito:isSupplementedBy` | `datacite:IsSupplementedBy` | Supplementary material |
| **Uses** | `cito:usesDataFrom` | `datacite:Cites` | Data usage citation |
| **IsDerivedFrom** | (broad) `cito:obtainsSupportFrom` | `datacite:IsDerivedFrom` | Derivation relationship |

**CiTO Properties Verified:**
- All mappings verified against authoritative source: https://github.com/sparontologies/cito
- Uses inverse properties appropriately (e.g., `isDocumentedBy` vs `documents`)
- All CiTO properties are subproperties of either `cito:cites` or `cito:isCitedBy`

### CitationType

Maps scholarly work types to FaBiO classes and schema.org types:

| Value | FaBiO URI | schema.org | Description |
|-------|-----------|------------|-------------|
| **Publication** | `fabio:JournalArticle` | `schema:ScholarlyArticle` | Peer-reviewed article |
| **Preprint** | `fabio:Preprint` | (related) `schema:ScholarlyArticle` | Non-peer-reviewed |
| **Protocol** | `fabio:ExperimentalProtocol` | (broad) `schema:HowTo` | Research protocol |
| **Thesis** | `fabio:Thesis` | `schema:Thesis` | Academic thesis |
| **Book** | `fabio:Book` | `schema:Book` | Book or chapter |
| **Software** | `fabio:ComputerProgram` | `schema:SoftwareSourceCode` | Software package |
| **Dataset** | `fabio:Dataset` | `schema:Dataset` | Research dataset |

## Slot Mappings

### Core Metadata Slots

| Slot | Mappings | Notes |
|------|----------|-------|
| `name` | `schema:name`, `dcterms:title` | Human-readable title |
| `description` | `schema:description`, `dcterms:description` | Textual description |
| `homepage` | `schema:url`, `foaf:homepage` | Landing page URL |
| `citation_doi` | `datacite:doi`, `schema:identifier` | DOI identifier |
| `citation_title` | `dcterms:title`, `schema:name` | Work title |
| `citation_authors` | `dcterms:creator`, `schema:author` | Authors (semicolon-separated) |
| `citation_year` | `dcterms:issued`, `schema:datePublished` | Publication year |
| `citation_relationship` | (slot_uri) `cito:hasCitationCharacterization` | Relationship type |
| `citation_type` | `dcterms:type`, `schema:additionalType` | Resource type |

## Benefits

### Immediate Benefits (Current Implementation)

1. **Semantic Precision**
   - Citations now have precise, machine-readable meanings
   - Relationships align with scholarly communication standards

2. **Interoperability**
   - Schema is compatible with RDF/JSON-LD export
   - Can integrate with institutional repositories, knowledge graphs

3. **FAIR Compliance**
   - **F**indable: Ontology terms are resolvable URIs
   - **A**ccessible: Standard vocabularies ensure broad access
   - **I**nteroperable: Aligned with established schemas
   - **R**eusable: Clear semantic definitions enable reuse

4. **Standards Alignment**
   - Compatible with DataCite, CrossRef, OpenCitations
   - Follows SPAR (Semantic Publishing and Referencing Ontologies) best practices

### Future Capabilities

1. **RDF Export**
   ```turtle
   @prefix cito: <http://purl.org/spar/cito/> .
   @prefix fabio: <http://purl.org/spar/fabio/> .

   <https://doi.org/10.1234/citing-paper>
       a fabio:JournalArticle ;
       cito:usesDataFrom <https://doi.org/10.48324/dandi.000003> .
   ```

2. **SPARQL Queries**
   - Query citation networks across systems
   - Example: "Find all datasets cited by publications in Nature"

3. **Knowledge Graph Integration**
   - Export to Wikidata with proper relationship types
   - Integration with institutional repositories (DSpace, EPrints)
   - Compatibility with DataCite/CrossRef graphs

4. **Automated Reasoning**
   - Infer preprint→publication relationships
   - Detect citation patterns and clusters

## Examples

### Example 1: Dataset Citation with Data Usage

**TSV Record:**
```tsv
item_id: dandi:000003
citation_doi: 10.1038/s41586-2024-12345
citation_relationship: Uses
```

**Semantic Interpretation:**
- The publication (10.1038/s41586-2024-12345)
- **uses data from** (`cito:usesDataFrom`)
- The DANDI dataset (dandi:000003)

**RDF Export:**
```turtle
<https://doi.org/10.1038/s41586-2024-12345>
    cito:usesDataFrom <https://doi.org/10.48324/dandi.000003> .
```

### Example 2: Data Descriptor Publication

**TSV Record:**
```tsv
item_id: dandi:000003
citation_doi: 10.1038/sdata.2024.56789
citation_relationship: IsDocumentedBy
citation_type: Publication
```

**Semantic Interpretation:**
- The dataset is documented by (`cito:isDocumentedBy`)
- A journal article (`fabio:JournalArticle`)
- In Nature Scientific Data

**RDF Export:**
```turtle
<https://doi.org/10.48324/dandi.000003>
    cito:isDocumentedBy <https://doi.org/10.1038/sdata.2024.56789> .

<https://doi.org/10.1038/sdata.2024.56789>
    a fabio:JournalArticle ;
    schema:name "Data descriptor for DANDI dataset 000003" .
```

## Backward Compatibility

**Important:** All ontology mappings are **purely additive**. They do not affect existing functionality:

- **YAML/TSV serialization:** Unchanged
- **Python API:** Unchanged (Pydantic models identical)
- **Existing data:** Fully compatible, no migration needed
- **Enum values:** Existing values preserved with added semantics

**What changes:**
- RDF/JSON-LD export now uses ontology URIs
- Schema documentation is richer
- Future tools can leverage semantic mappings

## Testing & Validation

### Validation Steps

1. **Schema Compilation**
   ```bash
   gen-pydantic schema/citations.yaml > src/citations_collector/models/generated.py
   gen-json-schema schema/citations.yaml > schema/citations.schema.json
   ```

2. **Backward Compatibility**
   - Load existing YAML/TSV files with updated schema
   - Verify all fields parse correctly
   - Check that enum values still validate

3. **Ontology URI Resolution**
   - Verify all mapped URIs are resolvable
   - Check CiTO, FaBiO, DataCite vocabularies are accessible

4. **Future: RDF Export**
   - Export collection to JSON-LD
   - Validate against schema.org and SPAR ontologies
   - Query with SPARQL

## Extending the Alignment

### Adding New Relationship Types

To add a new citation relationship (e.g., from CiTO):

1. Find the CiTO property at https://sparontologies.github.io/cito/current/cito.html
2. Add to `CitationRelationship` enum:
   ```yaml
   UsesMethodIn:
     description: The work uses methods from the item.
     meaning: cito:usesMethodIn
     exact_mappings:
       - datacite:Cites
   ```
3. Update discovery modules if needed
4. Regenerate models: `gen-pydantic schema/citations.yaml`

### Adding New Work Types

To add a new work type:

1. Find FaBiO class at https://sparontologies.github.io/fabio/current/fabio.html
2. Add to `CitationType` enum:
   ```yaml
   ConferencePaper:
     description: Conference paper or proceedings article.
     meaning: fabio:ConferencePaper
     exact_mappings:
       - schema:ScholarlyArticle
   ```
3. Update OpenAlex/CrossRef type mappers
4. Regenerate models

## References

### Official Ontology Sources

- **CiTO GitHub:** https://github.com/sparontologies/cito
- **CiTO HTML Docs:** https://sparontologies.github.io/cito/current/cito.html
- **FaBiO HTML Docs:** https://sparontologies.github.io/fabio/current/fabio.html
- **DataCite Schema:** https://schema.datacite.org/
- **schema.org:** https://schema.org
- **Dublin Core:** https://www.dublincore.org/specifications/dublin-core/dcmi-terms/

### LinkML Documentation

- **LinkML URIs and Mappings:** https://linkml.io/linkml/schemas/uris-and-mappings.html
- **LinkML Best Practices:** https://linkml.io/linkml/intro/tutorial.html

### Related Standards

- **SPAR Ontologies:** http://www.sparontologies.net/
- **COAR Vocabulary:** https://vocabularies.coar-repositories.org/
- **DataCite Relations:** https://support.datacite.org/docs/connecting-to-works

## Implementation Phases

### ✅ Phase 1: Core Mappings (Completed)

- Added ontology prefixes
- Mapped core classes (Collection, Item, CitationRecord)
- Mapped all enum values with CiTO and FaBiO
- Mapped core metadata slots
- Backward compatible, no breaking changes

### 🔄 Phase 2: Enhanced Relationships (Future)

- Add `UsesMethodIn`, `CitesAsDataSource` relationship types
- Add `ConferencePaper` work type
- Update discovery modules to detect new types
- Provide migration guide

### 📋 Phase 3: Structured Metadata (Future)

- Implement Person class for structured authors
- Add structured identifier handling
- Parallel support for old string/new structured formats
- Deprecate string-based fields in v1.0

### 🎯 Phase 4: RDF Export (Future)

- Implement JSON-LD export
- Add RDF/Turtle serialization
- SPARQL endpoint integration
- Knowledge graph utilities

## Version History

- **v0.2.0** (2026-01-31): Added ontology alignment (Phase 1)
  - Core class and enum mappings
  - CiTO, FaBiO, DataCite, schema.org alignment
  - Backward compatible

---

*Last updated: 2026-01-31*
