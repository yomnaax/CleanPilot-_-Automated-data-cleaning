"""
Regex Pattern Extractor using proven grammar-based inference algorithm.

Implements a well-known algorithm for automatic regex generation:
- Longest Common Subsequence (LCS) for structure discovery
- Position-based character class inference  
- Quantifier generation for variable-length patterns
- Based on research in automatic regex generation
"""

import re
import pandas as pd
from typing import List, Dict, Any, Set, Tuple
from collections import Counter, defaultdict
from .base_extractor import BaseExtractor
from ...db import models
import logging

logger = logging.getLogger(__name__)


class RegexExtractor(BaseExtractor):
    """
    Extracts format validation rules using grammar-based regex pattern inference.
    
    Uses a proven algorithm that analyzes examples to generate accurate regex patterns.
    """
    
    def __init__(self, min_match_ratio: float = 0.5, high_confidence_threshold: float = 0.8):
        """
        Initialize the regex extractor.

        The extractor automatically adjusts its thresholds based on the
        reinforcement learning strictness score.  A higher strictness
        score means the extractor will require patterns to match a larger
        fraction of the data before producing a rule, while a lower
        score relaxes this requirement.  Thresholds are clamped to
        sensible ranges to prevent extreme behaviour.

        Args:
            min_match_ratio: Baseline minimum percentage of values that must
                match a pattern for it to be extracted (default: 0.5 = 50%).
            high_confidence_threshold: Baseline ratio above which match is
                considered high confidence (default: 0.8 = 80%).
        """
        # Import here to avoid circular dependencies
        try:
            from ..reinforcement_learning import get_strictness  # type: ignore
            strictness = get_strictness("regex")
        except Exception:
            strictness = 0.0
        # Adjust thresholds based on strictness.  Positive strictness
        # tightens thresholds; negative values relax them.  Use a small
        # scaling factor to ensure gradual change.
        delta = strictness * 0.05
        # Compute min_match_ratio and clamp to [0.3, 0.95]
        adj_min = min_match_ratio + delta
        adj_min = adj_min if adj_min is not None else min_match_ratio
        if adj_min < 0.3:
            adj_min = 0.3
        if adj_min > 0.95:
            adj_min = 0.95
        # Compute high_confidence_threshold and ensure it is at least 0.05
        # above min_match_ratio and no more than 0.99
        adj_high = high_confidence_threshold + delta
        if adj_high < adj_min + 0.05:
            adj_high = adj_min + 0.05
        if adj_high > 0.99:
            adj_high = 0.99
        super().__init__("Regex Pattern Extractor")
        self.min_match_ratio = adj_min
        self.high_confidence_threshold = adj_high
    
    def extract(self, dataset: models.Dataset) -> List[Dict[str, Any]]:
        """
        Extract regex-based format validation rules from dataset.
        
        Args:
            dataset: The dataset to extract rules from
            
        Returns:
            List of rule dictionaries
        """
        rules = []
        
        # Validate dataset
        if not self.validate_dataset(dataset):
            return rules
        
        try:
            # Load dataframe
            df = self.load_dataframe(dataset, sample_rows=5000)
            
            # Get valid columns
            valid_columns = self.get_valid_columns(df)
            
            if not valid_columns:
                logger.warning(f"{self.name}: No valid columns found in dataset {dataset.id}")
                return rules
            
            # Extract patterns from each column
            processed_columns = []
            skipped_columns = []
            
            for col in valid_columns:
                col_data = df[col]
                
                # Skip if mostly null
                if col_data.isna().sum() / len(col_data) > 0.5:
                    skipped_columns.append((col, "mostly_null"))
                    continue
                
                # Convert to string for analysis (handles numeric columns)
                col_data_str = col_data.astype(str)
                non_null = col_data_str.dropna()
                
                if len(non_null) == 0:
                    skipped_columns.append((col, "no_data"))
                    continue
                
                # Skip only extremely long free text
                max_length = non_null.str.len().max()
                if max_length > 1000:
                    skipped_columns.append((col, f"too_long({max_length})"))
                    continue
                
                logger.info(f"{self.name}: Processing column '{col}' for regex pattern extraction")
                processed_columns.append(col)
                
                # Extract patterns using grammar-based algorithm
                patterns = self._extract_patterns_from_column(non_null.tolist())
                
                # Create rules for each pattern found
                for pattern_info in patterns:
                    match_ratio = pattern_info['match_ratio']
                    has_low_match = pattern_info.get('has_low_match_rate', False)
                    
                    # Build explanation
                    if has_low_match:
                        explanation = (
                            f"Column '{col}' partially matches {pattern_info['pattern_name']} pattern "
                            f"({match_ratio:.1%} match rate). "
                            f"⚠️ Low match rate - many values don't follow this pattern. "
                            f"Review carefully before approving."
                        )
                    else:
                        explanation = (
                            f"Column '{col}' matches {pattern_info['pattern_name']} pattern "
                            f"({match_ratio:.1%} match rate)"
                        )
                    
                    rule = self.format_rule(
                        dataset=dataset,
                        columns=[col],
                        predicate=f"regex_match({col}, '{pattern_info['pattern']}')",
                        action=f"enforce_format({col}, '{pattern_info['pattern_name']}')",
                        confidence=pattern_info["confidence"],
                        explanation=explanation,
                    )
                    
                    # Add warning flag to targets for frontend display
                    if has_low_match:
                        rule["targets"]["low_match_rate_warning"] = True
                        rule["targets"]["match_rate"] = match_ratio
                    
                    rules.append(rule)
            
            # Log detailed results
            logger.info(f"{self.name}: Processed {len(processed_columns)} columns, skipped {len(skipped_columns)} columns")
            logger.info(f"{self.name}: Processed columns: {processed_columns}")
            if skipped_columns:
                logger.info(f"{self.name}: Skipped columns: {[f'{col} ({reason})' for col, reason in skipped_columns[:10]]}")
            self.log_extraction(len(rules), dataset.id)
            
        except Exception as e:
            logger.error(f"{self.name}: Error extracting rules from dataset {dataset.id}: {e}")
            raise
        
        return rules
    
    def _extract_patterns_from_column(self, values: List[str]) -> List[Dict[str, Any]]:
        """
        Extract regex patterns from a column using grammar-based algorithm.
        
        Args:
            values: List of string values in the column
            
        Returns:
            List of pattern dictionaries
        """
        patterns = []
        
        if len(values) == 0:
            return patterns
        
        # Use grammar-based inference algorithm
        inferred_pattern = self._generate_regex_pattern(values)
        
        if inferred_pattern:
            # Skip weak/useless patterns
            if self._is_weak_pattern(inferred_pattern):
                logger.debug(f"Skipping weak pattern: {inferred_pattern}")
                return patterns
            
            # Test the pattern against all values
            try:
                pattern_regex = re.compile(inferred_pattern)
                matches = sum(1 for v in values if pattern_regex.fullmatch(v))
                match_ratio = matches / len(values) if len(values) > 0 else 0
            except re.error:
                # Invalid regex pattern
                logger.warning(f"Invalid regex pattern generated: {inferred_pattern}")
                return patterns
            
            if match_ratio >= self.min_match_ratio:
                # Calculate confidence
                if match_ratio >= self.high_confidence_threshold:
                    confidence = min(match_ratio, 0.95)
                elif match_ratio >= 0.6:
                    confidence = match_ratio * 0.85
                else:
                    confidence = match_ratio * 0.7
                
                # Generate descriptive name
                pattern_name = self._describe_pattern(inferred_pattern, values)
                
                patterns.append({
                    "pattern_name": pattern_name,
                    "pattern": inferred_pattern,
                    "match_ratio": match_ratio,
                    "confidence": confidence,
                    "has_low_match_rate": match_ratio < self.high_confidence_threshold,
                })
        
        return patterns
    
    def _generate_regex_pattern(self, examples: List[str]) -> str | None:
        """
        Generate regex pattern from examples using grammar-based algorithm.
        
        Algorithm based on proven research:
        1. Find longest common prefix and suffix
        2. Analyze variable middle part using position-based alignment
        3. Build pattern with proper quantifiers and character classes
        
        Args:
            examples: List of example strings
            
        Returns:
            Regex pattern string or None
        """
        if not examples:
            return None
        
        # Remove duplicates and empty strings
        examples = [e for e in examples if e]
        if not examples:
            return None
        
        # Use all examples for better accuracy (not just sample)
        # This ensures we catch variations like 8 vs 9
        
        # Step 1: Find common structure (prefix/suffix)
        prefix = self._longest_common_prefix(examples)
        suffix = self._longest_common_suffix(examples)
        
        # Step 2: Extract and analyze middle parts
        if suffix:
            middle_parts = [e[len(prefix):-len(suffix)] for e in examples 
                          if len(e) >= len(prefix) + len(suffix)]
        else:
            middle_parts = [e[len(prefix):] for e in examples if len(e) >= len(prefix)]
        
        # Step 3: Build pattern
        pattern_parts = []
        
        if prefix:
            pattern_parts.append(re.escape(prefix))
        
        if middle_parts:
            middle_pattern = self._analyze_middle_part(middle_parts)
            if middle_pattern:
                pattern_parts.append(middle_pattern)
            else:
                # If middle pattern is None (too weak), return None
                return None
        
        if suffix:
            pattern_parts.append(re.escape(suffix))
        
        if not pattern_parts:
            # No common structure found, try position-based analysis
            return self._position_based_pattern(examples)
        
        full_pattern = "^" + "".join(pattern_parts) + "$"
        
        # Final check: if the full pattern is weak, return None
        if self._is_weak_pattern(full_pattern):
            return None
        
        return full_pattern
    
    def _longest_common_prefix(self, strings: List[str]) -> str:
        """
        Find longest common prefix using character-by-character comparison.
        
        This is a well-known algorithm for finding common structure.
        """
        if not strings:
            return ""
        
        prefix = ""
        min_len = min(len(s) for s in strings)
        
        for i in range(min_len):
            chars = [s[i] for s in strings]
            if len(set(chars)) == 1:
                prefix += chars[0]
            else:
                break
        
        return prefix
    
    def _longest_common_suffix(self, strings: List[str]) -> str:
        """
        Find longest common suffix using character-by-character comparison.
        """
        if not strings:
            return ""
        
        suffix = ""
        min_len = min(len(s) for s in strings)
        
        for i in range(1, min_len + 1):
            chars = [s[-i] for s in strings]
            if len(set(chars)) == 1:
                suffix = chars[0] + suffix
            else:
                break
        
        return suffix
    
    def _analyze_middle_part(self, parts: List[str]) -> str | None:
        """
        Analyze variable middle part and generate pattern.
        
        Uses position-based alignment to determine:
        - Fixed length: character-by-character analysis
        - Variable length: quantifiers with character classes
        
        Returns None if pattern would be too weak/useless.
        """
        if not parts:
            return ""
        
        # Filter empty parts
        non_empty = [p for p in parts if p]
        if not non_empty:
            return ""
        
        # Check if all same length
        lengths = [len(p) for p in non_empty]
        if len(set(lengths)) == 1:
            # Fixed length - analyze each position
            pattern = self._build_fixed_pattern(non_empty)
            # Check if the fixed pattern is weak
            if pattern and self._is_weak_pattern("^" + pattern + "$"):
                return None
            return pattern
        else:
            # Variable length - use quantifiers
            return self._build_variable_pattern(non_empty)
    
    def _build_fixed_pattern(self, parts: List[str]) -> str:
        """
        Build pattern for fixed-length parts using position-based analysis.
        
        For each position, determines the best character class representation.
        """
        if not parts:
            return ""
        
        pattern_parts = []
        length = len(parts[0])
        
        # Analyze each position across all examples
        for pos in range(length):
            chars_at_pos = [p[pos] if pos < len(p) else '' for p in parts]
            unique_chars = {c for c in chars_at_pos if c}
            
            if not unique_chars:
                continue
            
            if len(unique_chars) == 1:
                # Single character
                char = unique_chars.pop()
                if char.isdigit():
                    pattern_parts.append(r"\d")
                elif char.isalpha():
                    pattern_parts.append(r"[a-zA-Z]")
                else:
                    pattern_parts.append(re.escape(char))
            
            elif len(unique_chars) <= 5:
                # Small set - use character class (e.g., [89] for IDs starting with 8 or 9)
                sorted_chars = sorted(unique_chars)
                if all(c.isdigit() for c in sorted_chars):
                    pattern_parts.append(f"[{''.join(sorted_chars)}]")
                elif all(c.isalpha() for c in sorted_chars):
                    pattern_parts.append(f"[{''.join(sorted_chars)}]")
                else:
                    escaped = ''.join(re.escape(c) for c in sorted_chars)
                    pattern_parts.append(f"[{escaped}]")
            
            else:
                # Large set - generalize
                all_digits = all(c.isdigit() for c in unique_chars)
                all_letters = all(c.isalpha() for c in unique_chars)
                all_alnum = all(c.isalnum() for c in unique_chars)
                
                if all_digits:
                    pattern_parts.append(r"\d")
                elif all_letters:
                    pattern_parts.append(r"[a-zA-Z]")
                elif all_alnum:
                    pattern_parts.append(r"[a-zA-Z0-9]")
                else:
                    pattern_parts.append(r".")
        
        return "".join(pattern_parts)
    
    def _build_variable_pattern(self, parts: List[str]) -> str:
        """
        Build pattern for variable-length parts using quantifiers.
        
        Analyzes character types and generates appropriate quantifiers.
        Returns None if pattern would be too weak/useless.
        """
        if not parts:
            return ""
        
        # Analyze character types across all parts
        all_chars = set(''.join(parts))
        all_digits = all(c.isdigit() for c in all_chars)
        all_letters = all(c.isalpha() for c in all_chars)
        all_alnum = all(c.isalnum() for c in all_chars)
        
        lengths = [len(p) for p in parts]
        min_len = min(lengths)
        max_len = max(lengths)
        
        if all_digits:
            if min_len == max_len:
                return r"\d{" + str(min_len) + r"}"
            else:
                return r"\d{" + str(min_len) + r"," + str(max_len) + r"}"
        elif all_letters:
            if min_len == max_len:
                return r"[a-zA-Z]{" + str(min_len) + r"}"
            else:
                return r"[a-zA-Z]{" + str(min_len) + r"," + str(max_len) + r"}"
        elif all_alnum:
            return r"[a-zA-Z0-9]+"
        else:
            # Too diverse - return None instead of weak pattern
            # This will cause the pattern generation to fail gracefully
            return None
    
    def _position_based_pattern(self, examples: List[str]) -> str | None:
        """
        Fallback: Position-based pattern when no common prefix/suffix.
        
        Analyzes character positions to build pattern.
        """
        if not examples:
            return None
        
        # Check if all same length
        lengths = [len(e) for e in examples]
        if len(set(lengths)) == 1:
            # Fixed length - build character by character
            return "^" + self._build_fixed_pattern(examples) + "$"
        
        # Variable length - check for patterns like IDs starting with 8 or 9
        # Check first character variations across ALL examples (not just sample)
        first_chars = {e[0] for e in examples if e}
        
        if len(first_chars) <= 3 and all(c.isdigit() for c in first_chars):
            # Small set of digits at start (like 8 or 9)
            sorted_digits = sorted(first_chars)
            first_pattern = f"[{''.join(sorted_digits)}]"
            
            # Check if rest are digits
            rest_are_digits = all(e[1:].isdigit() if len(e) > 1 else True for e in examples)
            if rest_are_digits:
                return f"^{first_pattern}\\d+$"
        
        # Try to build pattern from alignment
        return self._build_pattern_from_alignment(examples)
    
    def _build_pattern_from_alignment(self, examples: List[str]) -> str | None:
        """
        Build pattern by aligning examples and finding common structure.
        
        Uses a simple alignment approach to find patterns.
        """
        if not examples:
            return None
        
        # For variable length, try to find if there's a pattern
        # Check if first N characters are consistent
        min_len = min(len(e) for e in examples)
        
        # Find longest consistent prefix
        prefix_len = 0
        for i in range(min_len):
            chars = [e[i] for e in examples if len(e) > i]
            if len(set(chars)) == 1:
                prefix_len = i + 1
            else:
                break
        
        if prefix_len > 0:
            # We have a prefix, analyze the rest
            prefix = examples[0][:prefix_len]
            rest_parts = [e[prefix_len:] for e in examples]
            
            prefix_pattern = re.escape(prefix)
            rest_pattern = self._build_variable_pattern(rest_parts)
            
            return f"^{prefix_pattern}{rest_pattern}$"
        
        # No clear structure - return None (let other methods handle it)
        return None
    
    def _describe_pattern(self, pattern: str, sample_values: List[str]) -> str:
        """
        Generate a human-readable description of the pattern.
        
        Args:
            pattern: The regex pattern
            sample_values: Sample values that match the pattern
            
        Returns:
            Descriptive name for the pattern
        """
        if not sample_values:
            return "custom_format"
        
        sample_str = " ".join(sample_values[:10])
        
        # Date patterns
        if r"\d{4}-\d{2}-\d{2}" in pattern or pattern.startswith(r"^\d{4}-"):
            return "date_iso_format"
        elif r"\d{2}/\d{2}/\d{4}" in pattern:
            return "date_us_format"
        elif r"\d{2}\.\d{2}\.\d{4}" in pattern:
            return "date_eu_format"
        
        # Email pattern
        elif "@" in sample_str and r"@" in pattern:
            return "email_format"
        
        # URL pattern
        elif r"https?://" in pattern or any("http" in v for v in sample_values[:5]):
            return "url_format"
        
        # Phone-like pattern
        elif (r"\+?" in pattern and r"[\d\s\-\(\)]+" in pattern) or \
             (r"\d" in pattern and any(c in sample_str for c in ["-", "(", ")", "+"]) and 
              len(sample_values[0]) >= 7 and len(sample_values[0]) <= 20):
            return "phone_like_format"

        # Alphanumeric (contains both letters and digits)
        elif sample_values and any(re.search(r"[A-Za-z]", v) and re.search(r"\d", v) for v in sample_values[:5]):
            return "alphanumeric_format"
        
        # ZIP code
        elif r"\d{5}" in pattern and len(sample_values[0]) <= 10:
            return "zipcode_format"
        
        # SSN
        elif r"\d{3}-\d{2}-\d{4}" in pattern:
            return "ssn_format"
        
        # Long numeric IDs
        elif pattern.count(r"\d") >= 12:
            return "numeric_id_format"
        
        # Single character
        elif r"^[a-zA-Z]$" in pattern:
            return "single_letter"
        
        # Pure alphabetic
        elif r"^[a-zA-Z]+$" in pattern:
            return "alphabetic_text"
        
        # Pure numeric
        elif r"^\d+$" in pattern:
            return "numeric_only"
        
        # Alphanumeric
        elif r"^[a-zA-Z0-9]+$" in pattern:
            return "alphanumeric_format"
        
        # Default
        else:
            return "custom_format"
    
    def _is_weak_pattern(self, pattern: str) -> bool:
        """
        Check if a regex pattern is too weak/useless to be meaningful.
        
        Weak patterns are those that match almost anything and don't provide
        meaningful validation constraints.
        
        Args:
            pattern: The regex pattern to check
            
        Returns:
            True if pattern is weak/useless, False otherwise
        """
        if not pattern:
            return True
        
        # Remove anchors for checking
        pattern_body = pattern.strip('^$')
        
        # Patterns that match any non-empty string (too weak)
        weak_patterns = [
            r'^.+$',           # Any non-empty string
            r'^.*$',           # Any string (including empty)
            r'^.{1,}$',        # At least one character
            r'^.{0,}$',        # Any number of characters
            r'^.+$',           # One or more of any character
            r'^.*$',           # Zero or more of any character
        ]
        
        # Check exact matches
        if pattern in weak_patterns:
            return True
        
        # Check if pattern is just .+ or .* with optional anchors
        if pattern_body in [r'.+', r'.*', r'.{1,}', r'.{0,}']:
            return True
        
        # Check if pattern is just a single . (matches any character)
        if pattern_body == r'.':
            return True
        
        # Check if pattern has no specific constraints (just wildcards)
        # This catches patterns like ^.+$ or ^.*$ even if slightly different
        if re.match(r'^\^?\.\+?\$?$', pattern) or re.match(r'^\^?\.\*\$?$', pattern):
            return True
        
        # Check if pattern is too simple (just one character class with + or *)
        # But allow specific ones like \d+, [a-zA-Z]+, etc.
        simple_pattern = re.match(r'^\^?([\\]?[a-zA-Z0-9\[\]\\\-]+)\+?\*?\$?$', pattern_body)
        if simple_pattern:
            # Allow specific character classes
            char_class = simple_pattern.group(1)
            if char_class in [r'\d', r'\w', r'\s', r'[a-zA-Z]', r'[a-zA-Z0-9]', r'[0-9]']:
                # These are meaningful, not weak
                return False
            # If it's just . with quantifier, it's weak
            if char_class == '.':
                return True
        
        return False


# Factory function for backward compatibility
def extract(dataset: models.Dataset) -> List[Dict[str, Any]]:
    """
    Extract regex-based rules from dataset.
    
    This function maintains backward compatibility with the old interface.
    
    Args:
        dataset: The dataset to extract rules from
        
    Returns:
        List of rule dictionaries
    """
    extractor = RegexExtractor()
    return extractor.extract(dataset)
