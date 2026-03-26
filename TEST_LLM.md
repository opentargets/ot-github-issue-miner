# Testing LLM Extraction Locally

This guide explains how to test the LLM-powered scenario mining locally before running it in production.

## Quick Start

1. **Set up your environment:**
   ```bash
   export ANTHROPIC_API_KEY='your-anthropic-api-key'
   export GITHUB_TOKEN='your-github-pat'  # Optional but recommended
   ```

2. **Run the test script:**
   ```bash
   # Mine issues from last 7 days with LLM
   python test_llm_local.py

   # Mine issues from last 30 days
   python test_llm_local.py --days 30

   # Save to custom directory with verbose output
   python test_llm_local.py --days 14 --output-dir my-test --verbose
   ```

3. **Check results:**
   Results are saved to `test-results/` (or your custom output directory):
   - `mined-scenarios.csv` - CSV format
   - `mined-scenarios.json` - JSON format

## What's Different from Production?

### Production (GitHub Action - Regex Only)
```bash
.venv/bin/python -m ot_miner.cli --output-dir ./results --no-llm --verbose
```
- Uses **regex only** (fast, free, no API calls)
- Runs weekly on all issues from last 3 months
- Good for basic ID extraction (explicit CHEMBL, ENSG, EFO IDs)

### Local Testing (LLM Enabled)
```bash
python test_llm_local.py --days 7
```
- Uses **regex + LLM** (slower, costs API credits, smarter)
- Reads issue body AND comments for better context
- Infers IDs from gene/disease/drug names
- Can use OpenTargets MCP tools for lookups (when configured)

## What the LLM Sees

The LLM now receives:
1. **Issue title**
2. **Issue body** (first 3000 chars)
3. **Comments** (first 10 comments, 300 chars each)
4. **OpenTargets GraphQL API access** (can query in real-time)

This allows it to:
- Find mentions in comments that regex missed
- **Query the OpenTargets API** to verify gene/disease/drug IDs
- Look up entities by name (e.g., "BRAF" → API query → ENSG00000157764)
- Verify IDs are valid before returning them
- Get accurate mappings instead of guessing

## OpenTargets API Integration

The LLM can make GraphQL queries like:
```graphql
query { 
  search(queryString:"BRAF", entityNames:["target"]) { 
    hits { id name } 
  } 
}
```

This ensures all returned IDs are:
- **Verified** - Checked against the live OpenTargets database
- **Accurate** - No guessing or incorrect mappings
- **Current** - Uses latest data from OpenTargets platform

## Cost Estimation

Approximate API costs (Claude 3.5 Sonnet):
- **Per issue:** ~$0.001-0.003 (depends on body + comment length)
- **7 days of issues:** ~$0.10-0.50
- **30 days of issues:** ~$0.50-2.00

The test script helps you validate on a small subset before running on the full dataset.

## Example Output

```
🚀 Running scenario miner with LLM
📅 Mining issues since: 2026-03-18 (7 days ago)
📂 Output directory: ./test-results
🤖 LLM model: claude-3-5-sonnet-20241022

⬇  Fetching GitHub issues (open + closed)…
   142 issues fetched…
✅ 142 issues fetched

🔍 Regex extraction (Pass 1)…
✅ 127 scenarios extracted

🤖 LLM enrichment pass on 127 issues in batches of 5…
   127/127 enriched…
✅ LLM enrichment complete

📝 Writing results…
✅ Results written to test-results/
```

## Troubleshooting

**"ANTHROPIC_API_KEY not set"**
- Get an API key from https://console.anthropic.com/
- Export it: `export ANTHROPIC_API_KEY='sk-ant-...'`

**"Could not find .venv/bin/python"**
- Install dependencies first: `uv sync`

**"Failed to fetch comments for issue #XXXX"**
- Non-critical warning, mining continues
- May indicate rate limiting or network issues
- Use GITHUB_TOKEN for higher rate limits

## Next Steps

Once testing looks good:
1. Push changes to GitHub
2. Enable LLM in workflow by removing `--no-llm` flag
3. Add `ANTHROPIC_API_KEY` to GitHub Secrets
4. Workflow will run weekly with LLM enabled
