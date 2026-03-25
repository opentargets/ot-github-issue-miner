"""
Output writers for scenario data in CSV and JSON formats.

Provides simple writers for standard output formats.
"""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from ot_miner.models import ScenarioMapping, SHEET_HEADERS
from ot_miner.utils import write_csv as write_csv_safe

logger = logging.getLogger(__name__)


class BaseWriter(ABC):
    """
    Abstract base class for output writers.
    
    Allows easy extension with new output formats while maintaining
    a consistent interface.
    """
    
    @abstractmethod
    def write(self, mappings: List[ScenarioMapping], path: Path) -> None:
        """
        Write scenario mappings to the specified format.
        
        Args:
            mappings: List of ScenarioMapping objects to write
            path: Output file path
        """
        pass


class CSVWriter(BaseWriter):
    """Writes scenario mappings to CSV format for Google Sheets import."""
    
    def write(self, mappings: List[ScenarioMapping], path: Path) -> None:
        """
        Write mappings to CSV file.
        
        The CSV format matches Google Sheets columns exactly, making it
        easy to import with File → Import → Upload.
        
        Args:
            mappings: List of ScenarioMapping objects
            path: Output CSV file path
        """
        rows = [m.to_row() for m in mappings]
        write_csv_safe(path, SHEET_HEADERS, rows)
        logger.info(f"📄 CSV  → {path}")


class JSONWriter(BaseWriter):
    """Writes scenario mappings to JSON format for programmatic access."""
    
    def __init__(self, pretty: bool = True, indent: int = 2):
        """
        Initialize JSON writer.
        
        Args:
            pretty: Whether to pretty-print JSON output
            indent: Number of spaces for indentation if pretty=True
        """
        self.pretty = pretty
        self.indent = indent if pretty else None
    
    def write(self, mappings: List[ScenarioMapping], path: Path) -> None:
        """
        Write mappings to JSON file.
        
        Args:
            mappings: List of ScenarioMapping objects
            path: Output JSON file path
        """
        # Ensure output directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = [m.to_dict() for m in mappings]
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=self.indent)
        
        logger.info(f"📦 JSON → {path}")


class MultiWriter:
    """
    Writes to CSV and JSON formats simultaneously.
    """
    
    def __init__(self):
        """Initialize the multi-writer with CSV and JSON writers."""
        self.csv_writer = CSVWriter()
        self.json_writer = JSONWriter()
    
    def write(self, mappings: List[ScenarioMapping], paths: dict[str, Path]) -> None:
        """
        Write mappings to CSV and JSON formats.
        
        Args:
            mappings: List of ScenarioMapping objects
            paths: Mapping of format names to output paths (keys: "csv", "json")
        """
        if "csv" in paths:
            self.csv_writer.write(mappings, paths["csv"])
        if "json" in paths:
            self.json_writer.write(mappings, paths["json"])


def create_default_writers() -> MultiWriter:
    """
    Create a MultiWriter for CSV and JSON output.
    
    Returns:
        MultiWriter configured for CSV and JSON formats
    """
    return MultiWriter()
