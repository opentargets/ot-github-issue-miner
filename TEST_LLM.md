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
   # Mine issues from last 7 days with LLM (default)
   python test_llm_local.py

   # Mine issues from last 30 days
   python test_llm_local.py --days 30

   # Mine issues from last 90 days (as used in testing)
   python test_llm_local.py --days 90

   # Save to custom directory with verbose output
   python test_llm_local.py --days 14 --output-dir my-test --verbose
   ```

3. **Check results:**
   Results are saved to `test-results/` (or your custom output directory):
   - `mined-scenarios.csv` - CSV format
   - `mined-scenarios.json` - JSON format



### Local Testing 
```bash
python test_llm_local.py --days 7
```
- Uses **regex + LLM** (slower, costs API credits, smarter)
- Reads issue body AND comments for better context
- Infers IDs from gene/disease/drug names
- Has OpenTargets GraphQL API access for real-time entity verification

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
📅 Mining issues since: 2025-12-26 (90 days ago)
📂 Output directory: ./test-results
🤖 LLM model: claude-3-5-sonnet-20241022

💻 Running: .venv/bin/python -m ot_miner.cli --output-dir ./test-results --since-date 2025-12-26

🚀 Open Targets scenario miner  [mode: regex + LLM]

⬇  Fetching GitHub issues (open + closed)…
   Filtering issues since: 2025-12-26T00:00:00
   142 issues fetched…
✅ 142 issues fetched

🔎 Pass 1: regex extraction…
   35 relevant issues out of 142 total

🤖 LLM enrichment pass on 35 issues in batches of 5…
   Batch 1/7: Processing 5 issues…
   Batch 2/7: Processing 5 issues…
   ...
   Batch 7/7: Processing 5 issues…
✅ LLM enrichment complete

📝 Writing outputs…
   Writing results/mined-scenarios.csv…
   Writing results/mined-scenarios.json…
✅ Results written to test-results/

📊 Summary:
   35 total scenarios
   12 with LLM enrichment

✅ Mining complete!
📁 Results saved to: ./test-results/
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

## GitHub Action Manual Trigger

The production workflow (regex-only) can be triggered manually with a custom date:

1. Go to **Actions** tab in GitHub
2. Select **"Open Targets Scenario Miner (Regex Only)"**
3. Click **"Run workflow"**
4. Enter a start date in `YYYY-MM-DD` format (e.g., `2026-02-20`)
5. Leave empty to use the default (90 days ago)

**Note:** The production workflow uses regex only (`--no-llm`) to keep costs at zero. For LLM-enriched results, use the local test script.

## Next Steps

Once local testing looks good:
1. Push changes to GitHub
2. Production workflow runs weekly (regex only, no cost)
3. For LLM-enabled production:
   - Remove `--no-llm` flag from `.github/workflows/mine-scenarios-regex.yml`
   - Add `ANTHROPIC_API_KEY` to GitHub repository secrets
   - Workflow will run weekly with LLM enrichment (~$2-5 per run)
