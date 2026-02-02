#!/bin/bash
# Automated workflow for DANDI-BIB citation collection and classification
#
# This script can be run manually or via cron to:
# 1. Discover new citations
# 2. Fetch PDFs for new citations
# 3. Extract contexts from PDFs
# 4. Classify citations with LLM
# 5. (Optional) Sync to Zotero
#
# Usage:
#   ./scripts/run-dandi-bib-workflow.sh [dandi-bib-dir]
#
# Environment variables:
#   SKIP_DISCOVER=1        Skip citation discovery
#   SKIP_PDFS=1           Skip PDF fetching
#   SKIP_EXTRACTION=1     Skip context extraction
#   SKIP_CLASSIFICATION=1 Skip LLM classification
#   SYNC_ZOTERO=1         Enable Zotero sync
#   DRY_RUN=1             Run in dry-run mode

set -e

# Colors
BOLD=$(tput bold)
RESET=$(tput sgr0)
GREEN=$(tput setaf 2)
YELLOW=$(tput setaf 3)
RED=$(tput setaf 1)

# Configuration
DANDI_BIB_DIR="${1:-/home/yoh/proj/dandi/dandi-bib}"
COLLECTION="${DANDI_BIB_DIR}/collection.yaml"
LOG_DIR="${DANDI_BIB_DIR}/logs"
LOG_FILE="${LOG_DIR}/workflow-$(date +%Y%m%d-%H%M%S).log"

# Create log directory
mkdir -p "$LOG_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

error() {
    echo "${RED}[ERROR]${RESET} $*" | tee -a "$LOG_FILE" >&2
}

info() {
    echo "${GREEN}[INFO]${RESET} $*" | tee -a "$LOG_FILE"
}

warn() {
    echo "${YELLOW}[WARN]${RESET} $*" | tee -a "$LOG_FILE"
}

# Banner
echo "${BOLD}╔════════════════════════════════════════════════════════════════╗${RESET}"
echo "${BOLD}║  DANDI-BIB Citation Workflow                                   ║${RESET}"
echo "${BOLD}╚════════════════════════════════════════════════════════════════╝${RESET}"
log "Starting workflow"
log "Collection: $COLLECTION"
log "Log file: $LOG_FILE"

# Check collection exists
if [ ! -f "$COLLECTION" ]; then
    error "Collection file not found: $COLLECTION"
    error "Run: ./scripts/setup-dandi-bib.sh $DANDI_BIB_DIR"
    exit 1
fi

cd "$DANDI_BIB_DIR"

# Check if running in dry-run mode
DRY_RUN_FLAG=""
if [ "${DRY_RUN}" = "1" ]; then
    warn "Running in DRY RUN mode"
    DRY_RUN_FLAG="--dry-run"
fi

# Step 1: Discover citations
if [ "${SKIP_DISCOVER}" != "1" ]; then
    info "Step 1: Discovering citations..."
    if uv run citations-collector discover "$COLLECTION" >> "$LOG_FILE" 2>&1; then
        info "✓ Citation discovery complete"
    else
        error "✗ Citation discovery failed"
        exit 1
    fi
else
    warn "⊘ Skipping citation discovery (SKIP_DISCOVER=1)"
fi

# Step 2: Fetch PDFs
if [ "${SKIP_PDFS}" != "1" ]; then
    info "Step 2: Fetching PDFs..."
    if uv run citations-collector fetch-pdfs "$COLLECTION" \
        $DRY_RUN_FLAG >> "$LOG_FILE" 2>&1; then
        info "✓ PDF fetching complete"
    else
        warn "⚠ PDF fetching had some failures (check log)"
    fi
else
    warn "⊘ Skipping PDF fetching (SKIP_PDFS=1)"
fi

# Step 3: Extract contexts
if [ "${SKIP_EXTRACTION}" != "1" ]; then
    info "Step 3: Extracting contexts from PDFs..."
    if uv run citations-collector extract-contexts "$COLLECTION" \
        --git-annex $DRY_RUN_FLAG >> "$LOG_FILE" 2>&1; then
        info "✓ Context extraction complete"
    else
        warn "⚠ Context extraction had some failures (check log)"
    fi
else
    warn "⊘ Skipping context extraction (SKIP_EXTRACTION=1)"
fi

# Step 4: Classify citations
if [ "${SKIP_CLASSIFICATION}" != "1" ]; then
    info "Step 4: Classifying citations with LLM..."

    # Check if Ollama is reachable
    if ! curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
        error "✗ Ollama not reachable at localhost:11434"
        error "Start SSH tunnel: ssh -L 0.0.0.0:11434:localhost:11434 typhon -N"
        exit 1
    fi

    if uv run citations-collector classify "$COLLECTION" \
        --backend ollama \
        --model qwen2:7b \
        --confidence-threshold 0.7 \
        $DRY_RUN_FLAG >> "$LOG_FILE" 2>&1; then
        info "✓ Classification complete"
    else
        error "✗ Classification failed"
        exit 1
    fi
else
    warn "⊘ Skipping classification (SKIP_CLASSIFICATION=1)"
fi

# Step 5: Sync to Zotero (optional)
if [ "${SYNC_ZOTERO}" = "1" ]; then
    info "Step 5: Syncing to Zotero..."
    if [ -z "$ZOTERO_API_KEY" ]; then
        warn "⊘ ZOTERO_API_KEY not set, skipping Zotero sync"
    else
        if uv run citations-collector sync-zotero "$COLLECTION" \
            $DRY_RUN_FLAG >> "$LOG_FILE" 2>&1; then
            info "✓ Zotero sync complete"
        else
            warn "⚠ Zotero sync had issues (check log)"
        fi
    fi
else
    warn "⊘ Skipping Zotero sync (SYNC_ZOTERO not set)"
fi

# Summary
echo ""
echo "${BOLD}╔════════════════════════════════════════════════════════════════╗${RESET}"
echo "${BOLD}║  Workflow Complete                                             ║${RESET}"
echo "${BOLD}╚════════════════════════════════════════════════════════════════╝${RESET}"
log "Workflow completed successfully"

# Show stats
info "Citation statistics:"
make stats 2>/dev/null || true

echo ""
info "Full log: $LOG_FILE"
