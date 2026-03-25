# Development Guide

This document provides architectural details and development patterns for the Open Targets Scenario Miner.

## Architecture Overview

### Design Principles

1. **Extensibility**: Every major component (extractors, writers, loaders) follows an abstract base class pattern
2. **Separation of Concerns**: Each module has a single, well-defined responsibility
3. **Type Safety**: Full type hints throughout the codebase
4. **Configuration as Code**: All settings injectable via Config object

### Module Responsibilities

#### `models.py`
- Core data structures using Python dataclasses
- `GitHubIssue`: GitHub API response wrapper
- `ScenarioMapping`: Normalized test scenario representation
- `ExtractionResult`: Wrapper for extraction output with confidence scores

#### `config.py`
- Environment-based configuration management
- Centralized settings with validation
- Path management for outputs
- GitHub API header construction

#### `utils.py`
- Compiled regex patterns for entity extraction
- Knowledge base dictionaries (gene→ENSG, disease→EFO, etc.)
- Helper functions for text processing
- CSV escaping and field merging logic

#### `loaders/__init__.py`
- `GitHubLoader`: Fetches issues with pagination and rate-limit awareness
- `IssueFilter`: Relevance filtering based on labels and keywords

#### `extractors/base.py`
- `BaseExtractor`: ABC defining the extractor interface

#### `extractors/regex.py`
- `RegexExtractor`: Fast pattern-based extraction (Pass 1)
- `AdaptiveRegexExtractor`: Enhanced regex with knowledge base inference

#### `extractors/llm.py`
- `LLMExtractor`: Claude API-based enrichment (Pass 2)
- Batch processing with configurable size and rate limiting
- System prompt design for bioinformatics context

#### `writers/__init__.py`
- `BaseWriter`: ABC for output formatting
- `CSVWriter`: Google Sheets compatible CSV output
- `JSONWriter`: Pretty-printed JSON for manual inspection
- `JSONLWriter`: Streaming JSON Lines format
- `MultiWriter`: Writes to multiple formats simultaneously

#### `miner.py`
- `ScenarioMiner`: Main orchestration class
- Pipeline composition: loader → regex → LLM → writers
- Statistics and summary generation

#### `cli.py`
- Command-line interface with argparse
- Environment variable loading
- Error handling and logging

## Extraction Pipeline

### Pass 1: Regex Extraction

```python
# Input: GitHubIssue
# Process:
1. Filter issues for relevance (labels + keywords)
2. Extract explicit identifiers using compiled regex patterns:
   - CHEMBL IDs
   - Ensembl gene IDs
   - EFO/MONDO disease IDs
   - Variant calls
   - Study IDs (GWAS, QTL)
   - Credible set hashes
3. Extract inferred identifiers (if using AdaptiveRegexExtractor):
   - Gene symbol → Ensembl ID lookup
   - Disease name → EFO/MONDO lookup
# Output: ScenarioMapping (or None if not relevant)
```

**Performance**: O(n) where n = number of issues, ~1-2 seconds for 100+ issues

**Cost**: Free (no API calls)

### Pass 2: LLM Enrichment

```python
# Input: ScenarioMapping from Pass 1 + original GitHubIssue
# Process:
1. Batch issues (configurable size, default 5)
2. Construct detailed prompt with:
   - Target schema
   - Known entity mappings
   - Extraction rules and priorities
   - Regex results for reference
3. Call Claude API
4. Parse JSON response
5. Merge LLM results with regex baseline (LLM wins for non-empty fields)
6. Respect rate limits between batches
# Output: Enriched ScenarioMapping
```

**Performance**: ~5-15 seconds per batch of 5 issues (depends on API latency)

**Cost**: ~$0.01-0.03 per mined scenario

## Data Flow

```
┌─────────────────┐
│  GitHub API     │
│  (opentargets)  │
└────────┬────────┘
         │ fetch_all_issues()
         ▼
┌─────────────────────────────────┐
│  GitHubLoader                   │
│  - Pagination (100 items/page)  │
│  - Rate-limit aware             │
│  - Returns List[GitHubIssue]    │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  RegexExtractor (Pass 1)        │
│  - Pattern matching             │
│  - Relevance filtering          │
│  - Knowledge base inference     │
│  Returns List[ScenarioMapping]  │
└────────┬────────────────────────┘
         │
         ▼
    [BRANCH 1]
    ├─→ Skip LLM (regex_only mode)
    │   └─→ Output results
    │
    [BRANCH 2]
    └─→ Conditional: if ANTHROPIC_API_KEY
        └─→
┌──────────────────────────────────┐
│  LLMExtractor (Pass 2)           │
│  - Batch processing             │
│  - Claude API calls             │
│  - Merge with regex baseline    │
│  - Returns List[ScenarioMapping]│
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│  MultiWriter                     │
│  - CSVWriter → .csv             │
│  - JSONWriter → .json           │
│  - JSONLWriter → .jsonl         │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│  Output Files                    │
│  - mined-scenarios.csv          │
│  - mined-scenarios.json         │
└──────────────────────────────────┘
```

## Extension Patterns

### Adding a New Extractor

```python
# ot_miner/extractors/custom.py
from ot_miner.extractors.base import BaseExtractor
from ot_miner.models import GitHubIssue, ScenarioMapping, ExtractionResult
from typing import List, Optional

class NeuralExtractor(BaseExtractor):
    """Extract using a small neural model."""
    
    def __init__(self):
        # Load your model here
        self.model = load_model()
    
    def extract(self, issue: GitHubIssue) -> Optional[ScenarioMapping]:
        # Single issue extraction
        pass
    
    def extract_batch(self, issues: List[GitHubIssue]) -> List[ExtractionResult]:
        # Batch extraction (more efficient)
        pass

# Note: ScenarioMiner orchestrates extraction directly.
# For custom extraction workflows, implement BaseExtractor interface.
```

### Adding a New Output Format

```python
# ot_miner/writers/tsv.py
from ot_miner.writers import BaseWriter
from ot_miner.models import ScenarioMapping
from pathlib import Path
from typing import List
import csv

class TSVWriter(BaseWriter):
    """Write scenarios to tab-separated format."""
    
    def write(self, mappings: List[ScenarioMapping], path: Path) -> None:
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter='\t')
            writer.writerow(HEADERS)
            for mapping in mappings:
                writer.writerow(mapping.to_row())

# Usage:
from ot_miner.writers import MultiWriter

writers = MultiWriter()
writers.add_writer("csv", CSVWriter())
writers.add_writer("json", JSONWriter())
writers.add_writer("tsv", TSVWriter())
```

### Custom Filtering

```python
# Extend IssueFilter for domain-specific relevance

from ot_miner.loaders import IssueFilter
from ot_miner.models import GitHubIssue

class BioInformaticsIssueFilter(IssueFilter):
    RELEVANT_KEYWORDS = IssueFilter.RELEVANT_KEYWORDS + [
        "genomic",
        "variant effect",
        "pathway",
        "biomarker",
    ]

# Use in RegexExtractor:
regex_extractor = RegexExtractor(filter_issues=True)
regex_extractor.issue_filter = BioInformaticsIssueFilter()
```

## Performance Optimization

### Batch Size Tuning

```python
# Smaller batches for faster per-item response
config.llm_batch_size = 3  # More API calls but smaller context per call

# Larger batches for cost optimization
config.llm_batch_size = 10  # Fewer API calls but larger prompts
```

### Rate Limiting

```python
# Adjust delay between batches to respect API rate limits
config.llm_delay_ms = 1000  # 1 second between batches
```

### Parallel Processing

For large repositories, consider:

```python
# Split issues into chunks and process in parallel
from concurrent.futures import ThreadPoolExecutor
from ot_miner.extractors import RegexExtractor

extractor = RegexExtractor()

def process_chunk(chunk):
    return extractor.extract_batch(chunk)

with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(process_chunk, issue_chunks))
```

## Logging

```python
import logging

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("ot_miner")

# Or via config
config.verbose = True
```

## Debugging

### Inspect Extraction Results

```python
from ot_miner import ScenarioMiner, Config

miner = ScenarioMiner(Config.from_env())
mappings = miner.run()

# Examine specific mapping
for m in mappings:
    if m.drug_id:
        print(f"{m.scenario_name}: drug={m.drug_id}")
    
    # Check confidence (if from LLM)
    # Results don't store confidence, but first pass vs LLM pass can be distinguished
```

### Test Individual Components

```python
from ot_miner.loaders import GitHubLoader
from ot_miner.extractors import RegexExtractor
from ot_miner.config import Config

config = Config.from_env()

# Test loader
loader = GitHubLoader(config)
issues = loader.fetch_all_issues()
print(f"Fetched {len(issues)} issues")

# Test extractor on first issue
extractor = RegexExtractor()
if issues:
    result = extractor.extract(issues[0])
    print(f"Extracted: {result}")
```

## Common Issues

### ImportError: No module named 'anthropic'

```bash
pip install anthropic
```

### ANTHROPIC_API_KEY not found

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python -m ot_miner.cli
```

### Rate limited by GitHub API

Use a personal access token:

```bash
export GITHUB_TOKEN=ghp_...
python -m ot_miner.cli
```

### Large prompt errors from LLM

Reduce batch size:

```bash
export LLM_BATCH_SIZE=3
```

## Testing Guidelines

Test coverage should include:

- [ ] Regex pattern matching accuracy
- [ ] GitHub loader pagination
- [ ] Issue filtering logic
- [ ] ScenarioMapping serialization
- [ ] CSV/JSON output formatting
- [ ] LLM response parsing
- [ ] Error handling and graceful fallbacks
- [ ] Rate-limit behavior

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ot_miner --cov-report=html

# Run specific test file
pytest tests/test_extractors.py -v
```

## Release Checklist

- [ ] Update version in setup.py and __init__.py
- [ ] Update CHANGELOG.md
- [ ] Run full test suite
- [ ] Update documentation
- [ ] Tag release in git
- [ ] Build distribution packages
- [ ] Upload to PyPI

```bash
# Build distribution
python -m build

# Upload to PyPI test server
python -m twine upload --repository testpypi dist/*

# Upload to PyPI
python -m twine upload dist/*
```
