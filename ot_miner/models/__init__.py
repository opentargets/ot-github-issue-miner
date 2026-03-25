"""
Data models and types for the Open Targets scenario miner.

This module defines the core data structures used throughout the application,
including GitHub issue representations and test scenario mappings.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List
from enum import Enum


class IssueState(str, Enum):
    """GitHub issue state enumeration."""
    OPEN = "open"
    CLOSED = "closed"


@dataclass
class GitHubLabel:
    """Represents a GitHub issue label."""
    name: str

    def __post_init__(self):
        self.name = self.name.lower()


@dataclass
class GitHubIssue:
    """Represents a GitHub issue with relevant metadata."""
    number: int
    title: str
    body: Optional[str]
    state: IssueState
    labels: List[GitHubLabel]
    html_url: str

    @classmethod
    def from_api_response(cls, data: dict) -> "GitHubIssue":
        """Create GitHubIssue from GitHub API response."""
        return cls(
            number=data["number"],
            title=data["title"],
            body=data.get("body"),
            state=IssueState(data["state"]),
            labels=[GitHubLabel(l["name"]) for l in data.get("labels", [])],
            html_url=data["html_url"],
        )


@dataclass
class ScenarioMapping:
    """
    Test scenario mapping aligned with Google Sheets columns.
    
    Each field maps to a specific sheet column and represents
    entity references relevant to Open Targets platform testing.
    """
    # Required fields
    scenario_name: str  # A — human-readable label
    source_url: str    # R — GitHub issue URL

    # Optional entity fields (empty string if not applicable)
    drug_id: str = ""                    # B — CHEMBL drug ID
    variant_id: str = ""                 # C — variant ID (main page)
    variant_pgx: str = ""                # D — pharmacogenetics variant
    variant_molqtl: str = ""             # E — molecular QTL variant
    target_id: str = ""                  # F — single Ensembl gene ID
    target_ids: str = ""                 # G — comma-separated Ensembl IDs
    aotf_diseases: str = ""              # H — diseases for AOTF list
    disease_id: str = ""                 # I — EFO or MONDO disease ID
    aotf_genes: str = ""                 # J — comma-separated gene symbols
    disease_search: str = ""             # K — free-text disease search
    disease_alt: str = ""                # L — alternative disease IDs
    gwas_study: str = ""                 # M — GWAS study ID
    qtl_study: str = ""                  # N — molecular QTL study ID
    credible_set_l2g: str = ""           # O — L2G credible set hash
    credible_set_gwas: str = ""          # P — GWAS credible set hash
    credible_set_qtl: str = ""           # Q — QTL credible set hash

    def to_row(self) -> List[str]:
        """Convert mapping to CSV row format."""
        return [
            self.scenario_name,
            self.drug_id,
            self.variant_id,
            self.variant_pgx,
            self.variant_molqtl,
            self.target_id,
            self.target_ids,
            self.aotf_diseases,
            self.disease_id,
            self.aotf_genes,
            self.disease_search,
            self.disease_alt,
            self.gwas_study,
            self.qtl_study,
            self.credible_set_l2g,
            self.credible_set_gwas,
            self.credible_set_qtl,
            self.source_url,
        ]

    def to_dict(self) -> dict:
        """Convert mapping to dictionary."""
        return asdict(self)


@dataclass
class ExtractionResult:
    """Result from pass 1 (regex) or pass 2 (LLM) extraction."""
    mapping: ScenarioMapping
    is_llm_enriched: bool = False
    confidence: float = 1.0


# Sheet header configuration
SHEET_HEADERS = [
    "Testing Scenario",
    "drug page test",
    "variant page test",
    "variant with pharmacogenetics",
    "Variant with molqtl",
    "Target page test",
    "Target page partial",
    "Target page List of AOTF disease",
    "Disease page test",
    "AOTF test for a list of genes for disease column",
    "Disease to search from home page",
    "disease page test alternatives",
    "GWAS study test page",
    "Mol Qtl study test page",
    "Credible Set Page with L2G coloc",
    "Credible set page with GWAS coloc",
    "Credible Set Page with QTL coloc",
    "Source (GitHub issue)",
]


# Empty mapping template for initialization
EMPTY_SCENARIO = ScenarioMapping(
    scenario_name="",
    source_url="",
)


# Re-export LLM models for convenience
from ot_miner.models.llm_models import ScenarioEntity

__all__ = [
    "IssueState",
    "GitHubLabel",
    "GitHubIssue",
    "ScenarioMapping",
    "ExtractionResult",
    "ScenarioEntity",
    "SHEET_HEADERS",
    "EMPTY_SCENARIO",
]
