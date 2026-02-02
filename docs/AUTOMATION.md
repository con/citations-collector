# Automation Guide for DANDI-BIB

This guide shows how to automate the citation collection workflow for continuous updates.

## Quick Setup

### 1. Create dandi-bib Project

```bash
cd /home/yoh/proj/dandi/citations-collector-enh-zotero
./scripts/setup-dandi-bib.sh /home/yoh/proj/dandi/dandi-bib
```

This creates:
```
/home/yoh/proj/dandi/dandi-bib/
├── collection.yaml          # Configuration
├── Makefile                 # Workflow automation
├── README.md               # Usage guide
├── citations/
│   ├── data/               # TSV output
│   └── pdfs/               # Downloaded PDFs
```

### 2. Run Initial Collection

```bash
cd /home/yoh/proj/dandi/dandi-bib

# Start Ollama tunnel (separate terminal)
ssh -L 0.0.0.0:11434:localhost:11434 typhon -N

# Run full workflow
make all
```

### 3. Set Up Automation (Optional)

See sections below for cron or systemd timer setup.

---

## Manual Workflow

### Full Workflow

```bash
make all
```

Runs:
1. `discover` - Find citations via CrossRef/OpenCitations/DataCite
2. `fetch-pdfs` - Download PDFs via Unpaywall
3. `extract-contexts` - Extract dataset mentions from PDFs
4. `classify` - Classify relationship types with LLM

### Individual Steps

```bash
# Discover new citations
make discover

# Fetch PDFs for citations without PDFs
make fetch-pdfs

# Extract contexts from PDFs
make extract-contexts

# Classify citations with LLM
make classify

# Review low-confidence classifications interactively
make classify-review

# Sync to Zotero
make sync-zotero
```

### View Statistics

```bash
make stats
```

Output:
```
Total citations: 1523
Unique papers: 487
Unique datasets: 156

Relationship types:
    456 Uses
    189 IsDocumentedBy
    123 CitesAsEvidence
    89 Cites
    ...

OA status:
    678 gold
    234 green
    156 hybrid
    455 closed
```

---

## Automated Workflow

### Option 1: Cron Job (Simple)

Add to your crontab (`crontab -e`):

```bash
# Run citation workflow weekly on Sunday at 2 AM
0 2 * * 0 /home/yoh/proj/dandi/citations-collector-enh-zotero/scripts/run-dandi-bib-workflow.sh /home/yoh/proj/dandi/dandi-bib >> /home/yoh/proj/dandi/dandi-bib/logs/cron.log 2>&1
```

**Environment setup for cron**:

Create `/home/yoh/proj/dandi/dandi-bib/.env`:
```bash
export PATH=/usr/local/bin:/usr/bin:/bin
export ZOTERO_API_KEY=your-api-key
export OPENAI_API_KEY=your-dartmouth-token
```

Then update crontab:
```bash
# Run weekly with environment
0 2 * * 0 source /home/yoh/proj/dandi/dandi-bib/.env && /home/yoh/proj/dandi/citations-collector-enh-zotero/scripts/run-dandi-bib-workflow.sh /home/yoh/proj/dandi/dandi-bib
```

### Option 2: Systemd Timer (Advanced)

Create systemd service and timer files:

**Service**: `/etc/systemd/system/dandi-bib-workflow.service`
```ini
[Unit]
Description=DANDI-BIB Citation Workflow
After=network.target

[Service]
Type=oneshot
User=yoh
WorkingDirectory=/home/yoh/proj/dandi/dandi-bib
EnvironmentFile=/home/yoh/proj/dandi/dandi-bib/.env
ExecStart=/home/yoh/proj/dandi/citations-collector-enh-zotero/scripts/run-dandi-bib-workflow.sh /home/yoh/proj/dandi/dandi-bib
StandardOutput=append:/home/yoh/proj/dandi/dandi-bib/logs/systemd.log
StandardError=append:/home/yoh/proj/dandi/dandi-bib/logs/systemd-error.log
```

**Timer**: `/etc/systemd/system/dandi-bib-workflow.timer`
```ini
[Unit]
Description=Run DANDI-BIB workflow weekly

[Timer]
OnCalendar=Sun 02:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable dandi-bib-workflow.timer
sudo systemctl start dandi-bib-workflow.timer

# Check status
systemctl status dandi-bib-workflow.timer

# View logs
journalctl -u dandi-bib-workflow.service
```

### Option 3: Custom Script with Locking

For more control, create a wrapper script:

`/home/yoh/proj/dandi/dandi-bib/run-workflow.sh`:
```bash
#!/bin/bash
set -e

LOCKFILE="/tmp/dandi-bib-workflow.lock"
LOGDIR="/home/yoh/proj/dandi/dandi-bib/logs"

# Ensure only one instance runs
if [ -f "$LOCKFILE" ]; then
    echo "Workflow already running (lockfile exists)"
    exit 1
fi

trap "rm -f $LOCKFILE" EXIT
touch "$LOCKFILE"

# Source environment
source /home/yoh/proj/dandi/dandi-bib/.env

# Check if Ollama tunnel is running
if ! curl -s http://localhost:11434/api/version > /dev/null; then
    echo "ERROR: Ollama not reachable. Start SSH tunnel:"
    echo "  ssh -L 0.0.0.0:11434:localhost:11434 typhon -N"
    exit 1
fi

# Run workflow with email notification on failure
if ! /home/yoh/proj/dandi/citations-collector-enh-zotero/scripts/run-dandi-bib-workflow.sh; then
    # Send failure notification
    echo "DANDI-BIB workflow failed. Check logs at $LOGDIR" | \
        mail -s "DANDI-BIB Workflow Failed" admin@example.com
    exit 1
fi

# Success notification
echo "DANDI-BIB workflow completed successfully" | \
    mail -s "DANDI-BIB Workflow Complete" admin@example.com
```

---

## Workflow Customization

### Skip Steps

Set environment variables to skip steps:

```bash
# Skip citation discovery (use existing citations)
SKIP_DISCOVER=1 ./scripts/run-dandi-bib-workflow.sh

# Skip PDF fetching (already have PDFs)
SKIP_PDFS=1 ./scripts/run-dandi-bib-workflow.sh

# Only run classification on existing data
SKIP_DISCOVER=1 SKIP_PDFS=1 SKIP_EXTRACTION=1 \
    ./scripts/run-dandi-bib-workflow.sh

# Enable Zotero sync
SYNC_ZOTERO=1 ./scripts/run-dandi-bib-workflow.sh
```

### Dry Run Mode

Test without making changes:

```bash
DRY_RUN=1 ./scripts/run-dandi-bib-workflow.sh
```

### Different LLM Backend

Edit `collection.yaml`:

```yaml
llm:
  backend: dartmouth  # Use Dartmouth instead of Ollama
  model: anthropic.claude-sonnet-4-5-20250929
```

Or override via Makefile:

```bash
make classify LLM_BACKEND=dartmouth LLM_MODEL=anthropic.claude-sonnet-4-5-20250929
```

---

## Monitoring

### Check Logs

```bash
# View latest workflow log
tail -f /home/yoh/proj/dandi/dandi-bib/logs/workflow-*.log

# View all logs
ls -lht /home/yoh/proj/dandi/dandi-bib/logs/

# Search for errors
grep ERROR /home/yoh/proj/dandi/dandi-bib/logs/workflow-*.log
```

### Monitor Cron Jobs

```bash
# List cron jobs
crontab -l

# View cron log
tail -f /home/yoh/proj/dandi/dandi-bib/logs/cron.log
```

### Monitor Systemd Timers

```bash
# List all timers
systemctl list-timers

# Check specific timer
systemctl status dandi-bib-workflow.timer

# View service logs
journalctl -u dandi-bib-workflow.service -f
```

---

## Troubleshooting

### Ollama Not Reachable

**Problem**: Classification fails with "Connection refused"

**Solution**: Ensure SSH tunnel is running:
```bash
# Check if tunnel is active
curl http://localhost:11434/api/version

# If not, start tunnel:
ssh -L 0.0.0.0:11434:localhost:11434 typhon -N
```

**For automated workflows**: Set up autossh for persistent tunnel:
```bash
# Install autossh
apt-get install autossh  # Debian/Ubuntu

# Run with autossh (auto-reconnects)
autossh -M 0 -o "ServerAliveInterval 30" -o "ServerAliveCountMax 3" \
    -L 0.0.0.0:11434:localhost:11434 typhon -N
```

### PDFs Not Downloading

**Problem**: Many "no PDF found" errors

**Possible causes**:
1. Papers are closed access (expected)
2. Unpaywall API rate limiting
3. Network issues

**Solutions**:
```bash
# Check Unpaywall quota (100k requests/day)
# Add delays between requests in config

# Use alternative sources
# Edit collection.yaml:
pdfs:
  fallback_sources: [arxiv, biorxiv, pubmed]
```

### Git-Annex Errors

**Problem**: "git-annex not initialized"

**Solution**:
```bash
cd /home/yoh/proj/dandi/dandi-bib
git init
git annex init "dandi-bib-$(hostname)"
```

### Low Classification Confidence

**Problem**: Many citations have confidence < 0.7

**Solutions**:

1. **Use better model**:
   ```yaml
   llm:
     backend: dartmouth
     model: anthropic.claude-opus-4-5-20251101  # More powerful
   ```

2. **Review interactively**:
   ```bash
   make classify-review
   ```

3. **Adjust threshold**:
   ```yaml
   classify:
     confidence_threshold: 0.6  # Lower threshold
   ```

---

## Performance Optimization

### Parallel Processing

For large collections (>1000 citations), process in batches:

```bash
# Split citations by dataset
awk -F'\t' 'NR==1 || /dandi:00000[0-2]/' citations.tsv > batch1.tsv
awk -F'\t' 'NR==1 || /dandi:00000[3-5]/' citations.tsv > batch2.tsv

# Process in parallel
make classify COLLECTION=batch1-collection.yaml &
make classify COLLECTION=batch2-collection.yaml &
wait
```

### Cache LLM Results

Classification results are saved to TSV, so re-running classification only processes new/changed citations.

### Incremental Updates

Use incremental mode to only discover new citations:

```bash
# First run: full discovery
make discover

# Subsequent runs: only new citations since last run
make discover  # Automatically uses incremental mode
```

---

## Backup & Recovery

### Backup Strategy

```bash
# Backup TSV data (small)
rsync -av /home/yoh/proj/dandi/dandi-bib/citations/data/ \
    backup-server:/backups/dandi-bib/data/

# Backup git-annex metadata (not PDFs)
cd /home/yoh/proj/dandi/dandi-bib
git annex sync
git push origin git-annex

# Optional: Backup PDFs (large)
rsync -av /home/yoh/proj/dandi/dandi-bib/citations/pdfs/ \
    backup-server:/backups/dandi-bib/pdfs/
```

### Restore from Backup

```bash
# Restore data
rsync -av backup-server:/backups/dandi-bib/data/ \
    /home/yoh/proj/dandi/dandi-bib/citations/data/

# Restore git-annex
git annex get .  # Re-download PDFs from remotes
```

---

## Integration with Other Tools

### Export to NeuroD3

```bash
# Generate NeuroD3-compatible JSON
citations-collector export-neurod3 collection.yaml \
    --output neurod3-export.json
```

### Export to find_reuse

```bash
# Cross-validate with find_reuse
citations-collector validate-with-find-reuse collection.yaml
```

### Custom Exports

```python
import pandas as pd

# Load TSV
df = pd.read_csv('citations/data/dandi-citations.tsv', sep='\t')

# Export to JSON
df.to_json('citations.json', orient='records', indent=2)

# Export to CSV
df.to_csv('citations.csv', index=False)

# Export to Parquet (efficient for large datasets)
df.to_parquet('citations.parquet')
```

---

## See Also

- [Makefile](../Makefile) - Workflow automation targets
- [SETUP-LLM.md](SETUP-LLM.md) - LLM backend setup
- [CONTEXT-EXTRACTION.md](CONTEXT-EXTRACTION.md) - Context extraction guide
- [scripts/run-dandi-bib-workflow.sh](../scripts/run-dandi-bib-workflow.sh) - Workflow script
