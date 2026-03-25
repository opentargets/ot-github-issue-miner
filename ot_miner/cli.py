#!/usr/bin/env python
"""
Command-line entry point for the Open Targets scenario miner.

Two-pass scenario miner for opentargets/issues → Google Sheets CSV format:
  Pass 1 — Regex: fast, free, catches explicit IDs in issue text
  Pass 2 — LLM (claude-haiku): understands context, fills gaps regex misses

Setup:
  pip install -r requirements.txt

Usage:
  # Regex-only (no API cost):
  python -m ot_miner.cli

  # Regex + LLM enrichment (recommended):
  ANTHROPIC_API_KEY=sk-ant-xxx python -m ot_miner.cli

  # With GitHub token (avoid 60 req/hr rate limit):
  GITHUB_TOKEN=ghp_xxx ANTHROPIC_API_KEY=sk-ant-xxx python -m ot_miner.cli

Import into Google Sheets:
  File → Import → Upload mined-scenarios.csv
  Import location: "Append to current sheet"
  Separator: Comma → Import data
"""

import sys
import logging
import argparse
from pathlib import Path

from ot_miner.config import Config
from ot_miner.miner import ScenarioMiner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Mine GitHub issues for Open Targets test scenarios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for CSV and JSON files",
    )
    
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip LLM enrichment pass (regex only)",
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        help="LLM batch size (default: 5)",
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = Config.from_env()
    
    # Override with CLI arguments
    if args.output_dir:
        config.output_dir = args.output_dir
    if args.no_llm:
        config.use_llm = False
    if args.verbose:
        config.verbose = True
        logger.setLevel(logging.DEBUG)
    if args.batch_size:
        config.llm_batch_size = args.batch_size
    
    try:
        # Run the miner
        miner = ScenarioMiner(config)
        mappings = miner.run()
        
        logger.info(f"✅ Mining complete: {len(mappings)} scenarios extracted")
        return 0
    
    except Exception as e:
        logger.error(f"❌ {str(e)}")
        if config.verbose:
            logger.exception("Full traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
