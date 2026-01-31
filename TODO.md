# TODO List

## Per-Source Incremental Discovery

**Problem:** Current incremental mode uses a single global "most recent discovery date" across all sources. This means if you query CrossRef today and DataCite last week, incremental mode will use today's date for both, missing potential DataCite citations.

**Current behavior:**
```python
# Gets max(discovered_date) across ALL citations, regardless of source
since = self._get_most_recent_discovery_date()
# Applies same 'since' date to ALL sources
for source_name, discoverer in discoverers:
    citations = discoverer.discover(ref, since=since)
```

**Desired behavior:**
```python
# Get most recent date PER SOURCE
since_dates = {
    "crossref": max discovery date from crossref citations,
    "datacite": max discovery date from datacite citations,
    "opencitations": max discovery date from opencitations citations,
    "openalex": max discovery date from openalex citations,
}
# Apply source-specific date
for source_name, discoverer in discoverers:
    since = since_dates.get(source_name)
    citations = discoverer.discover(ref, since=since)
```

**Implementation:**
1. Modify `_get_most_recent_discovery_date()` to return `dict[str, datetime]`
2. Update `discover_all()` to use per-source dates
3. Schema already supports `citation_source` field - no changes needed there

**Workaround:** Use `--full-refresh` flag to disable incremental mode entirely.

**Priority:** Medium - incremental mode is an optimization, not required for correctness
