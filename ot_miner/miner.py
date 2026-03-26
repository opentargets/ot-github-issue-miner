"""
Main application logic and orchestration.

This module ties together all components: GitHub loader, extractors,
and output writers into a cohesive mining pipeline.
"""

import logging
from typing import List, Optional

from ot_miner.config import Config
from ot_miner.models import GitHubIssue, ScenarioMapping
from ot_miner.loaders import GitHubLoader, IssueFilter
from ot_miner.extractors import (
    RegexExtractor,
    LLMExtractor,
)
from ot_miner.writers import create_default_writers, MultiWriter

logger = logging.getLogger(__name__)


class ScenarioMiner:
    """
    Main orchestration class for the two-pass GitHub issue scenario miner.
    
    Combines GitHub issue loading, multi-pass extraction (regex + LLM),
    and output generation into a single cohesive pipeline.
    
    Architecture:
        - GitHubLoader: Fetches issues from GitHub API with pagination
        - RegexExtractor: Fast first pass using compiled regex patterns
        - LLMExtractor: Context-aware enrichment using Claude API
        - Writers: Output to CSV, JSON, and extensible formats
    """
    
    def __init__(
        self,
        config: Optional[Config] = None,
        writers: Optional[MultiWriter] = None,
    ):
        """
        Initialize the scenario miner.
        
        Args:
            config: Application configuration (loaded from env if not provided)
            writers: Output writers (default CSV + JSON if not provided)
        """
        self.config = config or Config.from_env()
        self.writers = writers or create_default_writers()
        self.github_loader = GitHubLoader(self.config)
        self.issue_filter = IssueFilter()
    
    def run(self) -> List[ScenarioMapping]:
        """
        Execute the complete mining pipeline.
        
        Performs:
        1. Fetch all GitHub issues
        2. Pass 1: Regex extraction (fast, free)
        3. Pass 2: LLM enrichment (context-aware, optional)
        4. Write outputs to configured formats
        
        Returns:
            List of extracted ScenarioMapping objects
        """
        mode = "regex + LLM" if self.config.use_llm else "regex only"
        logger.info(f"🚀 Open Targets scenario miner  [mode: {mode}]\n")
        
        # Step 1: Fetch issues
        all_issues = self.github_loader.fetch_all_issues()
        
        # Step 2: Regex extraction (Pass 1)
        regex_mappings = self._pass_1_regex(all_issues)
        
        # Step 3: Conditional LLM enrichment (Pass 2)
        if self.config.use_llm:
            final_mappings = self._pass_2_llm(all_issues, regex_mappings)
        else:
            final_mappings = [m for m in regex_mappings if m is not None]
        
        # Step 3.5: Filter out issues without any page IDs
        final_mappings = self._filter_empty_mappings(final_mappings)
        
        # Step 4: Write outputs
        self._write_outputs(final_mappings)
        
        # Step 5: Summary statistics
        self._print_summary(final_mappings)
        
        return final_mappings
    
    def _pass_1_regex(self, issues: List[GitHubIssue]) -> List[Optional[ScenarioMapping]]:
        """
        Execute Pass 1: Fast regex-based extraction.
        
        Args:
            issues: List of GitHub issues to process
        
        Returns:
            List of ScenarioMapping or None if not extracted
        """
        logger.info("🔎 Pass 1: regex extraction…")
        
        extractor = RegexExtractor(filter_issues=True)
        mappings = []
        
        for issue in issues:
            mapping = extractor.extract(issue)
            mappings.append(mapping)
        
        hits = sum(1 for m in mappings if m is not None)
        logger.info(f"   {hits} relevant issues out of {len(issues)} total\n")
        
        return mappings
    
    def _pass_2_llm(
        self,
        issues: List[GitHubIssue],
        regex_mappings: List[Optional[ScenarioMapping]],
    ) -> List[ScenarioMapping]:
        """
        Execute Pass 2: LLM-based enrichment and refinement.
        
        Args:
            issues: List of GitHub issues
            regex_mappings: Results from Pass 1 for comparison
        
        Returns:
            List of enriched ScenarioMapping objects
        """
        try:
            extractor = LLMExtractor(self.config)
            
            # Filter to only issues with regex results
            relevant_issues = [
                (issue, regex_mappings[i])
                for i, issue in enumerate(issues)
                if i < len(regex_mappings) and regex_mappings[i] is not None
            ]
            
            if not relevant_issues:
                logger.info("ℹ  No issues to enrich – skipping LLM pass.\n")
                return []
            
            issues_to_enrich = [issue for issue, _ in relevant_issues]
            regex_to_enrich = [mapping for _, mapping in relevant_issues]
            
            # Process through LLM
            results = extractor.extract_batch(issues_to_enrich, regex_to_enrich)
            enriched = [r.mapping for r in results]
            
            return enriched
        
        except ImportError as e:
            logger.error(f"⚠  LLM extraction skipped: {e}")
            return [m for m in regex_mappings if m is not None]
        except ValueError as e:
            logger.error(f"⚠  LLM extraction skipped: {e}")
            return [m for m in regex_mappings if m is not None]
    
    def _filter_empty_mappings(self, mappings: List[ScenarioMapping]) -> List[ScenarioMapping]:
        """
        Filter out scenarios that don't have any page IDs.
        
        A scenario is considered valid if it has at least one of:
        - drug_id (CHEMBL)
        - variant_id (main variant)
        - variant_pgx (PGx variant)
        - variant_molqtl (molQTL variant)
        - target_id (single Ensembl ID)
        - target_ids (multiple Ensembl IDs)
        - disease_id (EFO/MONDO)
        - gwas_study
        - qtl_study
        - credible_set_l2g
        - credible_set_gwas
        - credible_set_qtl
        
        Args:
            mappings: List of ScenarioMapping objects
        
        Returns:
            Filtered list with only scenarios that have at least one page ID
        """
        filtered = []
        for mapping in mappings:
            has_page_id = any([
                mapping.drug_id.strip(),
                mapping.variant_id.strip(),
                mapping.variant_pgx.strip(),
                mapping.variant_molqtl.strip(),
                mapping.target_id.strip(),
                mapping.target_ids.strip(),
                mapping.disease_id.strip(),
                mapping.gwas_study.strip(),
                mapping.qtl_study.strip(),
                mapping.credible_set_l2g.strip(),
                mapping.credible_set_gwas.strip(),
                mapping.credible_set_qtl.strip(),
            ])
            if has_page_id:
                filtered.append(mapping)
        
        excluded = len(mappings) - len(filtered)
        if excluded > 0:
            logger.info(f"🗑️  Excluded {excluded} issue(s) without any page IDs\n")
        
        return filtered
    
    def _write_outputs(self, mappings: List[ScenarioMapping]) -> None:
        """
        Write extraction results to configured output formats.
        
        Args:
            mappings: List of ScenarioMapping objects to write
        """
        output_paths = {
            "csv": self.config.csv_path,
            "json": self.config.json_path,
        }
        self.writers.write(mappings, output_paths)
    
    def _print_summary(self, mappings: List[ScenarioMapping]) -> None:
        """
        Print extraction statistics and completion message.
        
        Args:
            mappings: List of extracted ScenarioMapping objects
        """
        def count_with(field: str) -> int:
            return sum(1 for m in mappings if getattr(m, field, "").strip())
        
        print("\n── Extraction summary ──────────────────────────────")
        print(f"  Total rows             : {len(mappings)}")
        print(f"  With drug (CHEMBL)     : {count_with('drug_id')}")
        print(f"  With variant           : {count_with('variant_id')}")
        print(f"  With PGx variant       : {count_with('variant_pgx')}")
        print(f"  With molQTL variant    : {count_with('variant_molqtl')}")
        print(f"  With target (ENSG)     : {count_with('target_id')}")
        print(f"  With disease EFO/MONDO : {count_with('disease_id')}")
        print(f"  With GWAS study        : {count_with('gwas_study')}")
        print(f"  With QTL study         : {count_with('qtl_study')}")
        print(f"  With credible set      : {count_with('credible_set_l2g')}")
        print(f"  With AOTF genes        : {count_with('aotf_genes')}")
        print("────────────────────────────────────────────────────")
        print("\n📋 To import into Google Sheets:")
        print("   File → Import → Upload mined-scenarios.csv")
        print('   Import location: "Append to current sheet"')
        print("   Separator type: Comma → Import data\n")
