#!/usr/bin/env python
"""
Quick reference and package summary for Open Targets Scenario Miner.
"""

# ==============================================================================
# PACKAGE STRUCTURE
# ==============================================================================

"""
ot-github-issue-miner/
├── ot_miner/                           # Main Python package
│   ├── __init__.py                     # Package exports + version
│   ├── __main__.py                     # python -m ot_miner support
│   ├── models.py                       # Data models (ScenarioMapping, etc)
│   ├── config.py                       # Configuration management
│   ├── utils.py                        # Utilities: regex, helpers, KBs
│   ├── cli.py                          # Command-line interface
│   ├── miner.py                        # Main orchestrator
│   ├── loaders/
│   │   └── __init__.py                 # GitHub loader + filtering
│   ├── extractors/
│   │   ├── __init__.py                 # Extractor exports
│   │   ├── base.py                     # Abstract base extractor
│   │   ├── regex.py                    # Regex extraction (Pass 1)
│   │   └── llm.py                      # LLM enrichment (Pass 2)
│   └── writers/
│       └── __init__.py                 # CSV, JSON, JSONL writers
├── setup.py                            # Package metadata
├── requirements.txt                    # Dependencies
├── README.md                           # User guide (original)
├── README_NEW.md                       # Comprehensive user guide
├── DEVELOPMENT.md                      # Dev guide & patterns
├── ARCHITECTURE.md                     # Architecture details
├── examples.py                         # Usage examples
└── LICENSE                             # Apache 2.0
"""

# ==============================================================================
# KEY FEATURES
# ==============================================================================

"""
✅ Two-Pass Extraction
   Pass 1 (Regex)     - Fast, free, ~60-70% coverage, instant
   Pass 2 (LLM)       - Context-aware, ~85-95% coverage, ~30-60s

✅ Extensible Architecture
   - Pluggable extractors (BaseExtractor ABC)
   - Multiple output formats (BaseWriter ABC)
   - Custom filters and knowledge bases
   - Clear separation of concerns

✅ Production-Ready
   - Type hints throughout
   - Comprehensive logging
   - Error handling with graceful fallbacks
   - Rate-limit aware
   - Dataclass-based models

✅ Comprehensive Entity Detection
   - Drugs (CHEMBL IDs)
   - Genes (Ensembl IDs with inference)
   - Diseases (EFO/MONDO ontology)
   - Variants (pharmacogenomic, molecular QTL)
   - Studies (GWAS, molecular QTL)
   - Credible sets

✅ Google Sheets Integration
   - CSV export in exact sheet format
   - One-click import: File → Import → Upload
"""

# ==============================================================================
# QUICK START
# ==============================================================================

"""
Installation:
    pip install -e .
    pip install -r requirements.txt

CLI Usage:
    # Regex only (free)
    python -m ot_miner.cli
    
    # With LLM (requires API key)
    ANTHROPIC_API_KEY=sk-ant-xxx python -m ot_miner.cli
    
    # With GitHub token (higher rate limit)
    GITHUB_TOKEN=ghp_xxx ANTHROPIC_API_KEY=sk-ant-xxx python -m ot_miner.cli

Python API:
    from ot_miner import ScenarioMiner, Config
    
    config = Config.from_env()
    miner = ScenarioMiner(config)
    mappings = miner.run()
"""

# ==============================================================================
# CORE COMPONENTS
# ==============================================================================

"""
class Configuration (config.py)
    - Loads settings from environment
    - Provides validated paths and credentials
    - Integration point for all settings

class ScenarioMapping (models.py)
    - 18 fields aligned to Google Sheets columns
    - Serialization methods (to_dict, to_row, to_json)
    - Represents extracted test scenario

class GitHubLoader (loaders/__init__.py)
    - Fetches issues with pagination (100/page)
    - Rate-limit aware (250ms between pages)
    - Optional authentication

class RegexExtractor (extractors/regex.py)
    - Pass 1: Pattern matching
    - 9+ compiled regex patterns
    - Knowledge base inference (genes, diseases, drugs)

class LLMExtractor (extractors/llm.py)
    - Pass 2: Claude API enrichment
    - Batch processing (configurable size)
    - Merges with regex results
    - Rate-limit aware

class MultiWriter (writers/__init__.py)
    - Orchestrates multiple output formats
    - CSV (Google Sheets compatible)
    - JSON (pretty-printed)
    - JSONL (streaming)
    - Extensible: add TSV, Parquet, etc.

class ScenarioMiner (miner.py)
    - Main orchestrator
    - Composes: Loader → Extractors → Writers
    - Statistics and summary generation
"""

# ==============================================================================
# CONFIGURATION
# ==============================================================================

"""
Environment Variables:
    GITHUB_OWNER              opentargets (optional)
    GITHUB_REPO               issues (optional)
    GITHUB_TOKEN              ghp_xxx (optional, for rate limits)
    
    ANTHROPIC_API_KEY         sk-ant-xxx (optional, for LLM)
    LLM_MODEL                 claude-haiku-4-5 (optional)
    LLM_BATCH_SIZE            5 (optional)
    LLM_DELAY_MS              500 (optional)
    
    OUTPUT_DIR                ./output (optional)
    CSV_FILENAME              mined-scenarios.csv (optional)
    JSON_FILENAME             mined-scenarios.json (optional)
    
    VERBOSE                   true/false (optional)

Programmatic Configuration:
    config = Config(
        github_token="ghp_xxx",
        anthropic_api_key="sk-ant-xxx",
        llm_batch_size=10,
        output_dir=Path("/tmp/output"),
        verbose=True,
    )
"""

# ==============================================================================
# EXTENSIBILITY EXAMPLES
# ==============================================================================

"""
Custom Extractor:
    from ot_miner.extractors import BaseExtractor
    
    class MyExtractor(BaseExtractor):
        def extract(self, issue):
            # Single issue extraction
            pass
        
        def extract_batch(self, issues):
            # Batch extraction
            pass

Custom Writer:
    from ot_miner.writers import BaseWriter
    
    class TSVWriter(BaseWriter):
        def write(self, mappings, path):
            # Write to TSV format
            pass

Composing Custom Extractors:
    # Implement BaseExtractor interface
    # ScenarioMiner automatically runs extraction passes
"""

# ==============================================================================
# FILE DESCRIPTIONS
# ==============================================================================

FILES = {
    # Core package
    "__init__.py": {
        "exports": [
            "Config", "ScenarioMiner",
            "ScenarioMapping", "GitHubIssue",
            "RegexExtractor", "LLMExtractor",
            "CSVWriter", "JSONWriter",
        ],
        "lines": "~50",
    },
    
    # Configuration
    "config.py": {
        "classes": ["Config"],
        "methods": ["from_env", "get_github_headers"],
        "lines": "~80",
    },
    
    # Data models
    "models.py": {
        "classes": ["GitHubIssue", "ScenarioMapping", "ExtractionResult"],
        "enums": ["IssueState"],
        "lines": "~150",
    },
    
    # Utilities
    "utils.py": {
        "patterns": ["REGEX_PATTERNS (9 compiled)"],
        "knowledge_bases": ["GENE_TO_ENSEMBL", "DISEASE_TO_ONTOLOGY", "DRUG_TO_CHEMBL"],
        "functions": ["find_all", "extract_gene_symbols", "csv_escape", "merge_extraction_fields"],
        "lines": "~200",
    },
    
    # CLI
    "cli.py": {
        "classes": ["(CLI functions)"],
        "entry_point": "main()",
        "lines": "~80",
    },
    
    # Orchestration
    "miner.py": {
        "classes": ["ScenarioMiner"],
        "methods": ["run", "_pass_1_regex", "_pass_2_llm", "_write_outputs"],
        "lines": "~150",
    },
    
    # Loaders
    "loaders/__init__.py": {
        "classes": ["GitHubLoader", "IssueFilter"],
        "lines": "~120",
    },
    
    # Extractors
    "extractors/base.py": {
        "classes": ["BaseExtractor"],
        "lines": "~80",
    },
    
    "extractors/regex.py": {
        "classes": ["RegexExtractor", "AdaptiveRegexExtractor"],
        "lines": "~180",
    },
    
    "extractors/llm.py": {
        "classes": ["LLMExtractor"],
        "methods": ["extract_batch", "_process_batch"],
        "lines": "~320",
    },
    
    # Writers
    "writers/__init__.py": {
        "classes": ["BaseWriter", "CSVWriter", "JSONWriter", "JSONLWriter", "MultiWriter"],
        "lines": "~200",
    },
}

# ==============================================================================
# STATISTICS
# ==============================================================================

"""
Code Metrics:
    Total Lines of Code:     ~2000
    Core Package:            ~1800 lines
    Number of Classes:       ~20
    Number of Methods:       ~80+
    Test Coverage Target:    >80%
    
Package Size:
    Source Code:             ~50 KB
    With Dependencies:       ~100 MB (including anthropic, requests)
    Pip Package:             ~200 KB
    
Performance:
    Regex Extraction:        O(n) time, instant for small repos
    LLM Enrichment:          ~5-15 sec per batch of 5 issues
    Memory Usage:            ~100 MB for 500+ issues
    
API Costs:
    Regex Only:              $0
    Regex + LLM:             ~$0.01-0.03 per scenario
    1000 scenarios:          ~$10-30
"""

# ==============================================================================
# DEVELOPMENT COMMANDS
# ==============================================================================

"""
Install for development:
    pip install -e ".[dev]"

Run tests:
    pytest
    pytest --cov=ot_miner
    pytest tests/test_extractors.py -v

Code quality:
    black ot_miner/
    ruff check ot_miner/
    mypy ot_miner/

Run from source:
    python -m ot_miner.cli
    
    # Or:
    python -c "from ot_miner import ScenarioMiner; ..."

Build distribution:
    python -m build
    twine upload dist/*
"""

# ==============================================================================
# COMMON TASKS
# ==============================================================================

"""
Task: Extract scenarios without API calls
    python -m ot_miner.cli

Task: Enrich with LLM
    ANTHROPIC_API_KEY=sk-ant-xxx python -m ot_miner.cli

Task: Analyze results
    python examples.py 7  # Run example 7

Task: Import to Google Sheets
    1. Run miner to generate mined-scenarios.csv
    2. In Sheets: File → Import → Upload
    3. Select "Append to current sheet", separator "Comma"

Task: Create custom extractor
    1. Create class inheriting from BaseExtractor
    2. Implement extract() and extract_batch()
    3. Use directly or integrate into ScenarioMiner

Task: Add new output format
    1. Create class inheriting from BaseWriter
    2. Implement write() method
    3. Add to MultiWriter
"""

# ==============================================================================
# TROUBLESHOOTING
# ==============================================================================

"""
Problem: "ModuleNotFoundError: No module named 'anthropic'"
Solution: pip install anthropic

Problem: "ANTHROPIC_API_KEY not found"
Solution: export ANTHROPIC_API_KEY=sk-ant-xxx

Problem: "GitHub rate limited"
Solution: export GITHUB_TOKEN=ghp_xxx

Problem: "LLM batch failed"
Solution: Lower LLM_BATCH_SIZE (export LLM_BATCH_SIZE=3)

Problem: "Large memory usage"
Solution: Process in chunks (see examples.py #11)

Problem: "Slow extraction"
Solution: Increase LLM_BATCH_SIZE (costs more but fewer API calls)
"""

# ==============================================================================
# NEXT STEPS
# ==============================================================================

"""
1. Read README.md for user-facing guide
2. Check examples.py for usage patterns
3. Review DEVELOPMENT.md for architecture details
4. See ARCHITECTURE.md for design decisions
5. Run tests: pytest
6. Try: python -m ot_miner.cli
7. Extend: Create custom extractors/writers
"""

if __name__ == "__main__":
    print(__doc__)
