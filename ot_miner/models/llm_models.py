"""Models for LLM-based extraction."""

from pydantic import BaseModel, Field


class ScenarioEntity(BaseModel):
    """Schema for extracted scenario entity."""
    scenario_name: str = Field(default="")
    drug_id: str = Field(default="")
    variant_id: str = Field(default="")
    variant_pgx: str = Field(default="")
    variant_molqtl: str = Field(default="")
    target_id: str = Field(default="")
    target_ids: str = Field(default="")
    aotf_diseases: str = Field(default="")
    disease_id: str = Field(default="")
    aotf_genes: str = Field(default="")
    disease_search: str = Field(default="")
    disease_alt: str = Field(default="")
    gwas_study: str = Field(default="")
    qtl_study: str = Field(default="")
    credible_set_l2g: str = Field(default="")
    credible_set_gwas: str = Field(default="")
    credible_set_qtl: str = Field(default="")
    source_url: str = Field(default="")
