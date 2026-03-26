#!/usr/bin/env python3
"""
Local test script for running the scenario miner with LLM.

This runs the same mining process as the GitHub action but with LLM enabled.
Good for testing locally on a small number of recent issues before deploying.

Usage:
    python test_llm_local.py [--days N] [--output-dir DIR]

Examples:
    # Mine issues from last 7 days with LLM
    python test_llm_local.py --days 7
    
    # Mine issues from last 30 days, save to test-results/
    python test_llm_local.py --days 30 --output-dir test-results

Required environment variables:
    ANTHROPIC_API_KEY - Your Anthropic API key for LLM
    GITHUB_TOKEN      - GitHub PAT for higher API limits (optional but recommended)
"""

import os
import sys
import subprocess
from datetime import datetime, timedelta

def main():
    # Check for required environment variables
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Error: ANTHROPIC_API_KEY not set")
        print("\nSet it with:")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        return 1
    
    if not os.getenv("GITHUB_TOKEN"):
        print("⚠️  Warning: GITHUB_TOKEN not set (API rate limits will be lower)")
        print("Set it with:")
        print("  export GITHUB_TOKEN='your-token-here'\n")
    
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(
        description="Run scenario miner with LLM on recent issues"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days back to mine (default: 7)"
    )
    parser.add_argument(
        "--output-dir",
        default="./test-results",
        help="Output directory for results (default: ./test-results)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    args = parser.parse_args()
    
    # Calculate date
    since_date = datetime.now() - timedelta(days=args.days)
    since_date_str = since_date.strftime("%Y-%m-%d")
    
    print(f"🚀 Running scenario miner with LLM")
    print(f"📅 Mining issues since: {since_date_str} ({args.days} days ago)")
    print(f"📂 Output directory: {args.output_dir}")
    print(f"🤖 LLM model: {os.getenv('LLM_MODEL', 'claude-3-5-sonnet-20241022')}")
    print()
    
    # Build command - same as GitHub action but WITH LLM
    cmd = [
        ".venv/bin/python",
        "-m",
        "ot_miner.cli",
        "--output-dir", args.output_dir,
        "--since-date", since_date_str,
    ]
    
    if args.verbose:
        cmd.append("--verbose")
    
    print(f"💻 Running: {' '.join(cmd)}\n")
    
    # Run the command
    try:
        result = subprocess.run(cmd, check=True)
        print(f"\n✅ Mining complete!")
        print(f"📁 Results saved to: {args.output_dir}/")
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Mining failed with exit code {e.returncode}")
        return e.returncode
    except FileNotFoundError:
        print("\n❌ Error: Could not find .venv/bin/python")
        print("Make sure you've installed dependencies with: uv sync")
        return 1


if __name__ == "__main__":
    sys.exit(main())
