"""
Regex-based entity extraction from GitHub issues.

Pass 1 of the two-pass miner: fast, free entity extraction using
compiled regex patterns. Catches explicit IDs in issue text.
"""

import logging
from typing import List, Optional

from ot_miner.models import GitHubIssue, ScenarioMapping, ExtractionResult
from ot_miner.utils import (
    find_all, extract_gene_symbols, REGEX_PATTERNS,
    GENE_TO_ENSEMBL, DISEASE_TO_ONTOLOGY
)
from ot_miner.loaders import IssueFilter
from ot_miner.extractors.base import BaseExtractor

logger = logging.getLogger(__name__)


class RegexExtractor(BaseExtractor):
    """
    Extracts entities from GitHub issues using precompiled regex patterns.
    
    This is the fast, free first pass that catches explicit identifiers
    like CHEMBL IDs, Ensembl gene IDs, EFO disease IDs, etc.
    
    Can be extended by configuring REGEX_PATTERNS or overriding extraction logic.
    """
    
    def __init__(self, filter_issues: bool = True):
        """
        Initialize the regex extractor.
        
        Args:
            filter_issues: If True, only extracts from issues deemed relevant
        """
        self.filter_issues = filter_issues
        self.issue_filter = IssueFilter()
    
    def extract(self, issue: GitHubIssue) -> Optional[ScenarioMapping]:
        """
        Extract entities from a single GitHub issue.
        
        Args:
            issue: GitHub issue to process
        
        Returns:
            ScenarioMapping if entities found, None otherwise
        """
        # Pre-filtering step
        if self.filter_issues and not self.issue_filter.is_relevant(issue):
            return None
        
        text = f"{issue.title}\n{issue.body or ''}"
        
        # Extract all entities using regex patterns
        chembl = find_all(text, REGEX_PATTERNS["chembl"])
        variants = find_all(text, REGEX_PATTERNS["variant"])
        ensg = find_all(text, REGEX_PATTERNS["ensg"])
        efos = find_all(text, REGEX_PATTERNS["efo"])
        mondos = find_all(text, REGEX_PATTERNS["mondo"])
        disease_ids = efos + mondos
        gcst = find_all(text, REGEX_PATTERNS["gcst"])
        qtl = find_all(text, REGEX_PATTERNS["ukb_ppp"])
        credible_sets = find_all(text, REGEX_PATTERNS["credible_set"])
        genes = extract_gene_symbols(text)
        diseases = find_all(text, REGEX_PATTERNS["disease"])
        
        # Check if any entities were found
        has_entities = any([
            chembl, variants, ensg, disease_ids, gcst, qtl, credible_sets
        ])
        
        # Check for bug-related labels
        is_bug_label = any(
            label.name in ["bug", "frontend", "platform", "aotf", "api"]
            for label in issue.labels
        )
        
        if not has_entities and not is_bug_label:
            return None
        
        # Build mapping from extracted entities
        mapping = ScenarioMapping(
            scenario_name=f"gh#{issue.number}: {issue.title[:80]}",
            source_url=issue.html_url,
            drug_id=chembl[0] if chembl else "",
            variant_id=variants[0] if variants else "",
            variant_pgx=variants[1] if len(variants) > 1 else (variants[0] if variants else ""),
            variant_molqtl=variants[0] if variants else "",
            target_id=ensg[0] if ensg else "",
            target_ids=", ".join(ensg[:3]) if ensg else "",
            aotf_diseases=", ".join(diseases[:3]) if diseases else "",
            disease_id=disease_ids[0] if disease_ids else "",
            aotf_genes=", ".join(genes[:5]) if genes else "",
            disease_search=diseases[0].lower() if diseases else "",
            disease_alt=", ".join(disease_ids[1:3]) if len(disease_ids) > 1 else "",
            gwas_study=gcst[0] if gcst else "",
            qtl_study=qtl[0] if qtl else "",
            credible_set_l2g=credible_sets[0] if credible_sets else "",
            credible_set_gwas=credible_sets[1] if len(credible_sets) > 1 else "",
            credible_set_qtl=credible_sets[2] if len(credible_sets) > 2 else "",
        )
        
        return mapping
    
    def extract_batch(self, issues: List[GitHubIssue]) -> List[ExtractionResult]:
        """
        Extract entities from multiple GitHub issues.
        
        Args:
            issues: List of GitHub issues to process
        
        Returns:
            List of ExtractionResult objects
        """
        results = []
        
        for issue in issues:
            mapping = self.extract(issue)
            if mapping:
                results.append(ExtractionResult(
                    mapping=mapping,
                    is_llm_enriched=False,
                    confidence=0.7,  # Regex has moderate confidence
                ))
        
        return results
