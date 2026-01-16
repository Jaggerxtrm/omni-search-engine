# Obsidian Semantic Search - Usage Guide

Complete guide for deploying and using the Obsidian Semantic Search MCP server.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Configuration](#configuration)
3. [Initial Setup](#initial-setup)
4. [MCP Server Integration](#mcp-server-integration)
5. [Using the Tools](#using-the-tools)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

- Podman or Docker installed
- OpenAI API key
- Obsidian vault with markdown files

### 5-Minute Setup

```bash
# 1. Navigate to project directory
cd /home/dawid/second-mind/tools/obsidian-semantic-search

# 2. Configure Environment
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY and VAULT_PATH

# 3. Build and Run (using Docker Compose)
# This handles build, config, and volume persistence automatically
docker-compose up -d

# 4. Verify
docker-compose logs -f
```

---

## Configuration

### Environment Variables (.env)

The system is now configured entirely via environment variables.
See `.env.example` for reference:

```bash
OPENAI_API_KEY=sk-...        # Required: OpenAI API Key
VAULT_PATH=/path/to/your/obsidian/vault    # Required: Absolute path to your Obsidian vault
WATCH_MODE=true  # Enable auto-indexing (optional)
```

### Advanced Config
The `config.yaml` is now baked into the image. To override it, you can still mount a custom config file or use `CONFIG_PATH` variable, but the default should work for most users.

---

## MCP Server Integration

### Claude Code Configuration

Edit `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "obsidian-search": {
      "command": "podman",
      "args": [
        "run", "--rm", "-i",
        
        // 1. Vault Access (Read-only bind mount)
        "-v", "/home/dawid/second-mind:/vault:ro",
        
        // 2. Data Persistence (Docker Named Volume)
        "-v", "obsidian_search_data:/data",
        
        // 3. Configuration via Env
        "-e", "OPENAI_API_KEY",
        
        "obsidian-search:latest"
      ],
      "env": {
        "OPENAI_API_KEY": "sk-..." 
      }
    }
  }
}
```

**Volume Mounts:**
- `/home/dawid/second-mind:/vault:ro` - Your vault (read-only)
- `/home/dawid/.config/obsidian-semantic-search:/data:rw` - ChromaDB storage (read-write)

**Important:**
- Replace `/home/dawid/second-mind` with your actual vault path
- Replace the API key with your actual key
- Ensure paths use absolute paths, not `~`

### Restart Claude Code

After updating config:
1. Restart Claude Code completely
2. Verify MCP server is loaded (check logs if available)

---

## Using the Tools

### Tool 1: `semantic_search`

Search your vault semantically for relevant content.

**Parameters:**
- `query` (string, required): Natural language search query
- `n_results` (int, optional): Number of results to return (default: 5)
- `folder` (string, optional): Filter by folder (e.g., "1-projects/trading")
- `tags` (string, optional): Filter by comma-separated tags

**Example prompts:**
```
"Search my vault for information about gold markets"
"Find notes related to treasury basis trades"
"What do my notes say about real interest rates?"
"Search for trading strategies in the 1-projects folder"
```

**Returns:**
```json
[
  {
    "id": "gold-markets.md::0",
    "content": "Gold is a precious metal...",
    "similarity": 0.637,
    "file_path": "gold-markets.md",
    "note_title": "gold-markets",
    "header_context": "# Gold Market Analysis",
    "folder": "",
    "tags": ["trading", "gold", "commodities"],
    "chunk_index": 0,
    "token_count": 150
  }
]
```

### Suggest Links

Find related notes to link to a specific file.

```python
# Basic suggestion
result = await session.call_tool("suggest_links", {
    "note_path": "1-projects/my-note.md"
})

# Filter by folder (e.g., look for links only in "2-areas")
result = await session.call_tool("suggest_links", {
    "note_path": "1-projects/my-note.md",
    "folder": "2-areas"
})

# Filter by tags
result = await session.call_tool("suggest_links", {
    "note_path": "1-projects/my-note.md",
    "tags": "development"
})
```

### Tool 2: `reindex_vault`

Rebuild or update the vault index.

**Parameters:**
- `force` (boolean, optional): Force reindex all files (default: false)

**Example prompts:**
```bash
"Reindex my Obsidian vault"                    # Incremental
"Index all notes (force rebuild)"              # Force full reindex
"Update the index with recent changes"         # Incremental
```


### Tool 3: `index_note`

Index a specific note immediately.

```python
# Index a single file
result = await session.call_tool("index_note", {
    "note_path": "1-projects/new-meeting-notes.md"
})
```

### Tool 4: `get_index_stats`
"Reindex my Obsidian vault"                    # Incremental
"Index all notes (force rebuild)"              # Force full reindex
"Update the index with recent changes"         # Incremental
```

**Incremental vs Force:**
- **Incremental** (force=false): Only indexes new/modified files based on content hash
- **Force** (force=true): Reindexes all files regardless of changes

**Returns:**
```json
{
  "success": true,
  "notes_processed": 3,
  "notes_skipped": 217,
  "chunks_created": 15,
  "duration_seconds": 12.5,
  "errors": []
}
```

**Cost Savings:**
Incremental indexing saves API costs by skipping unchanged files. For a typical vault:
- Initial index: ~$0.007 (220 files)
- Daily incremental: ~$0.00015 (5 modified files)
- Monthly: ~$0.005

### Tool 3: `get_index_stats`

Get statistics about the current index.

**Example prompts:**
```
"How many notes are indexed?"
"Show me index statistics"
"What's the current state of my vault index?"
```

**Returns:**
```json
{
  "total_chunks": 660,
  "total_files": 220,
  "vault_path": "/home/dawid/second-mind",
  "chromadb_path": "/home/dawid/.config/obsidian-semantic-search/chromadb",
  "embedding_model": "text-embedding-3-small",
  "collection_name": "obsidian_notes"
}
```

---

## Troubleshooting

### Container Issues

**Problem:** Container fails to build
```
Error: ... onnxruntime ... Python 3.14
```
**Solution:** Container uses Python 3.13 base image. If this error occurs, verify Dockerfile:
```dockerfile
FROM python:3.13-slim
```

**Problem:** Container runs but crashes immediately
**Solution:** Check logs:
```bash
podman logs <container-id>
```

### Permission Issues

**Problem:** Permission denied accessing vault
```
PermissionError: [Errno 13] Permission denied: '/vault/...'
```
**Solution:**
1. Verify vault is mounted with `:ro` flag
2. Check SELinux labels (Fedora/RHEL):
```bash
ls -Z /home/dawid/second-mind
```
If needed, relabel:
```bash
chcon -Rt svirt_sandbox_file_t /home/dawid/second-mind
```

**Problem:** Cannot write to ChromaDB directory
**Solution:** Ensure data directory is mounted with `:rw` and exists:
```bash
mkdir -p ~/.config/obsidian-semantic-search/chromadb
```

### API Issues

**Problem:** OpenAI API key not found
```
Error: OPENAI_API_KEY not set
```
**Solution:** Set environment variable:
```bash
export OPENAI_API_KEY="sk-..."
# Or add to ~/.bashrc for persistence
```

**Problem:** Rate limit errors
```
RateLimitError: Rate limit exceeded
```
**Solution:**
- Built-in retry logic (3 attempts with exponential backoff)
- If persistent, wait a few minutes
- Check API usage at platform.openai.com

**Problem:** Invalid API key
```
AuthenticationError: Incorrect API key
```
**Solution:** Verify key is correct and active:
1. Check at platform.openai.com/api-keys
2. Regenerate if necessary
3. Update config and environment variable

### Search Quality Issues

**Problem:** Search returns irrelevant results
**Possible causes:**
1. Not enough content in vault
2. Query too vague
3. Need to rebuild index

**Solutions:**
- Be more specific in queries
- Force reindex: `reindex_vault(force=true)`
- Check similarity scores (< 0.3 = weak match)

**Problem:** Expected note not in results
**Solutions:**
1. Verify note is indexed: `get_index_stats()`
2. Check note content exists
3. Try broader query
4. Reindex: `reindex_vault(force=true)`

### Performance Issues

**Problem:** Indexing takes too long
**Expected times:**
- 220 files: ~30-60 seconds initial index
- 5 files incremental: ~5-10 seconds

**Solutions:**
1. Check API latency (network issues)
2. Reduce batch_size in config (default: 100)
3. Use incremental indexing (force=false)

**Problem:** Search is slow (> 1 second)
**Solutions:**
1. Reduce n_results parameter
2. Check ChromaDB storage size
3. Restart MCP server

### Data Issues

**Problem:** Stale index (recent changes not reflected)
**Solution:** Run incremental reindex:
```
"Update the index with recent changes"
```

**Problem:** Corrupted ChromaDB
**Solution:** Delete and rebuild:
```bash
rm -rf ~/.config/obsidian-semantic-search/chromadb
# Then reindex via Claude Code
```

---

## Advanced Usage

### Custom Configuration

For multiple vaults or special setups, create custom configs:

```bash
# Vault 1 config
mkdir -p ~/.config/obsidian-semantic-search/vault1
cp config.yaml ~/.config/obsidian-semantic-search/vault1/

# Vault 2 config
mkdir -p ~/.config/obsidian-semantic-search/vault2
cp config.yaml ~/.config/obsidian-semantic-search/vault2/
```

Then use different MCP server entries:
```json
{
  "mcpServers": {
    "obsidian-vault1": { "env": { "CONFIG_PATH": "~/.config/.../vault1/config.yaml" } },
    "obsidian-vault2": { "env": { "CONFIG_PATH": "~/.config/.../vault2/config.yaml" } }
  }
}
```

### Monitoring

Check ChromaDB size:
```bash
du -sh ~/.config/obsidian-semantic-search/chromadb
# Expected: ~2-5 MB per 100 notes
```

Check index freshness:
```bash
ls -lt ~/.config/obsidian-semantic-search/chromadb/chroma.sqlite3
```

---

## Cost Estimation

### OpenAI API Costs

**Model:** text-embedding-3-small ($0.02 / 1M tokens)

**Your vault** (452 MB, ~220 files):
- Initial index: 330,000 tokens = **$0.0066** (~0.7 cents)
- Daily updates (5 files): 7,500 tokens = **$0.00015**
- Monthly: **$0.005** (~0.5 cents)

**First month total:** ~$0.01 (1 penny)

### Storage

ChromaDB local storage:
- 220 files → ~660 chunks → ~5 MB disk space
- No ongoing storage costs

---

## Support

For issues or questions:
1. Check this guide
2. Review logs: `podman logs <container-id>`
3. Run integration test to verify setup
4. Check GitHub issues (if applicable)

---

## Maintenance

### Regular Tasks

**Weekly:**
- Run incremental reindex to pick up changes

**Monthly:**
- Check ChromaDB size
- Review API usage costs
- Update container if needed: `podman build -t obsidian-search:latest .`

**As Needed:**
- Force reindex after major vault reorganization
- Clear ChromaDB if experiencing issues
- Update API key if rotated
