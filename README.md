# ot-github-issue-miner

Mines OT issues to get testing scenarios.

This is a production-grade Python package for mining GitHub issues from the [opentargets/issues](https://github.com/opentargets/issues) repository and extracting test scenarios in formats suitable for data analysis and Google Sheets import.

## Quick Links

- **📖 [Full Documentation](README_NEW.md)** - Comprehensive guide with quick start, architecture, and examples
- **⚡ [Quick Reference](QUICKREF.md)** - Common commands and patterns
- **🏗️ [Architecture](ARCHITECTURE.md)** - Deep dive into package design
- **🛠️ [Development Guide](DEVELOPMENT.md)** - Contributing and extending

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Run with LLM enrichment
ANTHROPIC_API_KEY=sk-ant-xxx python -m ot_miner.cli

# With GitHub token (higher rate limit)
GITHUB_TOKEN=ghp_xxx ANTHROPIC_API_KEY=sk-ant-xxx python -m ot_miner.cli
```

Or in Python:

```python
from ot_miner import ScenarioMiner, Config

config = Config.from_env()
miner = ScenarioMiner(config)
mappings = miner.run()

for mapping in mappings:
    print(f"{mapping.scenario_name}: {mapping.drug_id} → {mapping.target_id}")
```

## Key Features

- ✅ **Two-pass extraction**: Regex (fast) + LLM (accurate, via LangChain)
- ✅ **Production ready**: Error handling, rate limiting, logging
- ✅ **Extensible architecture**: Custom extractors, writers
- ✅ **No external APIs needed**: Run regex-only for free

## License

See [LICENSE](LICENSE)
