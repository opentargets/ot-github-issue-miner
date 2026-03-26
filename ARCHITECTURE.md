# Architecture Overview

A detailed guide to the Open Targets Scenario Miner's design, components, and extensibility.

## High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                    ScenarioMiner (Orchestrator)                │
│  Coordinates: GitHub Loader → Extractors → Writers             │
└──────────────────┬──────────────────────────────────────────────┘
                   │
        ┌──────────┼──────────┬────────────┬──────────────┐
        │          │          │            │              │
        ▼          ▼          ▼            ▼              ▼
   ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐   ┌────────┐
   │Config  │  │Loader  │  │ExtPass1│  │ExtPass2│   │Writers │
   │        │  │        │  │(Regex) │  │(LLM)   │   │        │
   │- Env   │  │-GitHub │  │- Patterns  │- Claude│   │- CSV   │
   │- Paths │  │- Auth  │  │-           │- Batch │   │- JSON  │
   │- LLM   │  │- Pagina│  │-           │- Merge │   │        │
   └────────┘  └────────┘  └────────┘  └────────┘   └────────┘
```

## Component Hierarchy

### Core Modules

#### 1. **models.py** - Data Contracts
Defines all domain objects and schemas:

```python
# Main entities
- GitHubIssue: API response wrapper with structured fields
- ScenarioMapping: Test scenario with ~ 18 fields aligned to Google Sheets
- ExtractionResult: Wrapper with confidence scores
- IssueState: Enum for open/closed states
- GitHubLabel: Label wrapper with normalization
```

**Why structured dataclasses?**
- Type safety with mypy
- Automatic serialization (to_dict, to_row)
- IDE autocomplete and refactoring support
- Clear schema documentation

#### 2. **config.py** - Settings Management
Centralized configuration with environment loading:

```python
class Config:
  - GitHub credentials & API settings
  - LLM settings (model, batch size, delays)
  - Output paths and filenames
  - Feature flags (verbose, use_llm)
  
Methods:
  - from_env(): Load from environment variables
  - csv_path, json_path: Computed output paths
  - get_github_headers(): HTTP headers for GitHub API
```

**Benefits:**
- No magic strings throughout codebase
- Easy testing with different configs
- Single source of truth for settings
- Method chaining ready

#### 3. **utils.py** - Helpers & Knowledge Bases
Utility functions and curated entity mappings:

```python
# Regex patterns (compiled for performance)
REGEX_PATTERNS: dict with 9+ patterns for entity type detection

# Knowledge bases (for inference)
GENE_TO_ENSEMBL: ~14 common gene → Ensembl ID mappings
DISEASE_TO_ONTOLOGY: ~10 disease → EFO/MONDO mappings
DRUG_TO_CHEMBL: ~5 drug → CHEMBL ID mappings

# Functions
- find_all(): Unique regex matches
- extract_gene_symbols(): Smart gene symbol extraction
- csv_escape(): Safe CSV formatting
- merge_extraction_fields(): LLM + regex field merging
```

**Rationale:**
- Precompiled patterns: ~10x faster than runtime compilation
- Curated knowledge base: High precision with no external API calls
- Pure functions: Testable, composable, predictable

#### 4. **loaders/__init__.py** - Data Input

```python
class GitHubLoader:
  - Pagination: 100 items/page
  - Rate-limiting: 250ms between pages
  - Headers: Optional token auth
  - Returns: Fully parsed GitHubIssue objects

class IssueFilter:
  - Relevance filtering (labels + keywords)
  - Label-based: bug, frontend, platform, aotf, api
  - Keyword-based: 20+ bioinformatics terms
  - Extensible: Easy to add custom filters
```

**Design pattern:** Strategy pattern for filtering

#### 5. **extractors/** - Entity Extraction

##### base.py: Interface Definition
```python
class BaseExtractor (abstract):
  - extract(issue) → ScenarioMapping | None
  - extract_batch(issues) → List[ExtractionResult]
```

**Why ABC?** Enables pluggable strategies and clear contracts

##### regex.py: Fast Extraction
```python
class RegexExtractor(BaseExtractor):
  - Simple pattern matching for explicit IDs
  - Relevance filtering (labels + keywords)
  - No inference - only extracts what's present
  - Returns confidence ~0.7
```

**Performance:** O(n) time, O(1) memory per issue
**Purpose:** Filter relevant issues and extract explicit identifiers only

##### llm.py: Smart Enrichment
```python
class LLMExtractor(BaseExtractor):
  - Batch processing: 1-10 issues per API call
  - Context-aware: Full issue text + schema
  - Merging: LLM wins for non-empty fields
  - Rate limiting: Configurable delays
  - Confidence: ~0.9
  
Methods:
  - extract_batch(): Process multiple issues efficiently
  - _process_batch(): Single LLM API call
```


#### 6. **writers/** - Output Formatting

```python
class BaseWriter (abstract):
  - write(mappings, path)

Implementations:
- CSVWriter: Google Sheets compatible (quoted, escaped)
- JSONWriter: Pretty-printed with indentation
- MultiWriter: Orchestrates multiple writers
```

**Extensibility:** Easy to add TSV, Parquet, Excel, etc.

#### 7. **miner.py** - Orchestration

```python
class ScenarioMiner:
  - Composes: Loader → Extractors → Writers
  - Phases:
    1. Fetch all issues from GitHub
    2. Pass 1: Regex extraction
    3. Pass 2: LLM enrichment (optional)
    4. Output to configured formats
    5. Print statistics
```

**Two-pass design rationale:**
- Pass 1 (Regex): 90% coverage, free, instant
- Pass 2 (LLM): Last 10% with context, costs $, takes ~30-60s

#### 8. **cli.py** - Command-Line Interface

```python
- argparse for CLI arguments
- ENV → Config conversion
- Logging setup
- Error handling with exit codes
```

## Data Flow

### Complete Mining Pipeline

```
┌─────────────────────┐
│ GitHub API Stream   │
│ opentargets/issues  │
└──────────┬──────────┘
           │ (paginated, 100/page)
           ▼
┌──────────────────────────┐
│ GitHubLoader             │
│ - Handles pagination     │
│ - Rate limiting (250ms)  │
│ - Returns 500+ issues    │
└──────────┬───────────────┘
           │ List[GitHubIssue]
           ▼
┌──────────────────────────────┐
│ RegexExtractor (Pass 1)      │
│ - For each issue:            │
│   1. Filter by relevance     │
│   2. Match 9 regex patterns  │
│   3. Extract entities        │
│ - Returns ~200 mappings      │
└──────────┬───────────────────┘
           │ List[ScenarioMapping | None]
           ▼
       ┌───┴─────────────────┐
       │                     │
    [Regex Only Mode]   [Regex + LLM Mode]
       │                     │
       ▼                     ▼
    End             ┌──────────────────────┐
                    │ GroupBy: 5 issues    │
                    │ (LLM batch size)     │
                    └──────────┬───────────┘
                               │ Batch[ScenarioMapping]
                               ▼
                    ┌──────────────────────────┐
                    │ LLMExtractor (Pass 2)    │
                    │ - Call Claude API        │
                    │ - Parse response JSON    │
                    │ - Merge with regex base  │
                    │ - Respect rate limits    │
                    └──────────┬───────────────┘
                               │ Enriched List[ScenarioMapping]
                               ▼
            ┌──────────────────────────────────┐
            │ MultiWriter                      │
            ├──────────────────────────────────┤
            │ ├─ CSVWriter → .csv             │
            │ ├─ JSONWriter → .json           │
            │ └─ (extensible)                 │
            └──────────┬───────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
    [.csv]         [.json]      [???]
    
    Ready for Google Sheets import!
```

## Extension Points

### 1. Custom Extractor

```python
# ot_miner/extractors/my_extractor.py

from ot_miner.extractors.base import BaseExtractor

class MyExtractor(BaseExtractor):
    def extract(self, issue):
        # Single issue → ScenarioMapping
        pass
    
    def extract_batch(self, issues):
        # List of issues → List[ExtractionResult]
        pass

# The ScenarioMiner orchestrates the two-pass extraction automatically.
    # For custom workflows, implement BaseExtractor and compose in ScenarioMiner.
```

### 2. Custom Writer

```python
# ot_miner/writers/my_writer.py

from ot_miner.writers import BaseWriter

class TSVWriter(BaseWriter):
    def write(self, mappings, path):
        # mappings → TSV file
        pass

# Usage:
writers = MultiWriter()
writers.add_writer("tsv", TSVWriter())
```

## File Organization

```
ot_miner/
├── __init__.py          # Package exports
├── __main__.py          # python -m ot_miner
├── config.py            # Settings
├── models.py            # Data contracts
├── utils.py             # Helpers & patterns
├── cli.py               # Entry point
├── miner.py             # Orchestration
├── loaders/
│   └── __init__.py      # GitHub loader & filter
├── extractors/
│   ├── __init__.py      # Exports
│   ├── base.py          # ABC
│   ├── regex.py         # Pattern matching
│   └── llm.py           # Claude enrichment
└── writers/
    └── __init__.py      # Output writers

Root:
├── setup.py             # Distribution config
├── requirements.txt     # Dependencies
├── README.md            # User guide
├── DEVELOPMENT.md       # Dev guide
├── ARCHITECTURE.md      # This file
└── examples.py          # Usage examples
```

This architecture prioritizes **extensibility**, **maintainability**, and **clarity** while maintaining strong separation of concerns and clear data contracts between components.
