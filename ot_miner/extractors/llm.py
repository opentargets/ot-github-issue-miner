"""
LLM-based entity enrichment and refinement using LangChain.

Pass 2 of the two-pass miner: uses Claude API via LangChain to understand context,
fill gaps that regex misses, and correct misclassifications.
"""

import json
import time
import logging
from typing import List, Optional

from ot_miner.models import GitHubIssue, ScenarioMapping, ExtractionResult, ScenarioEntity
from ot_miner.extractors.base import BaseExtractor
from ot_miner.utils import merge_extraction_fields
from ot_miner.config import Config
from ot_miner.prompts import LLM_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class LLMExtractor(BaseExtractor):
    """
    LLM-based extractor that enriches and refines regex extraction results.
    
    Uses Claude API via LangChain to understand context, fill gaps, and correct
    misclassifications that regex might miss (e.g., "BRAF target page"
    → ENSG00000157764, or correctly classifying variants).
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the LLM extractor with LangChain.
        
        Args:
            config: Application configuration with Anthropic API key
        
        Raises:
            ValueError: If no Anthropic API key is configured
            ImportError: If langchain or langchain-anthropic not installed
        """
        if config is None:
            config = Config.from_env()
        
        if not config.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable not set. "
                "LLM extraction requires valid Anthropic credentials."
            )
        
        self.config = config
        
        # Initialize LangChain ChatAnthropic (lazy import)
        try:
            from langchain_anthropic import ChatAnthropic
            from langchain_core.output_parsers import JsonOutputParser
            
            self.llm = ChatAnthropic(
                model=config.llm_model,
                api_key=config.anthropic_api_key,
                temperature=0.7,
            )
            self.parser = JsonOutputParser(pydantic_object=ScenarioEntity)
        except ImportError as e:
            raise ImportError(
                "langchain-anthropic package not found. "
                "Install it with: pip install langchain-anthropic langchain-core"
            ) from e
    
    def extract(self, issue: GitHubIssue) -> Optional[ScenarioMapping]:
        """
        Single issues cannot be extracted efficiently by LLM.
        This method is provided for interface compliance but should
        use extract_batch for better performance and cost efficiency.
        
        Args:
            issue: GitHub issue to extract from
        
        Returns:
            ScenarioMapping extracted by LLM
        """
        results = self.extract_batch([issue])
        return results[0].mapping if results else None
    
    def extract_batch(
        self,
        issues: List[GitHubIssue],
        regex_mappings: Optional[List[Optional[ScenarioMapping]]] = None,
    ) -> List[ExtractionResult]:
        """
        Extract and enrich entities from multiple GitHub issues.
        
        Processes issues in configurable batch sizes to manage API costs
        and respect rate limits.
        
        Args:
            issues: List of GitHub issues to process
            regex_mappings: Optional list of regex extraction results for comparison
        
        Returns:
            List of ExtractionResult objects with LLM enrichment
        """
        if not issues:
            return []
        
        logger.info(f"🤖 LLM enrichment pass on {len(issues)} issues "
                   f"in batches of {self.config.llm_batch_size}…")
        
        all_results: List[ExtractionResult] = []
        
        # Process in configurable batch sizes
        for batch_idx in range(0, len(issues), self.config.llm_batch_size):
            batch = issues[batch_idx:batch_idx + self.config.llm_batch_size]
            batch_regex = regex_mappings[batch_idx:batch_idx + self.config.llm_batch_size] if regex_mappings else None
            
            try:
                batch_results = self._process_batch(batch, batch_regex)
                all_results.extend(batch_results)
            except Exception as e:
                logger.error(f"LLM batch {batch_idx // self.config.llm_batch_size + 1} failed: {e}")
                # Fallback to regex results if available
                if batch_regex:
                    for mapping in batch_regex:
                        if mapping:
                            all_results.append(ExtractionResult(
                                mapping=mapping,
                                is_llm_enriched=False,
                                confidence=0.7,
                            ))
            
            # Rate limiting between batches
            processed = min(batch_idx + self.config.llm_batch_size, len(issues))
            print(f"\r   {processed}/{len(issues)} enriched…", end="", flush=True)
            time.sleep(self.config.llm_delay_ms / 1000)
        
        print()  # New line after progress
        logger.info(f"✅ LLM enrichment complete")
        return all_results
    
    def _process_batch(
        self,
        issues: List[GitHubIssue],
        regex_mappings: Optional[List[Optional[ScenarioMapping]]] = None,
    ) -> List[ExtractionResult]:
        """
        Process a single batch of issues through the LLM.
        
        Args:
            issues: Batch of issues to process
            regex_mappings: Optional regex results for reference
        
        Returns:
            List of ExtractionResult from LLM
        """
        # Build payload for LLM
        payloads = []
        for i, issue in enumerate(issues):
            regex_mapping = regex_mappings[i] if regex_mappings and i < len(regex_mappings) else None
            
            payload = {
                "issue_number": issue.number,
                "title": issue.title,
                "body": (issue.body or "")[:1500],  # Truncate to avoid huge prompts
                "labels": [label.name for label in issue.labels],
                "regex_extracted": {
                    "drug_id": regex_mapping.drug_id if regex_mapping else "",
                    "variant_id": regex_mapping.variant_id if regex_mapping else "",
                    "variant_pgx": regex_mapping.variant_pgx if regex_mapping else "",
                    "variant_molqtl": regex_mapping.variant_molqtl if regex_mapping else "",
                    "target_id": regex_mapping.target_id if regex_mapping else "",
                    "target_ids": regex_mapping.target_ids if regex_mapping else "",
                    "disease_id": regex_mapping.disease_id if regex_mapping else "",
                    "gwas_study": regex_mapping.gwas_study if regex_mapping else "",
                    "qtl_study": regex_mapping.qtl_study if regex_mapping else "",
                    "credible_set_l2g": regex_mapping.credible_set_l2g if regex_mapping else "",
                    "credible_set_gwas": regex_mapping.credible_set_gwas if regex_mapping else "",
                    "credible_set_qtl": regex_mapping.credible_set_qtl if regex_mapping else "",
                } if regex_mapping else {},
                "source_url": issue.html_url,
            }
            payloads.append(payload)
        
        # Call LLM via LangChain
        user_message = f"Extract and map entities for these {len(issues)} GitHub issues.\n\n{json.dumps(payloads, indent=2)}"
        
        try:
            response = self.llm.invoke([
                ("system", LLM_SYSTEM_PROMPT),
                ("human", user_message),
            ])
            response_text = response.content
            
            # Parse JSON response
            try:
                # Try to extract JSON from response
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0].strip()
                else:
                    json_str = response_text
                
                llm_results = json.loads(json_str)
            except (json.JSONDecodeError, IndexError) as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.debug(f"Response was: {response_text[:500]}")
                raise ValueError("LLM response was not valid JSON") from e
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise
        
        # Ensure llm_results is a list
        if not isinstance(llm_results, list):
            llm_results = [llm_results]
        
        # Merge LLM results with regex baseline
        results = []
        for i, llm_result in enumerate(llm_results):
            if i >= len(issues):
                break
            
            regex_mapping = regex_mappings[i] if regex_mappings and i < len(regex_mappings) else None
            
            # Ensure llm_result is a dict
            if isinstance(llm_result, ScenarioEntity):
                llm_result = llm_result.model_dump()
            
            # Build merged mapping
            if regex_mapping:
                mapping = ScenarioMapping(
                    scenario_name=regex_mapping.scenario_name,  # Keep formatted name
                    source_url=regex_mapping.source_url,
                    drug_id=merge_extraction_fields(llm_result.get("drug_id"), regex_mapping.drug_id),
                    variant_id=merge_extraction_fields(llm_result.get("variant_id"), regex_mapping.variant_id),
                    variant_pgx=merge_extraction_fields(llm_result.get("variant_pgx"), regex_mapping.variant_pgx),
                    variant_molqtl=merge_extraction_fields(llm_result.get("variant_molqtl"), regex_mapping.variant_molqtl),
                    target_id=merge_extraction_fields(llm_result.get("target_id"), regex_mapping.target_id),
                    target_ids=merge_extraction_fields(llm_result.get("target_ids"), regex_mapping.target_ids),
                    aotf_diseases=merge_extraction_fields(llm_result.get("aotf_diseases"), regex_mapping.aotf_diseases),
                    disease_id=merge_extraction_fields(llm_result.get("disease_id"), regex_mapping.disease_id),
                    aotf_genes=merge_extraction_fields(llm_result.get("aotf_genes"), regex_mapping.aotf_genes),
                    disease_search=merge_extraction_fields(llm_result.get("disease_search"), regex_mapping.disease_search),
                    disease_alt=merge_extraction_fields(llm_result.get("disease_alt"), regex_mapping.disease_alt),
                    gwas_study=merge_extraction_fields(llm_result.get("gwas_study"), regex_mapping.gwas_study),
                    qtl_study=merge_extraction_fields(llm_result.get("qtl_study"), regex_mapping.qtl_study),
                    credible_set_l2g=merge_extraction_fields(llm_result.get("credible_set_l2g"), regex_mapping.credible_set_l2g),
                    credible_set_gwas=merge_extraction_fields(llm_result.get("credible_set_gwas"), regex_mapping.credible_set_gwas),
                    credible_set_qtl=merge_extraction_fields(llm_result.get("credible_set_qtl"), regex_mapping.credible_set_qtl),
                )
            else:
                # Create mapping from LLM result alone
                mapping = ScenarioMapping(
                    scenario_name=llm_result.get("scenario_name", ""),
                    source_url=llm_result.get("source_url", ""),
                    drug_id=llm_result.get("drug_id", ""),
                    variant_id=llm_result.get("variant_id", ""),
                    variant_pgx=llm_result.get("variant_pgx", ""),
                    variant_molqtl=llm_result.get("variant_molqtl", ""),
                    target_id=llm_result.get("target_id", ""),
                    target_ids=llm_result.get("target_ids", ""),
                    aotf_diseases=llm_result.get("aotf_diseases", ""),
                    disease_id=llm_result.get("disease_id", ""),
                    aotf_genes=llm_result.get("aotf_genes", ""),
                    disease_search=llm_result.get("disease_search", ""),
                    disease_alt=llm_result.get("disease_alt", ""),
                    gwas_study=llm_result.get("gwas_study", ""),
                    qtl_study=llm_result.get("qtl_study", ""),
                    credible_set_l2g=llm_result.get("credible_set_l2g", ""),
                    credible_set_gwas=llm_result.get("credible_set_gwas", ""),
                    credible_set_qtl=llm_result.get("credible_set_qtl", ""),
                )
            
            results.append(ExtractionResult(
                mapping=mapping,
                is_llm_enriched=True,
                confidence=0.9,  # LLM has higher confidence
            ))
        
        return results
