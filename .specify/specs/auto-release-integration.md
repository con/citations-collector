# Auto-Release Integration Plan

This document outlines the steps to integrate `intuit/auto` for automated releases, following the dandi-cli pattern.

## Overview

Auto-release automation will:
1. Automatically create releases when PRs with `release` label merge to `master`
2. Generate changelog from PR titles and labels
3. Build and publish to PyPI automatically
4. Create GitHub releases with generated notes

## Required Files

### 1. `.autorc` Configuration

Create `.autorc` in repository root:

```json
{
    "baseBranch": "master",
    "name": "citations-collector-bot",
    "email": "bot@dandiarchive.org",
    "noVersionPrefix": true,
    "plugins": [
        "protected-branch",
        "git-tag",
        [
            "exec",
            {
                "afterRelease": "python -m build && twine upload dist/*"
            }
        ],
        "released"
    ]
}
```

### 2. GitHub Workflow `.github/workflows/release.yml`

```yaml
name: Auto-release on PR merge

on:
  push:
    branches:
      - master
  workflow_dispatch:

jobs:
  auto-release:
    runs-on: ubuntu-latest
    if: "!contains(github.event.head_commit.message, 'ci skip') && !contains(github.event.head_commit.message, 'skip ci')"
    steps:
      - name: Checkout source
        uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - name: Download latest auto
        run: |
          auto_download_url="$(curl -fsSL https://api.github.com/repos/intuit/auto/releases/latest | jq -r '.assets[] | select(.name == "auto-linux.gz") | .browser_download_url')"
          wget -O- "$auto_download_url" | gunzip > ~/auto
          chmod a+x ~/auto

      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: '3.12'

      - name: Install build & twine
        run: python -m pip install build twine

      - name: Create release
        run: |
          echo "@${{ github.actor }} is creating a release triggered by ${{ github.event_name }}"
          if [ "${{ github.event_name }}" = workflow_dispatch ]
          then opts=
          else opts=--only-publish-with-release-label
          fi
          ~/auto shipit -vv $opts
        env:
          PROTECTED_BRANCH_REVIEWER_TOKEN: ${{ secrets.GH_TOKEN }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
```

### 3. Update `CHANGELOG.md`

Convert to auto-compatible format:

```markdown
# CHANGELOG

This changelog is automatically generated using [auto](https://github.com/intuit/auto).

## 0.2.1 (Fri Jan 30 2026)

#### 🚀 Enhancement

- Add OpenAlex as a citation discovery source [#XXX](https://github.com/dandi/citations-collector/pull/XXX)
- Add dynamic source population for DANDI dandisets [#XXX](https://github.com/dandi/citations-collector/pull/XXX)
- Add multi-source citation tracking with coherence validation [#XXX](https://github.com/dandi/citations-collector/pull/XXX)

#### 🐛 Bug Fix

- Fix DataCite Event Data API query parameters [#XXX](https://github.com/dandi/citations-collector/pull/XXX)

#### 🏠 Internal

- Remove last_updated from Collection schema [#XXX](https://github.com/dandi/citations-collector/pull/XXX)
- Add tox environment for updating example citations [#XXX](https://github.com/dandi/citations-collector/pull/XXX)

#### Authors: 1

- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# Previous releases...
```

## Required GitHub Repository Labels

Create the following labels in the repository (Settings → Labels):

### Primary Release Labels
- **`release`** - Marks PR for automatic release on merge (required for auto-release)
- **`skip-release`** - Skip release even if other criteria met

### Category Labels (for changelog organization)
- **`enhancement`** / **`feature`** → 🚀 Enhancement
- **`bug`** / **`fix`** → 🐛 Bug Fix
- **`internal`** → 🏠 Internal
- **`documentation`** / **`docs`** → 📝 Documentation
- **`tests`** / **`testing`** → 🧪 Tests
- **`dependencies`** → 📦 Dependencies
- **`performance`** / **`perf`** → ⚡ Performance

### Version Bump Labels (optional, auto-determines from category if not set)
- **`major`** - Breaking changes (1.0.0 → 2.0.0)
- **`minor`** - New features (1.0.0 → 1.1.0)
- **`patch`** - Bug fixes (1.0.0 → 1.0.1)

## Required GitHub Secrets

Add these secrets in repository Settings → Secrets and variables → Actions:

1. **`PYPI_TOKEN`** - PyPI API token for publishing
   - Generate at https://pypi.org/manage/account/token/
   - Scope: Entire account or specific project

2. **`GH_TOKEN`** (optional) - GitHub Personal Access Token
   - Only needed if using protected-branch plugin
   - Generate at https://github.com/settings/tokens
   - Scope: `repo`, `workflow`

Note: `GITHUB_TOKEN` is automatically provided by GitHub Actions

## Workflow

### For Contributors

1. Create PR with descriptive title (becomes changelog entry)
2. Add appropriate labels:
   - Category label: `enhancement`, `bug`, `docs`, etc.
   - Version bump (if not auto-detected): `major`, `minor`, `patch`
3. For release: Add `release` label when ready

### For Maintainers

1. Review PR with `release` label
2. Merge to `master`
3. GitHub Actions automatically:
   - Determines version bump from labels
   - Updates `CHANGELOG.md`
   - Creates git tag (e.g., `v0.2.2`)
   - Builds package: `python -m build`
   - Publishes to PyPI: `twine upload dist/*`
   - Creates GitHub release with changelog

### Manual Release

If needed, trigger manually:
```bash
gh workflow run release.yml
```

Or use local `auto`:
```bash
npm install -g auto
auto shipit
```

## Migration Steps

1. **Create `.autorc`** in repo root
2. **Create `.github/workflows/release.yml`**
3. **Convert `CHANGELOG.md`** to auto format
4. **Create labels** in GitHub repo (see list above)
5. **Add secrets** (`PYPI_TOKEN`, optionally `GH_TOKEN`)
6. **Test with dry-run**:
   ```bash
   npm install -g auto
   auto shipit --dry-run
   ```
7. **Create test PR** with `release` label and `patch` label
8. **Verify workflow** executes on merge

## Benefits

✅ **Automated releases** - No manual version bumping, tagging, or PyPI uploads
✅ **Consistent changelogs** - Auto-generated from PR titles and labels
✅ **Clear versioning** - Semantic versioning enforced via labels
✅ **GitHub releases** - Automatic with detailed notes
✅ **Reduced errors** - No forgetting to update CHANGELOG or tag releases
✅ **Better collaboration** - Clear labels indicate change type and release intent

## Best Practices

1. **Write descriptive PR titles** - They become changelog entries
2. **Use conventional commits** - For clarity in labels
3. **Test before `release` label** - Add label only when ready to ship
4. **One feature per PR** - Easier to categorize and track
5. **Update CHANGELOG manually** - For major releases or complex changes

## Resources

- [auto documentation](https://intuit.github.io/auto/)
- [dandi-cli example](https://github.com/dandi/dandi-cli)
- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)

## Rollback Plan

If auto-release causes issues:

1. **Disable workflow**: Rename `.github/workflows/release.yml` to `.yml.disabled`
2. **Manual releases**: Use `git tag` and `python -m build && twine upload dist/*`
3. **Fix and re-enable**: Address issues and restore workflow
