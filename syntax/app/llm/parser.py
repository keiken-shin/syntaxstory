import re
from typing import Any, Dict

import yaml
from pydantic import BaseModel


class YamlParsingError(Exception):
    """Exception raised when YAML text cannot be extracted or parsed."""
    def __init__(self, message: str, raw_text: str):
        super().__init__(message)
        self.raw_text = raw_text


def extract_yaml_from_text(text: str) -> str:
    """
    Extracts YAML content from a string that might contain markdown formatting.
    It looks for ```yaml ... ``` or ``` ... ``` blocks. If none are found, 
    it assumes the whole text might be YAML.
    """
    text = text.strip()
    
    # Look for ```yaml markers first
    pattern = re.compile(r"```(?:yaml|yml)?\s*\n(.*?)\n```", re.IGNORECASE | re.DOTALL)
    match = pattern.search(text)
    
    if match:
        return match.group(1).strip()
        
    # If no markdown fences are found, try returning the raw text as a fallback
    return text


def parse_yaml_safely(text: str) -> Dict[str, Any]:
    """
    Extracts and parses a YAML string into a Python dictionary.
    Raises YamlParsingError if the result is invalid or parsing fails.
    """
    if not text:
        raise YamlParsingError("Provided text is empty.", text)

    extracted_yaml = extract_yaml_from_text(text)
    
    if not extracted_yaml:
        raise YamlParsingError("Failed to extract YAML content from text.", text)
        
    try:
        # Using safe_load to prevent arbitrary code execution
        parsed = yaml.safe_load(extracted_yaml)
        
        if not isinstance(parsed, dict):
            raise YamlParsingError(
                f"YAML root must be a dictionary/object, got {type(parsed).__name__}.", 
                text
            )
            
        return parsed
    except yaml.YAMLError as e:
        raise YamlParsingError(f"YAML parser error: {str(e)}", text)
