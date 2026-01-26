import re
import sys
from typing import Dict

from rich import print

from constants import MAX_FIELD_LENGTH

# Valid CU field name pattern: letters, numbers, underscores only; must start with letter or underscore; max 64 chars
VALID_FIELD_NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]{0,63}$')
ALLOWED_CHARS = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_')


class FieldNameNormalizer:
    """
    A class to handle field name normalization and track mappings between 
    original and normalized names to ensure consistency between analyzer and labels.
    """
    
    def __init__(self):
        """Initialize the normalizer with empty mappings."""
        self._original_to_normalized: Dict[str, str] = {}
        self._normalized_to_original: Dict[str, str] = {}
    
    def clear(self):
        """Clear all stored mappings."""
        self._original_to_normalized.clear()
        self._normalized_to_original.clear()
    
    def get_mapping(self) -> Dict[str, str]:
        """
        Get the mapping from original field names to normalized field names.
        Returns:
            Dict[str, str]: A dictionary mapping original names to normalized names.
        """
        return self._original_to_normalized.copy()
    
    def get_reverse_mapping(self) -> Dict[str, str]:
        """
        Get the mapping from normalized field names to original field names.
        Returns:
            Dict[str, str]: A dictionary mapping normalized names to original names.
        """
        return self._normalized_to_original.copy()
    
    def is_valid_field_name(self, name: str) -> bool:
        """
        Check if a field name matches the valid pattern.
        
        Args:
            name (str): The field name to validate.
        Returns:
            bool: True if the name is valid, False otherwise.
        """
        if not name:
            return False
        return bool(VALID_FIELD_NAME_PATTERN.match(name))
    
    def normalize_field_name(self, original_name: str, context: str = "") -> str:
        """
        Normalize a field name to match the pattern ^[a-zA-Z_][a-zA-Z0-9_]{0,63}$.
        
        This method:
        1. Replaces invalid characters with underscores
        2. Handles duplicates by appending a counter
        3. Truncates to MAX_FIELD_LENGTH if needed
        4. Ensures the result is not empty after normalization
        
        Args:
            original_name (str): The original field name to normalize.
            context (str): Optional context for error messages (e.g., "table 'MyTable'").
        
        Returns:
            str: The normalized field name.
        
        Raises:
            SystemExit: If the normalized name would be empty or exceed MAX_FIELD_LENGTH.
        """
        # If already normalized for this name, return the cached result
        if original_name in self._original_to_normalized:
            return self._original_to_normalized[original_name]
        
        # Normalize the name (or keep if already valid)
        if self.is_valid_field_name(original_name):
            normalized = original_name
        else:
            normalized = self._normalize_chars(original_name)
        
        # Handle empty result after normalization
        if not normalized:
            context_msg = f" in {context}" if context else ""
            print(f"[red]Error: Field name '{original_name}'{context_msg} becomes empty after normalization. "
                  f"Field names must contain at least one letter, number, or underscore.[/red]")
            sys.exit(1)
        
        # Truncate if too long (leave room for potential counter suffix)
        if len(normalized) > MAX_FIELD_LENGTH:
            # Truncate to max length, but we may need to add a suffix for duplicates
            normalized = normalized[:MAX_FIELD_LENGTH]
        
        # Handle duplicates (even for already valid names that might collide)
        normalized = self._handle_duplicate(normalized, original_name)
        
        # Final length check after duplicate handling
        if len(normalized) > MAX_FIELD_LENGTH:
            context_msg = f" in {context}" if context else ""
            print(f"[red]Error: Normalized field name '{normalized}'{context_msg} exceeds the limit of {MAX_FIELD_LENGTH} characters. "
                  f"Original name: '{original_name}'[/red]")
            sys.exit(1)
        
        # Register the mapping
        self._register_mapping(original_name, normalized)
        
        return normalized
    
    def get_normalized_name(self, original_name: str) -> str:
        """
        Get the normalized name for an original field name.
        This should be called after normalize_field_name has been called for the field.
        
        Args:
            original_name (str): The original field name.
        
        Returns:
            str: The normalized field name, or the original if no mapping exists.
        """
        return self._original_to_normalized.get(original_name, original_name)
    
    def has_mapping(self, original_name: str) -> bool:
        """
        Check if a mapping exists for the given original name.
        
        Args:
            original_name (str): The original field name.
        
        Returns:
            bool: True if a mapping exists, False otherwise.
        """
        return original_name in self._original_to_normalized
    
    def _normalize_chars(self, name: str) -> str:
        """
        Replace invalid characters with underscores and clean up the result.
        
        Args:
            name (str): The name to normalize.
        
        Returns:
            str: The normalized name with only valid characters.
        """
        result = []
        prev_was_underscore = False
        
        for char in name:
            if char in ALLOWED_CHARS:
                prev_was_underscore = (char == '_')
                result.append(char)
            else:
                # Replace invalid char with underscore, avoid consecutive underscores
                if not prev_was_underscore:
                    result.append('_')
                    prev_was_underscore = True
        
        # Join and clean up leading/trailing underscores
        normalized = ''.join(result).strip('_')
        
        # Remove any remaining consecutive underscores
        while '__' in normalized:
            normalized = normalized.replace('__', '_')
        
        # Ensure name starts with letter or underscore (not a number)
        if normalized and normalized[0].isdigit():
            normalized = 'f_' + normalized
        
        return normalized
    
    def _handle_duplicate(self, normalized: str, original_name: str) -> str:
        """
        Handle duplicate normalized names by appending a counter.
        
        Args:
            normalized (str): The normalized name that might be a duplicate.
            original_name (str): The original name (for context).
        
        Returns:
            str: A unique normalized name.
        """
        if normalized not in self._normalized_to_original:
            return normalized
        
        # If the same original maps to this normalized name, it's fine
        if self._normalized_to_original.get(normalized) == original_name:
            return normalized
        
        # Find a unique name by appending a counter
        counter = 1
        base_name = normalized
        
        # Calculate max base length to leave room for counter suffix
        # Format: baseName_N where N can be up to 3 digits
        max_base_length = MAX_FIELD_LENGTH - 4  # "_" + up to 3 digits
        
        if len(base_name) > max_base_length:
            base_name = base_name[:max_base_length]
        
        while True:
            candidate = f"{base_name}_{counter}"
            if len(candidate) > MAX_FIELD_LENGTH:
                # Need to shorten base_name more
                max_base_length -= 1
                if max_base_length < 1:
                    print(f"[red]Error: Cannot create unique normalized name for '{original_name}'. "
                          f"Too many duplicates.[/red]")
                    sys.exit(1)
                base_name = normalized[:max_base_length]
                counter = 1
                continue
            
            if candidate not in self._normalized_to_original:
                print(f"[yellow]Warning: Field name '{original_name}' normalized to '{candidate}' "
                      f"(added suffix to avoid duplicate with '{self._normalized_to_original[normalized]}')[/yellow]")
                return candidate
            
            counter += 1
            if counter > 999:
                print(f"[red]Error: Cannot create unique normalized name for '{original_name}'. "
                      f"Too many duplicates (>999).[/red]")
                sys.exit(1)
    
    def _register_mapping(self, original: str, normalized: str) -> None:
        """
        Register a mapping between original and normalized names.
        
        Args:
            original (str): The original field name.
            normalized (str): The normalized field name.
        """
        self._original_to_normalized[original] = normalized
        self._normalized_to_original[normalized] = original
        
        if original != normalized:
            print(f"[yellow]Info: Field name '{original}' normalized to '{normalized}'[/yellow]")


def normalize_field_name_simple(name: str) -> str:
    """
    Simple normalization function without tracking (for one-off normalizations).
    Replaces invalid characters with underscores.
    
    Args:
        name (str): The field name to normalize.
    
    Returns:
        str: The normalized field name.
    
    Note:
        This function does NOT handle duplicates. Use FieldNameNormalizer class
        for full functionality including duplicate detection.
    """
    if not name:
        return name
    
    result = []
    prev_was_underscore = False
    
    for char in name:
        if char in ALLOWED_CHARS:
            prev_was_underscore = (char == '_')
            result.append(char)
        else:
            if not prev_was_underscore:
                result.append('_')
                prev_was_underscore = True
    
    normalized = ''.join(result).strip('_')
    
    while '__' in normalized:
        normalized = normalized.replace('__', '_')
    
    # Ensure name starts with letter or underscore (not a number)
    if normalized and normalized[0].isdigit():
        normalized = 'f_' + normalized
    
    return normalized


def is_valid_field_name(name: str) -> bool:
    """
    Check if a field name matches the valid CU pattern.
    
    Args:
        name (str): The field name to validate.
    
    Returns:
        bool: True if valid, False otherwise.
    """
    if not name:
        return False
    return bool(VALID_FIELD_NAME_PATTERN.match(name))
