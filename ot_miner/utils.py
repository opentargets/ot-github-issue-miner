"""
Utility functions and patterns for the scenario miner.
"""

import re
import csv
from io import StringIO
from typing import Set, List, Optional
from pathlib import Path


# Compiled regex patterns for entity extraction
REGEX_PATTERNS = {
    "chembl": re.compile(r"\bCHEMBL\d{4,7}\b", re.IGNORECASE),
    "ensg": re.compile(r"\bENSG\d{11}\b", re.IGNORECASE),
    "efo": re.compile(r"\bEFO_\d{7}\b", re.IGNORECASE),
    "mondo": re.compile(r"\bMONDO_\d{7}\b", re.IGNORECASE),
    "variant": re.compile(r"\b(?:chr)?\d{1,2}_\d{5,9}_[ACGTN*]+_[ACGTN*]+\b", re.IGNORECASE),
    "gcst": re.compile(r"\bGCST\d{5,9}\b", re.IGNORECASE),
    "ukb_ppp": re.compile(r"\bUKB_PPP_[A-Z0-9_]+", re.IGNORECASE),
    "credible_set": re.compile(r"\b[0-9a-f]{32}\b", re.IGNORECASE),
    "disease": re.compile(
        r"\b(cancer|carcinoma|melanoma|diabetes|asthma|arthritis|alzheimer|"
        r"parkinson|epilepsy|obesity|hypertension|schizophrenia|depression|"
        r"myocardial infarction|breast cancer|lung cancer|coronary|fibrosis|"
        r"colitis|lupus|psoriasis|sclerosis)\b",
        re.IGNORECASE
    ),
}

# Gene symbols to filter out (abbreviations, acronyms, stop words)
GENE_STOPWORDS: Set[str] = {
    "API", "URL", "UI", "UX", "PR", "CI", "CD", "DB", "ID", "OK", "NA",
    "JS", "TS", "CSS", "HTML", "JSON", "SQL", "GCP", "AWS", "SNP", "QTL",
    "GTF", "VCF", "TSV", "CSV", "GWAS", "AOTF", "PPP", "PTS", "L2G", "UKB",
    "EUR", "OID", "BUG", "FIX", "NEW", "ADD", "GET", "SET", "THE", "FOR",
    "NOT", "AND", "HAS", "ARE", "WAS", "WITH", "FROM", "THIS", "THAT",
    "HAVE", "BEEN", "THEY", "WHEN", "WILL", "DOES",
}

# Known gene name to Ensembl ID mappings
GENE_TO_ENSEMBL = {
    "BRAF": "ENSG00000157764",
    "BRCA2": "ENSG00000139618",
    "TP53": "ENSG00000141510",
    "IL6": "ENSG00000136244",
    "PCSK9": "ENSG00000169174",
    "LPA": "ENSG00000198670",
    "APOE": "ENSG00000130203",
    "ADRB1": "ENSG00000043591",
    "EGFR": "ENSG00000146648",
    "TNF": "ENSG00000232810",
    "VEGFA": "ENSG00000112715",
    "KRAS": "ENSG00000133703",
    "PTEN": "ENSG00000171862",
    "MYC": "ENSG00000136997",
}

# Known disease name to EFO/MONDO mappings
DISEASE_TO_ONTOLOGY = {
    "breast cancer": "EFO_0000305",
    "lung cancer": "EFO_0001071",
    "melanoma": "EFO_0000389",
    "diabetes": "EFO_0000400",
    "asthma": "EFO_0000270",
    "myocardial infarction": "EFO_0000612",
    "colorectal cancer": "EFO_0005842",
    "rheumatoid arthritis": "EFO_0000685",
    "alzheimer disease": "EFO_0000249",
    "parkinson disease": "EFO_0002508",
}

# Known drug name to CHEMBL mappings
DRUG_TO_CHEMBL = {
    "imatinib": "CHEMBL941",
    "trastuzumab": "CHEMBL1201585",
    "vemurafenib": "CHEMBL1229517",
    "pembrolizumab": "CHEMBL3137343",
    "rituximab": "CHEMBL1201576",
}


def find_all(text: str, pattern: re.Pattern) -> List[str]:
    """Extract unique non-empty matches from text."""
    matches = pattern.findall(text)
    return sorted(list(set(m.strip() for m in matches if m.strip())))


def extract_gene_symbols(text: str) -> List[str]:
    """Extract potential gene symbols from text."""
    # Find all 2-10 char uppercase words
    candidates = re.findall(r"\b([A-Z][A-Z0-9]{1,9})\b", text)
    
    genes = []
    for gene in candidates:
        # Filter out stopwords and known prefixes
        if (len(gene) >= 2 and len(gene) <= 10 and
            gene not in GENE_STOPWORDS and
            not any(gene.startswith(prefix) for prefix in ["ENSG", "CHEMBL", "EFO", "MONDO", "GCST", "UKB"])):
            genes.append(gene)
    
    return sorted(list(set(genes)))


def csv_escape(value: str) -> str:
    """Escape value for CSV output."""
    if "," in value or '"' in value or "\n" in value:
        return f'"{value.replace(chr(34), chr(34) + chr(34))}"'
    return value


def write_csv(filename: Path, headers: List[str], rows: List[List[str]]) -> None:
    """Write CSV file safely."""
    # Ensure output directory exists
    filename.parent.mkdir(parents=True, exist_ok=True)
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    
    with open(filename, "w", encoding="utf-8", newline="") as f:
        f.write(output.getvalue())


def merge_extraction_fields(llm_value: Optional[str], regex_value: str) -> str:
    """Merge LLM and regex extraction results, preferring non-empty LLM value."""
    if llm_value and llm_value.strip():
        return llm_value.strip()
    return regex_value
