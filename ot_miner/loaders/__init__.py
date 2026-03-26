"""
GitHub API loader for fetching issues.

This module handles all interactions with the GitHub API,
including pagination and rate-limiting considerations.
"""

import time
import logging
from typing import List, Optional
import requests

from ot_miner.models import GitHubIssue
from ot_miner.config import Config

logger = logging.getLogger(__name__)


class GitHubLoader:
    """
    Loads GitHub issues from the opentargets/issues repository.
    
    Handles pagination, rate limiting, and optional authentication
    for increased rate limits.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the GitHub loader.
        
        Args:
            config: Application configuration with GitHub credentials
        """
        self.config = config
        self.base_url = f"https://api.github.com/repos/{config.github_owner}/{config.github_repo}/issues"
        self.comments_url = f"https://api.github.com/repos/{config.github_owner}/{config.github_repo}/issues"
        self.headers = config.get_github_headers()
    
    def fetch_all_issues(self) -> List[GitHubIssue]:
        """
        Fetch all GitHub issues (open and closed).
        
        Uses pagination to retrieve all available issues. Includes
        automatic rate-limit handling and progress output.
        
        Returns:
            List of GitHubIssue objects
        """
        issues: List[GitHubIssue] = []
        page = 1
        
        logger.info("⬇  Fetching GitHub issues (open + closed)…")
        
        params = {
            "state": "all",
            "per_page": 100,
            "page": page,
        }
        
        # Add date filter if specified
        if self.config.since_date:
            params["since"] = self.config.since_date.isoformat()
            logger.info(f"   Filtering issues since: {self.config.since_date.isoformat()}")
        
        while True:
            try:
                response = requests.get(
                    self.base_url,
                    headers=self.headers,
                    params=params,
                    timeout=10,
                )
                response.raise_for_status()
            except requests.RequestException as e:
                logger.error(f"Failed to fetch page {page}: {e}")
                raise
            
            batch = response.json()
            if not batch:
                break
            
            # Fetch issues with comments
            for item in batch:
                comments = self._fetch_issue_comments(item["number"])
                issue = GitHubIssue.from_api_response(item, comments)
                issues.append(issue)
            
            print(f"\r   {len(issues)} issues fetched…", end="", flush=True)
            
            # Check for next page in Link header
            link_header = response.headers.get("link", "")
            if 'rel="next"' not in link_header:
                break
            
            page += 1
            params["page"] = page
            time.sleep(0.25)  # Be respectful to API
        
        print()  # New line after progress
        logger.info(f"✅ {len(issues)} issues fetched")
        return issues
    
    def _fetch_issue_comments(self, issue_number: int) -> List[dict]:
        """
        Fetch all comments for a specific issue.
        
        Args:
            issue_number: GitHub issue number
        
        Returns:
            List of comment dictionaries from GitHub API
        """
        comments_url = f"{self.comments_url}/{issue_number}/comments"
        
        try:
            response = requests.get(
                comments_url,
                headers=self.headers,
                params={"per_page": 100},  # Most issues have < 100 comments
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.warning(f"Failed to fetch comments for issue #{issue_number}: {e}")
            return []


class IssueFilter:
    """
    Filters GitHub issues based on relevance criteria.
    
    Determines whether an issue is relevant to the scenario mining
    process based on labels and keywords.
    """
    
    # Labels that indicate relevance
    RELEVANT_LABELS = {
        "frontend",
        "platform",
        "bug",
        "aotf",
        "api",
    }
    
    # Keywords that indicate relevance
    RELEVANT_KEYWORDS = [
        "page", "widget", "association", "target", "disease", "variant",
        "drug", "study", "credible set", "l2g", "gwas", "qtl",
        "loading", "error", "broken", "fails", "missing", "incorrect",
        "not working", "display", "render", "search", "filter", "export",
    ]
    
    @classmethod
    def is_relevant(cls, issue: GitHubIssue) -> bool:
        """
        Check if an issue is relevant for scenario mining.
        
        Args:
            issue: GitHubIssue to evaluate
        
        Returns:
            True if the issue is relevant, False otherwise
        """
        # Check labels
        issue_labels = {label.name for label in issue.labels}
        if cls.RELEVANT_LABELS & issue_labels:
            return True
        
        # Check keywords in title and body
        text = f"{issue.title} {issue.body or ''}".lower()
        if any(keyword in text for keyword in cls.RELEVANT_KEYWORDS):
            return True
        
        return False
