"""
LLM-based entity extraction using LangChain with OpenTargets API integration.

Uses Claude API via LangChain to extract entities from GitHub issues with full context
(title, body, comments). The LLM has access to the OpenTargets GraphQL API to verify
and look up gene IDs, disease IDs, drug IDs, and other entities in real-time.
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
    LLM-based extractor with OpenTargets API integration.
    
    Uses Claude API via LangChain to extract entities from GitHub issues.
    Reads full issue context (title, body, comments) and can query the
    OpenTargets GraphQL API to verify and look up entity IDs in real-time.
    
    Examples:
    - "BRAF target page" → queries API → returns ENSG00000157764
    - "breast cancer" → queries API → returns EFO_0000305
    - "imatinib" → queries API → returns CHEMBL941
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
            
            # Bind OpenTargets MCP tools if available
            # The LLM can use these to look up page IDs, gene/disease mappings, etc.
            try:
                self.llm = self._bind_opentargets_tools(self.llm)
            except Exception as e:
                logger.warning(f"OpenTargets MCP tools not available: {e}")
                logger.info("LLM will work without external tools (using built-in knowledge only)")
            
            self.parser = JsonOutputParser(pydantic_object=ScenarioEntity)
        except ImportError as e:
            raise ImportError(
                "langchain-anthropic package not found. "
                "Install it with: pip install langchain-anthropic langchain-core"
            ) from e
    
    def _bind_opentargets_tools(self, llm):
        """
        Bind OpenTargets GraphQL API as a tool for the LLM.
        
        This allows the LLM to query the OpenTargets API directly to:
        - Verify gene/target IDs
        - Verify disease/phenotype IDs
        - Verify drug/compound IDs
        - Search for entities by name
        
        Args:
            llm: ChatAnthropic instance
        
        Returns:
            LLM with OpenTargets API tool bound
        """
        from langchain_core.tools import tool
        import requests
        
        @tool
        def query_opentargets_api(graphql_query: str) -> str:
            """
            Query the OpenTargets GraphQL API to look up or verify gene IDs, disease IDs, drug IDs, etc.
            
            Args:
                graphql_query: A valid GraphQL query string for the OpenTargets API.
                    Example: query { search(queryString:"BRAF", entityNames:["target"]) { hits { id name } } }
            
            Returns:
                JSON response from the API as a string
            """
            api_url = "https://api.platform.opentargets.org/api/v4/graphql"
            
            try:
                response = requests.post(
                    api_url,
                    json={"query": graphql_query},
                    headers={"Content-Type": "application/json"},
                    timeout=10,
                )
                response.raise_for_status()
                result = response.json()
                
                # Return compact JSON
                return json.dumps(result.get("data", result), indent=None)
            except Exception as e:
                return json.dumps({"error": str(e)})
        
        # Bind the tool to the LLM
        llm_with_tools = llm.bind_tools([query_opentargets_api])
        logger.info("✅ OpenTargets GraphQL API tool bound to LLM")
        
        return llm_with_tools
    
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
            
            # Format comments for LLM context
            comments_text = ""
            if issue.comments:
                comments_summary = []
                for comment in issue.comments[:10]:  # Limit to first 10 comments
                    comment_preview = comment.body[:300]  # First 300 chars per comment
                    comments_summary.append(f"[@{comment.user}]: {comment_preview}")
                comments_text = "\n".join(comments_summary)
            
            payload = {
                "issue_number": issue.number,
                "title": issue.title,
                "body": (issue.body or "")[:3000],  # Increased to 3000 for more context
                "comments": comments_text,
                "labels": [label.name for label in issue.labels],
                "source_url": issue.html_url,
            }
            payloads.append(payload)
        
        # Call LLM via LangChain with tool support
        user_message = f"Extract and map entities for these {len(issues)} GitHub issues.\n\n{json.dumps(payloads, indent=2)}"
        
        try:
            # Agent loop to handle tool calls
            messages = [
                ("system", LLM_SYSTEM_PROMPT),
                ("human", user_message),
            ]
            
            max_iterations = 10  # Prevent infinite loops
            for iteration in range(max_iterations):
                response = self.llm.invoke(messages)
                
                # Check if LLM wants to call tools
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    logger.debug(f"LLM making {len(response.tool_calls)} tool call(s)")
                    
                    # Add LLM response to messages (AIMessage object directly, not tuple)
                    messages.append(response)
                    
                    # Execute tool calls
                    from langchain_core.messages import ToolMessage
                    for tool_call in response.tool_calls:
                        tool_name = tool_call.get("name", "")
                        tool_args = tool_call.get("args", {})
                        tool_id = tool_call.get("id", "")
                        
                        logger.debug(f"Calling tool: {tool_name}")
                        
                        # Execute the tool (query_opentargets_api)
                        if tool_name == "query_opentargets_api":
                            import requests
                            api_url = "https://api.platform.opentargets.org/api/v4/graphql"
                            graphql_query = tool_args.get("graphql_query", "")
                            
                            try:
                                api_response = requests.post(
                                    api_url,
                                    json={"query": graphql_query},
                                    headers={"Content-Type": "application/json"},
                                    timeout=10,
                                )
                                api_response.raise_for_status()
                                result = api_response.json()
                                tool_result = json.dumps(result.get("data", result), indent=None)
                            except Exception as e:
                                tool_result = json.dumps({"error": str(e)})
                            
                            # Add tool result to messages
                            messages.append(ToolMessage(content=tool_result, tool_call_id=tool_id))
                    
                    # Continue loop to get LLM's next response
                    continue
                
                # No more tool calls, parse final response
                response_text = response.content
                break
            else:
                raise ValueError("LLM exceeded maximum tool call iterations")
            
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
        
        # Convert LLM results to ScenarioMappings
        results = []
        for i, llm_result in enumerate(llm_results):
            if i >= len(issues):
                break
            
            issue = issues[i]
            
            # Ensure llm_result is a dict
            if isinstance(llm_result, ScenarioEntity):
                llm_result = llm_result.model_dump()
            
            # Create mapping from LLM result (LLM is now the source of truth)
            mapping = ScenarioMapping(
                scenario_name=llm_result.get("scenario_name", f"gh#{issue.number}: {issue.title[:50]}"),
                source_url=llm_result.get("source_url", issue.html_url),
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
