# Makefile for DANDI Citations Collection and Classification
#
# This Makefile provides targets for:
# - Setting up the environment
# - Discovering citations
# - Fetching PDFs
# - Extracting contexts from PDFs
# - Classifying citations with LLM
# - Syncing to Zotero

.PHONY: help setup discover fetch-pdfs extract-contexts classify sync-zotero clean test

# Configuration
COLLECTION ?= collection.yaml
OUTPUT_TSV ?= citations.tsv
PDFS_DIR ?= pdfs
LLM_BACKEND ?= ollama
LLM_MODEL ?= qwen2:7b

# Colors for output
BOLD := $(shell tput bold)
RESET := $(shell tput sgr0)
GREEN := $(shell tput setaf 2)
YELLOW := $(shell tput setaf 3)
RED := $(shell tput setaf 1)

help: ## Show this help message
	@echo "$(BOLD)DANDI Citations Collection Workflow$(RESET)"
	@echo ""
	@echo "$(BOLD)Usage:$(RESET)"
	@echo "  make [target] [COLLECTION=path/to/collection.yaml]"
	@echo ""
	@echo "$(BOLD)Main Workflow:$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BOLD)Environment Variables:$(RESET)"
	@echo "  COLLECTION   Collection YAML file (default: collection.yaml)"
	@echo "  OUTPUT_TSV   Output TSV file (default: citations.tsv)"
	@echo "  PDFS_DIR     PDF directory (default: pdfs)"
	@echo "  LLM_BACKEND  LLM backend: ollama|dartmouth|openrouter (default: ollama)"
	@echo "  LLM_MODEL    Model name (default: qwen2:7b)"
	@echo ""
	@echo "$(BOLD)Example:$(RESET)"
	@echo "  make all COLLECTION=dandi-collection.yaml"

all: discover fetch-pdfs extract-contexts classify ## Run full workflow (discover → fetch → extract → classify)
	@echo "$(GREEN)✓ Full workflow complete!$(RESET)"

setup: ## Install dependencies and check environment
	@echo "$(BOLD)Setting up environment...$(RESET)"
	uv pip install -e ".[devel,llm,extraction]"
	@echo "$(GREEN)✓ Dependencies installed$(RESET)"
	@echo ""
	@echo "$(BOLD)Checking LLM backend connection...$(RESET)"
	@if [ "$(LLM_BACKEND)" = "ollama" ]; then \
		uv run scripts/test_ollama_connection.py || { \
			echo "$(RED)✗ Ollama not reachable$(RESET)"; \
			echo "$(YELLOW)Start SSH tunnel: ssh -L 0.0.0.0:11434:localhost:11434 typhon -N$(RESET)"; \
			exit 1; \
		}; \
	fi
	@echo "$(GREEN)✓ Setup complete$(RESET)"

check-collection: ## Validate collection YAML exists
	@if [ ! -f "$(COLLECTION)" ]; then \
		echo "$(RED)✗ Collection file not found: $(COLLECTION)$(RESET)"; \
		echo "$(YELLOW)Create it or set COLLECTION=path/to/file.yaml$(RESET)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✓ Collection file: $(COLLECTION)$(RESET)"

discover: check-collection ## Discover citations for items in collection
	@echo "$(BOLD)Discovering citations...$(RESET)"
	uv run citations-collector discover $(COLLECTION)
	@echo "$(GREEN)✓ Citations discovered and saved to $(OUTPUT_TSV)$(RESET)"

fetch-pdfs: check-collection ## Fetch PDFs for citations
	@echo "$(BOLD)Fetching PDFs...$(RESET)"
	uv run citations-collector fetch-pdfs $(COLLECTION) \
		--output-dir $(PDFS_DIR)
	@echo "$(GREEN)✓ PDFs fetched to $(PDFS_DIR)$(RESET)"

extract-contexts: check-collection ## Extract citation contexts from PDFs/HTMLs
	@echo "$(BOLD)Extracting contexts from PDFs/HTMLs...$(RESET)"
	uv run citations-collector extract-contexts $(COLLECTION) \
		--output-dir $(PDFS_DIR) \
		--git-annex
	@echo "$(GREEN)✓ Contexts extracted (saved as extracted_citations.json per paper)$(RESET)"

extract-contexts-dry-run: check-collection ## Preview context extraction without creating files
	@echo "$(BOLD)[DRY RUN] Extracting contexts...$(RESET)"
	uv run citations-collector extract-contexts $(COLLECTION) \
		--output-dir $(PDFS_DIR) \
		--dry-run

classify: check-collection ## Classify citations using LLM
	@echo "$(BOLD)Classifying citations with $(LLM_BACKEND)/$(LLM_MODEL)...$(RESET)"
	uv run citations-collector classify $(COLLECTION) \
		--backend $(LLM_BACKEND) \
		--model $(LLM_MODEL) \
		--confidence-threshold 0.7
	@echo "$(GREEN)✓ Citations classified and saved to $(OUTPUT_TSV)$(RESET)"

classify-review: check-collection ## Classify with interactive review of low-confidence
	@echo "$(BOLD)Classifying with review mode...$(RESET)"
	uv run citations-collector classify $(COLLECTION) \
		--backend $(LLM_BACKEND) \
		--model $(LLM_MODEL) \
		--review

sync-zotero: check-collection ## Sync citations to Zotero
	@echo "$(BOLD)Syncing to Zotero...$(RESET)"
	uv run citations-collector sync-zotero $(COLLECTION) --dry-run
	@read -p "Proceed with sync? (y/N): " confirm && \
	if [ "$$confirm" = "y" ]; then \
		uv run citations-collector sync-zotero $(COLLECTION); \
		echo "$(GREEN)✓ Synced to Zotero$(RESET)"; \
	else \
		echo "$(YELLOW)⊘ Sync cancelled$(RESET)"; \
	fi

test: ## Run test suite
	@echo "$(BOLD)Running tests...$(RESET)"
	tox -e py3

test-llm: ## Test LLM backend connections
	@echo "$(BOLD)Testing LLM backends...$(RESET)"
	uv run scripts/test_ollama_connection.py
	@echo ""
	uv run scripts/test_llm_backends.py

test-extraction: ## Test context extraction
	@echo "$(BOLD)Testing context extraction...$(RESET)"
	uv run scripts/test_context_extraction.py

stats: ## Show statistics about citations
	@echo "$(BOLD)Citation Statistics$(RESET)"
	@if [ -f "$(OUTPUT_TSV)" ]; then \
		echo ""; \
		echo "Total citations: $$(tail -n +2 $(OUTPUT_TSV) | wc -l)"; \
		echo "Unique papers: $$(tail -n +2 $(OUTPUT_TSV) | cut -f3 | sort -u | wc -l)"; \
		echo "Unique datasets: $$(tail -n +2 $(OUTPUT_TSV) | cut -f1 | sort -u | wc -l)"; \
		echo ""; \
		echo "Relationship types:"; \
		tail -n +2 $(OUTPUT_TSV) | cut -f7 | sort | uniq -c | sort -rn; \
		echo ""; \
		echo "Citation sources:"; \
		tail -n +2 $(OUTPUT_TSV) | cut -f8 | sort | uniq -c | sort -rn; \
		echo ""; \
		echo "OA status:"; \
		tail -n +2 $(OUTPUT_TSV) | cut -f9 | sort | uniq -c | sort -rn; \
	else \
		echo "$(RED)✗ TSV file not found: $(OUTPUT_TSV)$(RESET)"; \
	fi

clean: ## Remove generated files (preserves PDFs)
	@echo "$(BOLD)Cleaning generated files...$(RESET)"
	rm -f $(OUTPUT_TSV)
	find $(PDFS_DIR) -name "extracted_citations.json" -delete
	@echo "$(YELLOW)⚠ Preserved PDFs in $(PDFS_DIR)$(RESET)"
	@echo "$(GREEN)✓ Cleaned$(RESET)"

clean-all: ## Remove all generated files INCLUDING PDFs
	@echo "$(RED)$(BOLD)WARNING: This will delete all PDFs!$(RESET)"
	@read -p "Are you sure? (y/N): " confirm && \
	if [ "$$confirm" = "y" ]; then \
		rm -rf $(PDFS_DIR) $(OUTPUT_TSV); \
		echo "$(GREEN)✓ All files removed$(RESET)"; \
	else \
		echo "$(YELLOW)⊘ Cancelled$(RESET)"; \
	fi

.DEFAULT_GOAL := help
