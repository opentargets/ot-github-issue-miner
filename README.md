# Open Targets GitHub Issue Scenario Miner

A production-grade Python package for mining GitHub issues from the [opentargets/issues](https://github.com/opentargets/issues) repository and extracting test scenarios in formats suitable for data analysis and Google Sheets import.

## Features

- **Two-Pass Extraction Pipeline**
  - **Pass 1 (Regex)**: Fast, free extraction using compiled regex patterns
  - **Pass 2 (LLM)**: Optional Claude API enrichment for context-aware mapping and gap filling

- **Extensible Architecture**
  - Pluggable extractor interface for easy addition of new extraction strategies
  - Multiple output writers (CSV, JSON, JSONL)
  - Clear separation of concerns: loaders, extractors, writers

- **Comprehensive Entity Detection**
  - Drug identifiers (CHEMBL IDs)
  - Gene identifiers (Ensembl gene IDs with inference from gene symbols)
  - Disease identifiers (EFO/MONDO ontology IDs)
  - Variants (pharmacogenomic and molecular QTL)
  - Study identifiers (GWAS, molecular QTL)
  - Credible set hashes

## Installation

### From source

```bash
git clone https://github.com/opentargets/ot-github-issue-miner.git
cd ot-github-issue-miner
pip install -e .
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Optional development dependencies

```bash
pip install -e ".[dev]"
```

## Quick Start

### Command Line Usage

#### Regex-only mode (no API cost)

```bash
python -m ot_miner.cli
```

#### With GitHub token (higher rate limit)

```bash
GITHUB_TOKEN=ghp_xxx ANTHROPIC_API_KEY=sk-ant-xxx python -m ot_miner.cli
```

### Python API

```python
from ot_miner import ScenarioMiner, Config

# Load configuration from environment
config = Config.from_env()

# Create miner and run
miner = ScenarioMiner(config)
mappings = miner.run()

# Access results
for mapping in mappings:
    print(f"Scenario: {mapping.scenario_name}")
    print(f"  Drug: {mapping.drug_id}")
    print(f"  Target: {mapping.target_id}")
```

## Configuration

Configuration is loaded from environment variables:

```bash
# GitHub settings
export GITHUB_OWNER=opentargets
export GITHUB_REPO=issues
export GITHUB_TOKEN=ghp_xxx  # Optional, increases rate limit

# LLM settings
export ANTHROPIC_API_KEY=sk-ant-xxx  # Required for LLM pass
export LLM_MODEL=claude-haiku-4-5
export LLM_BATCH_SIZE=5
export LLM_DELAY_MS=500

# Output settings
export OUTPUT_DIR=/path/to/output
export CSV_FILENAME=mined-scenarios.csv
export JSON_FILENAME=mined-scenarios.json

# Logging
export VERBOSE=true
```

Or use Python API:

```python
from ot_miner import Config
from pathlib import Path

config = Config(
    github_token="ghp_xxx",
    anthropic_api_key="sk-ant-xxx",
    output_dir=Path("/tmp/output"),
    llm_batch_size=10,
    verbose=True,
)
```

## Architecture

### Core Components

```
ot_miner/
├── models.py           # Data models (ScenarioMapping, GitHubIssue)
├── config.py           # Configuration management
├── utils.py            # Utility functions, regex patterns, knowledge bases
├── cli.py              # Command-line entry point
├── miner.py            # Main orchestration (ScenarioMiner)
├── loaders/
│   └── __init__.py     # GitHub API loader and issue filtering
├── extractors/
│   ├── base.py         # Abstract base extractor interface
│   ├── regex.py        # Regex-based extraction (Pass 1)
│   ├── llm.py          # LLM-based enrichment (Pass 2)
│   └── __init__.py     # Extractor exports
└── writers/
    └── __init__.py     # Output writers (CSV, JSON, JSONL)
```

### Extraction Pipeline

```
GitHub Issues
    ↓
[GitHubLoader] - Fetch all issues with pagination
    ↓
[RegexExtractor] - Pass 1: Fast pattern matching
    ↓
[LLMExtractor] - Pass 2: Context-aware enrichment via LangChain
    ↓
[Writers] - Output to CSV, JSON, etc.
    ↓
Test Scenarios (ready for Google Sheets import)
```

### LLM via LangChain

The LLM extraction (Pass 2) uses LangChain to efficiently interface with Claude. LangChain handles:

- Message formatting and API communication
- JSON response parsing with Pydantic validation
- Retry logic and error handling
- Token counting for cost estimation

Simply provide your Anthropic API key and LLMExtractor handles the rest:

```python
from ot_miner import ScenarioMiner, Config

config = Config.from_env()  # Requires ANTHROPIC_API_KEY
miner = ScenarioMiner(config)
mappings = miner.run()  # Two-pass extraction with LLM enrichment
```

## Data Model

### ScenarioMapping

Each extracted scenario is a `ScenarioMapping` dataclass with:

| Field | Column | Description |
|-------|--------|-------------|
| `scenario_name` | A | Human-readable label derived from issue |
| `drug_id` | B | CHEMBL drug ID |
| `variant_id` | C | Main variant page ID |
| `variant_pgx` | D | Pharmacogenetics variant |
| `variant_molqtl` | E | Molecular QTL variant |
| `target_id` | F | Single Ensembl gene ID |
| `target_ids` | G | Comma-separated Ensembl IDs |
| `aotf_diseases` | H | Diseases for AOTF list |
| `disease_id` | I | EFO/MONDO disease ID |
| `aotf_genes` | J | Gene symbols for AOTF list |
| `disease_search` | K | Free-text disease search |
| `disease_alt` | L | Alternative disease IDs |
| `gwas_study` | M | GWAS study ID |
| `qtl_study` | N | Molecular QTL study ID |
| `credible_set_l2g` | O | L2G credible set hash |
| `credible_set_gwas` | P | GWAS credible set hash |
| `credible_set_qtl` | Q | QTL credible set hash |
| `source_url` | R | GitHub issue URL |

## Importing to Google Sheets

1. Run the miner to generate `mined-scenarios.csv`
2. In Google Sheets: **File** → **Import** → **Upload**
3. Select the CSV file
4. Choose "Append to current sheet"
5. Set separator to "Comma"
6. Click "Import data"

## Extensibility

### Custom Extractor

```python
from ot_miner.extractors import BaseExtractor
from ot_miner.models import GitHubIssue, ScenarioMapping, ExtractionResult
from typing import List, Optional

class CustomExtractor(BaseExtractor):
    def extract(self, issue: GitHubIssue) -> Optional[ScenarioMapping]:
        # Your extraction logic here
        pass
    
    def extract_batch(self, issues: List[GitHubIssue]) -> List[ExtractionResult]:
        # Batch processing logic
        pass

```

### Custom Writer

```python
from ot_miner.writers import BaseWriter
from ot_miner.models import ScenarioMapping
from pathlib import Path
from typing import List

class CustomWriter(BaseWriter):
    def write(self, mappings: List[ScenarioMapping], path: Path) -> None:
        # Your output logic here
        pass

# Use in MultiWriter
from ot_miner.writers import MultiWriter

writers = MultiWriter()
writers.add_writer("custom", CustomWriter())
```

## Troubleshooting

### LLM not enriching

Ensure `ANTHROPIC_API_KEY` is set:
```bash
echo $ANTHROPIC_API_KEY  # Should print your API key
```

### GitHub rate limiting

Use a GitHub token to increase rate limits:
```bash
export GITHUB_TOKEN=ghp_xxx
```

### Large issue bodies

The LLM pipeline truncates issue bodies to 1500 characters to keep prompts manageable. Adjust in `ot_miner/extractors/llm.py` if needed.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

Apache License 2.0 - see LICENSE file for details

## Acknowledgments

- Built for the [Open Targets Platform](https://www.opentargets.org/)
- Uses Claude API from [Anthropic](https://www.anthropic.com/)
- GitHub API integration via [PyGithub](https://github.com/PyGithub/PyGithub)

## Citation

If you use this tool in your research, please cite:

```bibtex
@software{opentargets_issue_miner_2024,
  title={Open Targets GitHub Issue Scenario Miner},
  author={Open Targets},
  year={2026},
  url={https://github.com/opentargets/ot-github-issue-miner}
}
```

## Support

For issues, questions, or suggestions:
- Open an [GitHub Issue](https://github.com/opentargets/ot-github-issue-miner/issues)
- Check [existing documentation](./README.md)
- Review [architecture documentation](./docs/ARCHITECTURE.md) (if available)
