"""
Configuration management for the scenario miner.

Loads and validates configuration from environment variables
and provides centralized access to all settings.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """Application configuration."""
    
    # GitHub settings
    github_owner: str = "opentargets"
    github_repo: str = "issues"
    github_token: str = ""
    
    # LLM settings
    anthropic_api_key: str = ""
    llm_model: str = "claude-haiku-4-5"
    llm_batch_size: int = 5
    llm_delay_ms: float = 500
    
    # Output settings
    output_dir: Path = Path.cwd()
    csv_filename: str = "mined-scenarios.csv"
    json_filename: str = "mined-scenarios.json"
    
    # Processing settings
    verbose: bool = False
    use_llm: bool = True
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            github_owner=os.getenv("GITHUB_OWNER", "opentargets"),
            github_repo=os.getenv("GITHUB_REPO", "issues"),
            github_token=os.getenv("GITHUB_TOKEN", ""),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            llm_model=os.getenv("LLM_MODEL", "claude-haiku-4-5"),
            llm_batch_size=int(os.getenv("LLM_BATCH_SIZE", "5")),
            llm_delay_ms=float(os.getenv("LLM_DELAY_MS", "500")),
            output_dir=Path(os.getenv("OUTPUT_DIR", os.getcwd())),
            csv_filename=os.getenv("CSV_FILENAME", "mined-scenarios.csv"),
            json_filename=os.getenv("JSON_FILENAME", "mined-scenarios.json"),
            verbose=os.getenv("VERBOSE", "").lower() in ("true", "1", "yes"),
        )
    
    def __post_init__(self):
        """Validate and normalize configuration."""
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set use_llm based on API key availability
        self.use_llm = bool(self.anthropic_api_key)
    
    @property
    def csv_path(self) -> Path:
        """Get full path to CSV output file."""
        return self.output_dir / self.csv_filename
    
    @property
    def json_path(self) -> Path:
        """Get full path to JSON output file."""
        return self.output_dir / self.json_filename
    
    def get_github_headers(self) -> dict:
        """Get HTTP headers for GitHub API requests."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        return headers
