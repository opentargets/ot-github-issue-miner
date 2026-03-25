"""
Base extractor class defining the interface for all extractors.

Extractors are responsible for converting GitHub issues into
ScenarioMapping objects using various techniques (regex, LLM, etc.).
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import logging

from ot_miner.models import GitHubIssue, ScenarioMapping, ExtractionResult

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """
    Abstract base class for all extractors.
    
    Defines the interface that all extraction implementations must follow,
    allowing for easy addition of new extraction strategies (e.g., LLM,
    pattern matching, heuristics, etc.).
    """
    
    @abstractmethod
    def extract(self, issue: GitHubIssue) -> Optional[ScenarioMapping]:
        """
        Extract a scenario mapping from a GitHub issue.
        
        Args:
            issue: GitHubIssue to extract from
        
        Returns:
            ScenarioMapping if extraction succeeded, None if not relevant
        """
        pass
    
    @abstractmethod
    def extract_batch(self, issues: List[GitHubIssue]) -> List[ExtractionResult]:
        """
        Extract scenario mappings from multiple issues.
        
        Args:
            issues: List of GitHubIssues to extract from
        
        Returns:
            List of ExtractionResult objects
        """
        pass

