from __future__ import annotations

import re
import sys
from datetime import (
    date,
    datetime,
    time
)
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    ClassVar,
    Literal,
    Optional,
    Union
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer
)


metamodel_version = "None"
version = "0.2.0"


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias = True,
        validate_by_name = True,
        validate_assignment = True,
        validate_default = True,
        extra = "forbid",
        arbitrary_types_allowed = True,
        use_enum_values = True,
        strict = False,
    )

    @model_serializer(mode='wrap', when_used='unless-none')
    def treat_empty_lists_as_none(
            self, handler: SerializerFunctionWrapHandler,
            info: SerializationInfo) -> dict[str, Any]:
        if info.exclude_none:
            _instance = self.model_copy()
            for field, field_info in type(_instance).model_fields.items():
                if getattr(_instance, field) == [] and not(
                        field_info.is_required()):
                    setattr(_instance, field, None)
        else:
            _instance = self
        return handler(_instance, info)



class LinkMLMeta(RootModel):
    root: dict[str, Any] = {}
    model_config = ConfigDict(frozen=True)

    def __getattr__(self, key:str):
        return getattr(self.root, key)

    def __getitem__(self, key:str):
        return self.root[key]

    def __setitem__(self, key:str, value):
        self.root[key] = value

    def __contains__(self, key:str) -> bool:
        return key in self.root


linkml_meta = LinkMLMeta({'default_prefix': 'citations',
     'default_range': 'string',
     'description': 'Schema for tracking scholarly citations of digital products '
                    '(datasets, software, tools) identified by DOIs, RRIDs, or '
                    'other identifiers. Supports flexible hierarchical collections '
                    'and curation workflows.',
     'id': 'https://w3id.org/dandi/citations-collector',
     'imports': ['linkml:types'],
     'license': 'MIT',
     'name': 'citations-collector',
     'prefixes': {'citations': {'prefix_prefix': 'citations',
                                'prefix_reference': 'https://w3id.org/dandi/citations-collector/'},
                  'cito': {'prefix_prefix': 'cito',
                           'prefix_reference': 'http://purl.org/spar/cito/'},
                  'datacite': {'prefix_prefix': 'datacite',
                               'prefix_reference': 'https://purl.org/datacite/v4.4/'},
                  'dcterms': {'prefix_prefix': 'dcterms',
                              'prefix_reference': 'http://purl.org/dc/terms/'},
                  'fabio': {'prefix_prefix': 'fabio',
                            'prefix_reference': 'http://purl.org/spar/fabio/'},
                  'foaf': {'prefix_prefix': 'foaf',
                           'prefix_reference': 'http://xmlns.com/foaf/0.1/'},
                  'linkml': {'prefix_prefix': 'linkml',
                             'prefix_reference': 'https://w3id.org/linkml/'},
                  'schema': {'prefix_prefix': 'schema',
                             'prefix_reference': 'http://schema.org/'}},
     'source_file': 'schema/citations.yaml',
     'title': 'Citations Collector Schema'} )

class RefType(str, Enum):
    """
    Type of identifier reference.
    """
    doi = "doi"
    """
    Digital Object Identifier (version-specific).
    """
    rrid = "rrid"
    """
    Research Resource Identifier (SciCrunch).
    """
    arxiv = "arxiv"
    """
    arXiv preprint identifier.
    """
    pmid = "pmid"
    """
    PubMed identifier.
    """
    pmcid = "pmcid"
    """
    PubMed Central identifier.
    """
    url = "url"
    """
    Generic URL (fallback when no persistent ID available).
    """
    zenodo_concept = "zenodo_concept"
    """
    Zenodo concept DOI or parent.id representing ALL versions. Example: "10.5281/zenodo.1012598" or just "1012598". System will auto-discover all version DOIs via Zenodo API (query: parent.id:1012598&f=allversions:true).
    """
    zenodo_version = "zenodo_version"
    """
    Zenodo version-specific record ID (resolves to DOI).
    """
    github = "github"
    """
    GitHub repository (owner/repo format).
    """


class CitationRelationship(str, Enum):
    """
    The relationship between a citing work and the cited item. Aligned with CiTO (Citation Typing Ontology) and DataCite relationship types.
    """
    Cites = "Cites"
    """
    The work explicitly cites the item in its references.
    """
    IsDocumentedBy = "IsDocumentedBy"
    """
    The item is documented by this work (e.g., a data descriptor).
    """
    Describes = "Describes"
    """
    The work describes the item or its creation methodology.
    """
    IsSupplementedBy = "IsSupplementedBy"
    """
    The item is supplemented by this work.
    """
    References = "References"
    """
    The work references the item without formal citation.
    """
    Uses = "Uses"
    """
    The work uses data/code from the item.
    """
    IsDerivedFrom = "IsDerivedFrom"
    """
    The work is derived from the item.
    """


class CitationType(str, Enum):
    """
    The type of citing work. Aligned with FaBiO (FRBR-aligned Bibliographic Ontology) and schema.org types.
    """
    Publication = "Publication"
    """
    Peer-reviewed journal article or conference paper.
    """
    Preprint = "Preprint"
    """
    Non-peer-reviewed preprint (bioRxiv, arXiv, etc.).
    """
    Protocol = "Protocol"
    """
    Published protocol (protocols.io, etc.).
    """
    Thesis = "Thesis"
    """
    Doctoral or master's thesis.
    """
    Book = "Book"
    """
    Book or book chapter.
    """
    Software = "Software"
    """
    Software package or tool.
    """
    Dataset = "Dataset"
    """
    Another dataset that cites this one.
    """
    Other = "Other"
    """
    Other type of work.
    """


class CitationSource(str, Enum):
    """
    The source from which the citation was discovered.
    """
    crossref = "crossref"
    """
    Discovered via CrossRef cited-by API.
    """
    opencitations = "opencitations"
    """
    Discovered via OpenCitations (OCI) API.
    """
    datacite = "datacite"
    """
    Discovered via DataCite API.
    """
    openalex = "openalex"
    """
    Discovered via OpenAlex API.
    """
    europepmc = "europepmc"
    """
    Discovered via Europe PMC API.
    """
    semantic_scholar = "semantic_scholar"
    """
    Discovered via Semantic Scholar API.
    """
    scicrunch = "scicrunch"
    """
    Discovered via SciCrunch/RRID API.
    """
    manual = "manual"
    """
    Manually added by curator.
    """


class CitationStatus(str, Enum):
    """
    Curation status of the citation.
    """
    active = "active"
    """
    Citation is valid and should be included.
    """
    ignored = "ignored"
    """
    Citation is a false positive and should be excluded.
    """
    merged = "merged"
    """
    Citation has been merged into another (e.g., preprint → published).
    """
    pending = "pending"
    """
    Citation needs review by curator.
    """



class ItemRef(ConfiguredBaseModel):
    """
    A resolvable identifier for an item (DOI, RRID, URL, etc.). An item may have multiple refs (e.g., both RRID and Zenodo DOI).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/dandi/citations-collector'})

    ref_type: RefType = Field(default=..., description="""Type of identifier.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ItemRef', 'SourceConfig']} })
    ref_value: str = Field(default=..., description="""The identifier value. Format depends on ref_type: - doi: \"10.1234/example\" (without doi: prefix) - rrid: \"SCR_016216\" (without RRID: prefix) - arxiv: \"2301.12345\" - pmid: \"12345678\" - url: full URL - zenodo: record