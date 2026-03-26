"""
Open Targets GitHub Issue Scenario Miner.

A Python package for mining GitHub issues in the opentargets/issues repository
and extracting test scenarios in a format suitable for Google Sheets.

Features:
  - Two-pass extraction: regex (fast, free) + LLM (context-aware, via LangChain)
  - Extensible architecture with pluggable extractors and writers
  - Support for multiple output formats (CSV, JSON, JSONL)
  - Rate-limit aware with configurable batch processing
  - Comprehensive entity extraction (drugs, genes, diseases, variants, studies)
  - LLM powered by Claude via LangChain

Quick Start:
  from ot_miner import ScenarioMiner, Config
  
  config = Config.from_env()
  miner = ScenarioMiner(config)
  mappings = miner.run()

For CLI usage:
  python -m ot_miner.cli --help
"""

from ot_miner.config import Config
from ot_miner.miner import ScenarioMiner
from ot_miner.models import (
    ScenarioMapping,
    GitHubIssue,
    ExtractionResult,
    SHEET_HEADERS,
)
from ot_miner.extractors import (
    BaseExtractor,
    RegexExtractor,
    LLMExtractor,
)
from ot_miner.loaders import GitHubLoader, IssueFilter
from ot_miner.writers import (
    BaseWriter,
    CSVWriter,
    JSONWriter,
    MultiWriter,
    create_default_writers,
)

__version__ = "0.1.0"
__author__ = "OpenTargets"

__all__ = [
    # Core
    "Config",
    "ScenarioMiner",
    
    # Models
    "ScenarioMapping",
    "GitHubIssue",
    "ExtractionResult",
    "SHEET_HEADERS",
    
    # Extractors
    "BaseExtractor",
    "RegexExtractor",
    "LLMExtractor",
    
    # Loaders
    "GitHubLoader",
    "IssueFilter",
    
    # Writers
    "BaseWriter",
    "CSVWriter",
    "JSONWriter",
    "MultiWriter",
    "create_default_writers",
]
