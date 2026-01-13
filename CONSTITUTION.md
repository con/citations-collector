# citations-collector Constitution

This document defines the guiding principles, design philosophy, and standards for the **citations-collector** project. All contributors should read and follow these guidelines.

## Mission

Provide a simple, reliable Python library and CLI for collecting scholarly citation metadata. The tool should be easy to use for researchers, integrate smoothly into scripts and pipelines, and remain maintainable by a small open-source community.

## Core Principles

### 1. Simplicity Over Features

- Keep the API surface small and focused
- One obvious way to accomplish each task
- Resist feature creep; new features must justify their complexity
- Prefer standard library solutions when adequate

### 2. Library-First Design

- Core functionality lives in `core.py` as a reusable library
- CLI (`cli.py`) is a thin wrapper around the library
- All functionality accessible programmatically, not just via CLI
- No CLI-only features

### 3. Reliability

- Graceful error handling with meaningful messages
- Network failures should not crash the program
- Return `None` or empty results rather than raising on missing data
- Comprehensive test coverage for all code paths

### 4. Modern Python

- Target Python 3.10+ only (no legacy compatibility burden)
- Use type hints throughout (`py.typed` package)
- Leverage modern syntax: dataclasses, f-strings, `|` unions
- Follow PEP standards

## Code Standards

### Style

- **Line length**: 100 characters maximum
- **Linting**: Ruff with rules E, W, F, I, B, C4, UP, SIM
- **Formatting**: Ruff format (consistent with Black)
- **Imports**: Sorted by isort (via Ruff)

### Type Hints

- All public functions must have complete type annotations
- Use `from __future__ import annotations` for forward references
- Run mypy in CI; type errors are build failures

### Documentation

- Module-level docstrings explaining purpose
- Class and public method docstrings (Google style)
- README covers installation and common use cases
- No excessive inline comments; code should be self-explanatory

### Testing

- Tests live in `tests/` directory
- Use pytest as the test framework
- Mock external APIs with `responses` library
- Test both success and error paths
- AI-generated tests must be marked with `@pytest.mark.ai_generated`
- Target high coverage but prioritize meaningful tests over metrics

## Architecture

```
src/citations_collector/
├── __init__.py      # Version and public API exports
├── core.py          # CitationCollector class, Citation dataclass
├── cli.py           # Click-based CLI commands
└── py.typed         # PEP 561 marker
```

### Boundaries

- `core.py`: No CLI dependencies, no user interaction
- `cli.py`: Thin layer for argument parsing and output formatting
- Tests: No network calls; all HTTP mocked

### Dependencies

**Runtime** (keep minimal):
- `click` - CLI framework
- `requests` - HTTP client

**Development** (via extras):
- `pytest`, `pytest-cov`, `pytest-timeout` - testing
- `responses` - HTTP mocking
- `ruff` - linting/formatting
- `mypy`, `types-requests` - type checking
- `tox`, `tox-uv` - test automation

Adding new runtime dependencies requires justification and discussion.

## API Stability

- Public API: `Citation`, `CitationCollector`, `collect_citations()`
- CLI commands: `fetch`, `search`, `list`
- Breaking changes require version bump and changelog entry
- Internal functions (prefixed with `_`) may change without notice

## Contribution Guidelines

### Getting Started

```bash
git clone <repo>
cd citations-collector
uv venv && source .venv/bin/activate
uv pip install -e ".[devel]"
```

### Before Submitting

1. Run tests: `tox -e py3`
2. Run linter: `tox -e lint`
3. Run type checker: `tox -e type`
4. Ensure all CI checks pass

### Pull Request Standards

- One logical change per PR
- Clear description of what and why
- Tests for new functionality
- Update docs if user-facing behavior changes

### Review Process

- All changes require review before merge
- Be respectful and constructive in reviews
- Prefer suggestions over demands
- Small, incremental PRs merge faster

## Versioning

- Follow Semantic Versioning (SemVer)
- Version derived from git tags via `hatch-vcs`
- Tag format: `v1.2.3`

## License

MIT License - permissive, simple, widely compatible.

## Governance

- Maintainers have final say on design decisions
- Major changes should be discussed in issues first
- Community input is valued but consensus is not required
- "Rough consensus and running code" over endless debate

---

*This constitution may evolve. Propose changes via pull request with rationale.*
