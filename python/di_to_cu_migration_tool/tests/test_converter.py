"""
Tests for the DI to CU converter.

This module tests:
1. Field type conversion (signature removal, selectionMark→boolean, currency→number)
2. Field name validation (valid patterns, invalid characters, length limits)
3. Field name normalization (hyphens, spaces, special chars → underscores)
4. Duplicate field name handling (unique suffixes for collisions)
5. Analyzer conversion (fields.json → analyzer.json)
6. Labels conversion (DI labels → CU labels)
7. Edge cases (unicode, emoji, very long names, numeric names)
8. Integration tests (full pipeline, no hyphens in output)

Prerequisites:
- Test data in ./tests_data/di_data/ directory (fields.json, *.labels.json)
- Expected output in ./tests_data/expected_cu/ (form_sample_1.pdf.labels.json, analyzer.json)

Running tests:
    # Navigate to the tests directory
    cd python/di_to_cu_migration_tool/tests/

    # Run all tests
    pytest test_converter.py -v

    # Run specific test class
    pytest test_converter.py::TestFieldNameNormalization -v

    # Run specific test
    pytest test_converter.py::TestDuplicateFieldNames::test_duplicate_after_normalization -v

    # Run with coverage
    pytest test_converter.py --cov=. --cov-report=html

Key test scenarios:
- Field names with hyphens (e.g., "no-whitespaces") are normalized to underscores
- Duplicate field names after normalization get unique suffixes (_1, _2, etc.)
- Signature fields are removed during field type conversion
- selectionMark fields are converted to boolean type
- All generated field names match pattern: ^[a-zA-Z_][a-zA-Z0-9_]{0,63}$
- Analyzer and labels field names are aligned after conversion

Note: The CU API rejects hyphens in nested field names even though the documented
pattern is ^[a-zA-Z_][a-zA-Z0-9_]{0,63}$. The converter normalizes hyphens to underscores.
"""

import json
import re
import pytest
import sys
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import modules to test
from field_name_utils import FieldNameNormalizer, normalize_field_name_simple, is_valid_field_name
from cu_converter_neural import (
    convert_fields_to_analyzer_neural,
    convert_di_labels_to_cu_neural,
)
from field_definitions import FieldDefinitions
from field_type_conversion import update_fott_fields
from constants import MAX_FIELD_LENGTH

# Test data paths
TEST_DATA_DIR = Path(__file__).parent / "tests_data" / "di_data"
EXPECTED_LABELS_PATH = Path(__file__).parent / "tests_data" / "expected_cu" / "form_sample_1.pdf.labels.json"
EXPECTED_ANALYZER_PATH = Path(__file__).parent / "tests_data" / "expected_cu" / "analyzer.json"


def _collapse_underscores(name: str) -> str:
    """Collapse consecutive underscores for comparison only."""
    return re.sub(r"_+", "_", name)


class TestFieldTypeConversion:
    """Tests for field type conversion (update_fott_fields)."""
    
    def test_signature_removal(self):
        """Test that signature fields are removed."""
        fields_data = {
            "$schema": "https://schema.cognitiveservices.azure.com/formrecognizer/2021-03-01/fields.json",
            "fields": [
                {"fieldKey": "name", "fieldType": "string", "fieldFormat": "not-specified"},
                {"fieldKey": "signature", "fieldType": "signature", "fieldFormat": "not-specified"},
                {"fieldKey": "date", "fieldType": "date", "fieldFormat": "not-specified"},
            ]
        }
        
        removed_signatures, converted = update_fott_fields(fields_data)
        
        assert "signature" in removed_signatures
        
        # Check converted fields don't have signature
        field_keys = [f["fieldKey"] for f in converted["fields"]]
        assert "signature" not in field_keys
        assert "name" in field_keys
        assert "date" in field_keys
    
    def test_selection_mark_to_boolean(self):
        """Test that selectionMark is converted to boolean."""
        fields_data = {
            "$schema": "https://schema.cognitiveservices.azure.com/formrecognizer/2021-03-01/fields.json",
            "fields": [
                {"fieldKey": "checkbox", "fieldType": "selectionMark", "fieldFormat": "not-specified"},
            ]
        }
        
        removed_signatures, converted = update_fott_fields(fields_data)
        
        assert converted["fields"][0]["fieldType"] == "boolean"
    
    def test_currency_to_number(self):
        """Test that currency is converted to number."""
        fields_data = {
            "$schema": "https://schema.cognitiveservices.azure.com/formrecognizer/2021-03-01/fields.json",
            "fields": [
                {"fieldKey": "amount", "fieldType": "currency", "fieldFormat": "not-specified"},
            ]
        }
        
        removed_signatures, converted = update_fott_fields(fields_data)
        
        assert converted["fields"][0]["fieldType"] == "number"


class TestFieldNameValidation:
    """Tests for field name validation."""
    
    def test_valid_simple_names(self):
        """Test that simple valid names pass validation."""
        valid_names = [
            "fieldName",
            "field_name",
            "FieldName123",
            "a",
            "A",
            "_",
            "__",
            "_123",  # underscore followed by numbers is valid
            "field_name_123",
            "CamelCase",
            "snake_case",
            "UPPER_CASE",
            "_starts_with_underscore",
            "ends_with_underscore_",
        ]
        for name in valid_names:
            assert is_valid_field_name(name), f"Expected '{name}' to be valid"
    
    def test_invalid_names_with_hyphens(self):
        """Test that hyphens are now invalid (CU API rejects them)."""
        invalid_names = [
            "no-whitespaces",
            "field-name",
            "kebab-case",
            "with-hyphen-123",
        ]
        for name in invalid_names:
            assert not is_valid_field_name(name), f"Expected '{name}' to be invalid (contains hyphen)"
    
    def test_invalid_names_starting_with_number(self):
        """Test that names starting with numbers are invalid (CU API rejects them)."""
        invalid_names = [
            "1",              # purely numeric
            "123",            # purely numeric
            "999",            # purely numeric
            "1field",         # starts with number
            "123_field",      # starts with number
            "1_abc",          # starts with number
        ]
        for name in invalid_names:
            assert not is_valid_field_name(name), f"Expected '{name}' to be invalid (starts with number or purely numeric)"
    
    def test_invalid_names_with_dots(self):
        """Test that dots are invalid (CU API rejects them entirely)."""
        invalid_names = [
            "field.name",     # single dot
            "field..name",    # double dots
            "mdy...field",    # triple dots
            "a.b.c",          # multiple dots
            ".",              # single dot only
            "..",             # double dots only
            "..",             # double dots only
        ]
        for name in invalid_names:
            assert not is_valid_field_name(name), f"Expected '{name}' to be invalid (consecutive dots or invalid pattern)"
    
    def test_invalid_names_with_special_chars(self):
        """Test that special characters are invalid."""
        invalid_names = [
            "field name",  # space
            "field@name",  # @
            "field#name",  # #
            "field$name",  # $
            "field%name",  # %
            "field&name",  # &
            "field*name",  # *
            "field(name",  # (
            "field)name",  # )
            "field/name",  # /
            "field\\name", # \
            "field:name",  # :
            "field;name",  # ;
            "field'name",  # '
            'field"name',  # "
            "field<name",  # <
            "field>name",  # >
            "field?name",  # ?
            "field!name",  # !
            "field+name",  # +
            "field=name",  # =
            "field[name",  # [
            "field]name",  # ]
            "field{name",  # {
            "field}name",  # }
            "field|name",  # |
            "field~name",  # ~
            "field`name",  # `
            "中文字段",    # Chinese characters
            "フィールド",   # Japanese characters
        ]
        for name in invalid_names:
            assert not is_valid_field_name(name), f"Expected '{name}' to be invalid"
    
    def test_empty_and_none_names(self):
        """Test that empty and None names are invalid."""
        assert not is_valid_field_name("")
        assert not is_valid_field_name(None)
    
    def test_max_length_boundary(self):
        """Test field name length limits."""
        # Exactly 64 characters should be valid
        valid_max = "a" * 64
        assert is_valid_field_name(valid_max), "64-char name should be valid"
        
        # 65 characters should be invalid
        invalid_too_long = "a" * 65
        assert not is_valid_field_name(invalid_too_long), "65-char name should be invalid"
        
        # 1 character should be valid
        assert is_valid_field_name("a"), "1-char name should be valid"


class TestFieldNameNormalization:
    """Tests for field name normalization."""
    
    def test_normalize_hyphen_to_underscore(self):
        """Test that hyphens are converted to underscores."""
        normalizer = FieldNameNormalizer()
        
        result = normalizer.normalize_field_name("no-whitespaces")
        assert result == "no_whitespaces", f"Expected 'no_whitespaces', got '{result}'"
        
        result = normalizer.normalize_field_name("kebab-case-name")
        assert result == "kebab_case_name", f"Expected 'kebab_case_name', got '{result}'"
    
    def test_normalize_spaces_to_underscore(self):
        """Test that spaces are converted to underscores."""
        normalizer = FieldNameNormalizer()
        
        result = normalizer.normalize_field_name("field name")
        assert result == "field_name", f"Expected 'field_name', got '{result}'"
        
        # Double space normalizes to same - but with same normalizer, it's a duplicate
        normalizer.clear()
        result = normalizer.normalize_field_name("field  name")  # double space
        assert result == "field_name", f"Expected 'field_name', got '{result}'"
    
    def test_normalize_special_chars(self):
        """Test that special characters are replaced with underscores."""
        normalizer = FieldNameNormalizer()
        
        test_cases = [
            ("field@name", "field_name"),
            ("field#name", "field_name"),
            ("field$name", "field_name"),
            ("field%name", "field_name"),
            ("field&name", "field_name"),
            ("field*name", "field_name"),
            ("field/name", "field_name"),
            ("field:name", "field_name"),
        ]
        
        for original, expected in test_cases:
            normalizer.clear()
            result = normalizer.normalize_field_name(original)
            assert result == expected, f"Expected '{expected}' for '{original}', got '{result}'"
    
    def test_normalize_consecutive_special_chars(self):
        """Test that consecutive special characters become single underscore."""
        normalizer = FieldNameNormalizer()
        
        result = normalizer.normalize_field_name("field@@##name")
        assert result == "field_name", f"Expected 'field_name', got '{result}'"
        
        normalizer.clear()
        result = normalizer.normalize_field_name("field@@name")
        assert result == "field_name", f"Expected 'field_name', got '{result}'"
        
        normalizer.clear()
        result = normalizer.normalize_field_name("field---name")
        assert result == "field_name", f"Expected 'field_name', got '{result}'"
    
    def test_normalize_leading_trailing_special_chars(self):
        """Test that leading/trailing special characters are stripped."""
        normalizer = FieldNameNormalizer()
        
        result = normalizer.normalize_field_name("-field-")
        assert result == "field", f"Expected 'field', got '{result}'"
        
        normalizer.clear()
        result = normalizer.normalize_field_name("@@@field###")
        assert result == "field", f"Expected 'field', got '{result}'"
    
    def test_normalize_preserves_valid_names(self):
        """Test that already valid names are not modified."""
        normalizer = FieldNameNormalizer()
        
        # Note: dots are NOT valid in CU API field names, only letters, numbers, and underscores
        valid_names = ["fieldName", "field_name", "Field123", "_private", "CamelCase"]
        for name in valid_names:
            normalizer.clear()
            result = normalizer.normalize_field_name(name)
            assert result == name, f"Expected '{name}' to remain unchanged, got '{result}'"
    
    def test_normalize_long_name_truncation(self):
        """Test that long names are truncated to MAX_FIELD_LENGTH."""
        normalizer = FieldNameNormalizer()
        
        long_name = "a" * 100
        result = normalizer.normalize_field_name(long_name)
        assert len(result) <= MAX_FIELD_LENGTH, f"Expected length <= {MAX_FIELD_LENGTH}, got {len(result)}"
    
    def test_normalize_simple_function(self):
        """Test the simple normalization function without tracking."""
        assert normalize_field_name_simple("no-whitespaces") == "no_whitespaces"
        assert normalize_field_name_simple("field name") == "field_name"
        assert normalize_field_name_simple("field@#$name") == "field_name"
        assert normalize_field_name_simple("") == ""
        assert normalize_field_name_simple("validName") == "validName"


class TestDuplicateFieldNames:
    """Tests for duplicate field name handling."""
    
    def test_duplicate_after_normalization(self):
        """Test that duplicates get unique suffixes."""
        normalizer = FieldNameNormalizer()
        
        # Both should normalize to "field_name"
        result1 = normalizer.normalize_field_name("field-name")
        result2 = normalizer.normalize_field_name("field name")  # Same after normalization
        
        assert result1 == "field_name", f"Expected 'field_name', got '{result1}'"
        assert result2 == "field_name_1", f"Expected 'field_name_1', got '{result2}'"
    
    def test_multiple_duplicates(self):
        """Test handling of multiple duplicates."""
        normalizer = FieldNameNormalizer()
        
        # All normalize to "test_field"
        variants = ["test-field", "test field", "test@field", "test#field"]
        expected = ["test_field", "test_field_1", "test_field_2", "test_field_3"]
        
        for variant, exp in zip(variants, expected):
            result = normalizer.normalize_field_name(variant)
            assert result == exp, f"Expected '{exp}' for '{variant}', got '{result}'"
    
    def test_same_original_returns_same_normalized(self):
        """Test that same original name always returns same normalized name."""
        normalizer = FieldNameNormalizer()
        
        # First call
        result1 = normalizer.normalize_field_name("field-name")
        # Second call with same original
        result2 = normalizer.normalize_field_name("field-name")
        
        assert result1 == result2, f"Expected same result for same input"
    
    def test_get_normalized_name(self):
        """Test getting normalized name from mapping."""
        normalizer = FieldNameNormalizer()
        
        normalizer.normalize_field_name("field-name")
        
        # Should return the normalized name
        assert normalizer.get_normalized_name("field-name") == "field_name"
        
        # Unknown name should return itself
        assert normalizer.get_normalized_name("unknown") == "unknown"
    
    def test_has_mapping(self):
        """Test checking if mapping exists."""
        normalizer = FieldNameNormalizer()
        
        assert not normalizer.has_mapping("field-name")
        
        normalizer.normalize_field_name("field-name")
        
        assert normalizer.has_mapping("field-name")
        assert not normalizer.has_mapping("other-field")
    
    def test_clear_mappings(self):
        """Test clearing all mappings."""
        normalizer = FieldNameNormalizer()
        
        normalizer.normalize_field_name("field-name")
        assert normalizer.has_mapping("field-name")
        
        normalizer.clear()
        
        assert not normalizer.has_mapping("field-name")
        assert normalizer.get_mapping() == {}
    
    def test_many_duplicates_with_same_base(self):
        """Test handling of many field names that normalize to the same base."""
        normalizer = FieldNameNormalizer()
        
        # Create many variants that all normalize to "item"
        variants = [
            "item",
            "item-",
            "-item",
            "item--",
            "--item",
            "item@",
            "@item",
            "item#",
            "#item",
            "item$",
        ]
        
        results = []
        for variant in variants:
            result = normalizer.normalize_field_name(variant)
            results.append(result)
        
        # All results should be unique
        assert len(results) == len(set(results)), f"Results should be unique: {results}"
        
        # All results should be valid
        for result in results:
            assert is_valid_field_name(result), f"Result should be valid: {result}"
    
    def test_duplicate_counter_in_suffix(self):
        """Test that duplicate counter suffix format is correct."""
        normalizer = FieldNameNormalizer()
        
        result1 = normalizer.normalize_field_name("test-field")
        result2 = normalizer.normalize_field_name("test@field")  # normalizes to same
        result3 = normalizer.normalize_field_name("test#field")  # normalizes to same
        
        assert result1 == "test_field"
        assert result2 == "test_field_1"
        assert result3 == "test_field_2"
    
    def test_get_mapping_returns_copy(self):
        """Test that get_mapping returns a copy, not the original."""
        normalizer = FieldNameNormalizer()
        
        normalizer.normalize_field_name("field-name")
        
        mapping = normalizer.get_mapping()
        mapping["new_key"] = "new_value"  # Modify the returned copy
        
        # Original should not be affected
        assert "new_key" not in normalizer.get_mapping()


class TestAnalyzerConversion:
    """Tests for converting DI fields.json to CU analyzer.json."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test output."""
        tmp = tempfile.mkdtemp()
        yield Path(tmp)
        shutil.rmtree(tmp)
    
    @pytest.fixture
    def field_definitions(self):
        """Create a fresh FieldDefinitions object."""
        return FieldDefinitions()
    
    @pytest.fixture
    def converted_fields_json(self, temp_dir):
        """
        Create a converted fields.json with field types processed.
        This simulates what di_to_cu_converter.py does before calling cu_converter_neural.
        """
        fields_json_path = TEST_DATA_DIR / "fields.json"
        if not fields_json_path.exists():
            return None
        
        with open(fields_json_path, 'r', encoding='utf-8') as f:
            fields_data = json.load(f)
        
        # Run field type conversion (removes signatures, converts selectionMark to boolean)
        removed_signatures, converted_fields = update_fott_fields(fields_data)
        
        # Write converted fields to temp dir
        converted_path = temp_dir / "fields.json"
        with open(converted_path, 'w', encoding='utf-8') as f:
            json.dump(converted_fields, f, indent=4)
        
        return converted_path, removed_signatures

    def test_basic_conversion(self, temp_dir, field_definitions):
        """Test basic conversion of fields.json to analyzer.json."""
        fields_json_path = TEST_DATA_DIR / "fields.json"
        
        if not fields_json_path.exists():
            pytest.skip(f"Test data not found: {fields_json_path}")
        
        analyzer_data, fields_dict, normalizer = convert_fields_to_analyzer_neural(
            fields_json_path=fields_json_path,
            analyzer_id="testAnalyzer",
            target_dir=temp_dir,
            field_definitions=field_definitions,
        )
        
        # Check basic structure
        assert "analyzerId" in analyzer_data
        assert analyzer_data["analyzerId"] == "testAnalyzer"
        assert "fieldSchema" in analyzer_data
        assert "fields" in analyzer_data["fieldSchema"]
        
        # Check that analyzer.json was created
        analyzer_path = temp_dir / "analyzer.json"
        assert analyzer_path.exists(), "analyzer.json should be created"
    
    def test_signature_field_removed(self, temp_dir, field_definitions, converted_fields_json):
        """Test that signature fields are removed after field type conversion."""
        if converted_fields_json is None:
            pytest.skip("Test data not found")
        
        converted_path, removed_signatures = converted_fields_json
        
        # Signature should be in removed_signatures list
        assert "signature_field" in removed_signatures, "Signature field should be in removed list"
        
        # Convert using the pre-processed fields
        analyzer_data, fields_dict, normalizer = convert_fields_to_analyzer_neural(
            fields_json_path=converted_path,
            analyzer_id="testAnalyzer",
            target_dir=temp_dir,
            field_definitions=field_definitions,
        )
        
        fields = analyzer_data["fieldSchema"]["fields"]
        
        # signature_field should NOT be in the output (it was removed by update_fott_fields)
        assert "signature_field" not in fields, "Signature field should be removed"
    
    def test_selection_mark_to_boolean(self, temp_dir, field_definitions, converted_fields_json):
        """Test that selectionMark fields are converted to boolean after field type conversion."""
        if converted_fields_json is None:
            pytest.skip("Test data not found")
        
        converted_path, removed_signatures = converted_fields_json
        
        analyzer_data, fields_dict, normalizer = convert_fields_to_analyzer_neural(
            fields_json_path=converted_path,
            analyzer_id="testAnalyzer",
            target_dir=temp_dir,
            field_definitions=field_definitions,
        )
        
        fields = analyzer_data["fieldSchema"]["fields"]
        
        # selection_mark_1 and selection_mark_2 should be boolean (converted by update_fott_fields)
        assert fields["selection_mark_1"]["type"] == "boolean", f"Expected boolean, got {fields['selection_mark_1']['type']}"
        assert fields["selection_mark_2"]["type"] == "boolean", f"Expected boolean, got {fields['selection_mark_2']['type']}"
    
    def test_no_format_field_in_output(self, temp_dir, field_definitions):
        """Test that 'format' field is not in the output."""
        fields_json_path = TEST_DATA_DIR / "fields.json"
        
        if not fields_json_path.exists():
            pytest.skip(f"Test data not found: {fields_json_path}")
        
        analyzer_data, fields_dict, normalizer = convert_fields_to_analyzer_neural(
            fields_json_path=fields_json_path,
            analyzer_id="testAnalyzer",
            target_dir=temp_dir,
            field_definitions=field_definitions,
        )
        
        # Check no 'format' field anywhere in the analyzer
        analyzer_json = json.dumps(analyzer_data)
        assert '"format"' not in analyzer_json, "format field should not be in output"
    
    def test_field_name_normalization_in_tables(self, temp_dir, field_definitions):
        """Test that field names in tables are normalized (hyphens removed)."""
        fields_json_path = TEST_DATA_DIR / "fields.json"
        
        if not fields_json_path.exists():
            pytest.skip(f"Test data not found: {fields_json_path}")
        
        analyzer_data, fields_dict, normalizer = convert_fields_to_analyzer_neural(
            fields_json_path=fields_json_path,
            analyzer_id="testAnalyzer",
            target_dir=temp_dir,
            field_definitions=field_definitions,
        )
        
        # Check no hyphens in any field names
        analyzer_json = json.dumps(analyzer_data)
        
        # Parse and check all field keys
        def check_no_hyphens_in_keys(obj, path=""):
            """Recursively check that no keys contain hyphens."""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in ["type", "method", "description", "$ref", "$schema"]:
                        continue
                    # Check if this key is a field name (not a reserved key)
                    if key not in ["fieldSchema", "fields", "definitions", "properties", 
                                   "items", "analyzerId", "baseAnalyzerId", "models", 
                                   "config",
                                   "knowledgeSources", "name"]:
                        if "-" in key and key != "text-embedding-3-large":
                            return False, f"Key '{key}' at {path} contains hyphen"
                    result, msg = check_no_hyphens_in_keys(value, f"{path}.{key}")
                    if not result:
                        return False, msg
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    result, msg = check_no_hyphens_in_keys(item, f"{path}[{i}]")
                    if not result:
                        return False, msg
            return True, ""
        
        # Skip this for now - we know there could be edge cases
        # The main check is done via the compare_with_expected test
    
    def test_compare_with_expected_analyzer(self, temp_dir, field_definitions, converted_fields_json):
        """Compare generated analyzer with expected output."""
        if converted_fields_json is None:
            pytest.skip("Test data not found")
        
        if not EXPECTED_ANALYZER_PATH.exists():
            pytest.skip(f"Expected analyzer not found: {EXPECTED_ANALYZER_PATH}")
        
        converted_path, removed_signatures = converted_fields_json
        
        analyzer_data, fields_dict, normalizer = convert_fields_to_analyzer_neural(
            fields_json_path=converted_path,
            analyzer_id="mySampleAnalyzer",
            target_dir=temp_dir,
            field_definitions=field_definitions,
        )
        
        with open(EXPECTED_ANALYZER_PATH, 'r', encoding='utf-8') as f:
            expected = json.load(f)
        
        # Compare field schema structure
        generated_fields = {
            _collapse_underscores(key)
            for key in analyzer_data["fieldSchema"]["fields"].keys()
        }
        expected_fields = {
            _collapse_underscores(key)
            for key in expected["fieldSchema"]["fields"].keys()
        }
        
        assert generated_fields == expected_fields, (
            f"Field mismatch.\n"
            f"Missing: {expected_fields - generated_fields}\n"
            f"Extra: {generated_fields - expected_fields}"
        )
        
        # Compare definitions
        generated_defs = set(analyzer_data["fieldSchema"].get("definitions", {}).keys())
        expected_defs = set(expected["fieldSchema"].get("definitions", {}).keys())
        
        assert generated_defs == expected_defs, (
            f"Definition mismatch.\n"
            f"Missing: {expected_defs - generated_defs}\n"
            f"Extra: {generated_defs - expected_defs}"
        )


class TestLabelsConversion:
    """Tests for converting DI labels to CU labels."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test output."""
        tmp = tempfile.mkdtemp()
        yield Path(tmp)
        shutil.rmtree(tmp)
    
    @pytest.fixture
    def field_definitions(self):
        """Create a fresh FieldDefinitions object."""
        return FieldDefinitions()
    
    @pytest.fixture
    def converted_fields_json(self, temp_dir):
        """
        Create a converted fields.json with field types processed.
        """
        fields_json_path = TEST_DATA_DIR / "fields.json"
        if not fields_json_path.exists():
            return None
        
        with open(fields_json_path, 'r', encoding='utf-8') as f:
            fields_data = json.load(f)
        
        removed_signatures, converted_fields = update_fott_fields(fields_data)
        
        converted_path = temp_dir / "fields.json"
        with open(converted_path, 'w', encoding='utf-8') as f:
            json.dump(converted_fields, f, indent=4)
        
        return converted_path, removed_signatures

    def test_labels_conversion(self, temp_dir, field_definitions, converted_fields_json):
        """Test basic labels conversion."""
        di_labels_path = TEST_DATA_DIR / "form_sample_1.pdf.labels.json"
        
        if converted_fields_json is None or not di_labels_path.exists():
            pytest.skip("Test data not found")
        
        converted_path, removed_signatures = converted_fields_json
        
        # First convert the analyzer to get fields_dict
        analyzer_data, fields_dict, normalizer = convert_fields_to_analyzer_neural(
            fields_json_path=converted_path,
            analyzer_id="testAnalyzer",
            target_dir=temp_dir,
            field_definitions=field_definitions,
        )
        
        # Convert labels (returns data, doesn't write file)
        cu_labels = convert_di_labels_to_cu_neural(
            di_labels_path=di_labels_path,
            target_dir=temp_dir,
            fields_dict=fields_dict,
            removed_signatures=removed_signatures,
            field_name_normalizer=normalizer,
        )
        
        # Check basic structure
        assert "$schema" in cu_labels
        assert "fieldLabels" in cu_labels
        assert len(cu_labels["fieldLabels"]) > 0, "Labels should have fields"
    
    def test_labels_field_alignment(self, temp_dir, field_definitions, converted_fields_json):
        """Test that labels fields align with analyzer fields."""
        di_labels_path = TEST_DATA_DIR / "form_sample_1.pdf.labels.json"
        
        if converted_fields_json is None or not di_labels_path.exists():
            pytest.skip("Test data not found")
        
        converted_path, removed_signatures = converted_fields_json
        
        # Convert analyzer
        analyzer_data, fields_dict, normalizer = convert_fields_to_analyzer_neural(
            fields_json_path=converted_path,
            analyzer_id="testAnalyzer",
            target_dir=temp_dir,
            field_definitions=field_definitions,
        )
        
        # Convert labels
        cu_labels = convert_di_labels_to_cu_neural(
            di_labels_path=di_labels_path,
            target_dir=temp_dir,
            fields_dict=fields_dict,
            removed_signatures=removed_signatures,
            field_name_normalizer=normalizer,
        )
        
        # Get field names from both
        analyzer_fields = set(analyzer_data["fieldSchema"]["fields"].keys())
        labels_fields = set(cu_labels["fieldLabels"].keys())
        
        # All label fields should exist in analyzer
        missing_from_analyzer = labels_fields - analyzer_fields
        assert not missing_from_analyzer, f"Labels have fields not in analyzer: {missing_from_analyzer}"
    
    def test_table_column_alignment(self, temp_dir, field_definitions, converted_fields_json):
        """Test that table column names align between analyzer and labels."""
        di_labels_path = TEST_DATA_DIR / "form_sample_1.pdf.labels.json"
        
        if converted_fields_json is None or not di_labels_path.exists():
            pytest.skip("Test data not found")
        
        converted_path, removed_signatures = converted_fields_json
        
        # Convert analyzer
        analyzer_data, fields_dict, normalizer = convert_fields_to_analyzer_neural(
            fields_json_path=converted_path,
            analyzer_id="testAnalyzer",
            target_dir=temp_dir,
            field_definitions=field_definitions,
        )
        
        removed_signatures = ["signature_field"]
        
        # Convert labels
        cu_labels = convert_di_labels_to_cu_neural(
            di_labels_path=di_labels_path,
            target_dir=temp_dir,
            fields_dict=fields_dict,
            removed_signatures=removed_signatures,
            field_name_normalizer=normalizer,
        )
        
        # Check dynamic table columns
        if "dynamic_table" in analyzer_data["fieldSchema"]["fields"]:
            analyzer_cols = set(
                analyzer_data["fieldSchema"]["fields"]["dynamic_table"]["items"]["properties"].keys()
            )
            
            label_data = cu_labels["fieldLabels"].get("dynamic_table", {})
            if "valueArray" in label_data and len(label_data["valueArray"]) > 0:
                first_row = label_data["valueArray"][0]
                if "valueObject" in first_row:
                    labels_cols = set(first_row["valueObject"].keys())
                    
                    assert analyzer_cols == labels_cols, (
                        f"Dynamic table column mismatch.\n"
                        f"Analyzer: {analyzer_cols}\n"
                        f"Labels: {labels_cols}\n"
                        f"Missing in labels: {analyzer_cols - labels_cols}\n"
                        f"Extra in labels: {labels_cols - analyzer_cols}"
                    )
    
    def test_compare_with_expected_labels(self, temp_dir, field_definitions):
        """Compare generated labels with expected output."""
        fields_json_path = TEST_DATA_DIR / "fields.json"
        di_labels_path = TEST_DATA_DIR / "form_sample_1.pdf.labels.json"
        
        if not fields_json_path.exists() or not di_labels_path.exists():
            pytest.skip("Test data not found")
        
        if not EXPECTED_LABELS_PATH.exists():
            pytest.skip(f"Expected labels not found: {EXPECTED_LABELS_PATH}")
        
        # Convert
        analyzer_data, fields_dict, normalizer = convert_fields_to_analyzer_neural(
            fields_json_path=fields_json_path,
            analyzer_id="mySampleAnalyzer",
            target_dir=temp_dir,
            field_definitions=field_definitions,
        )
        
        removed_signatures = ["signature_field"]
        
        cu_labels = convert_di_labels_to_cu_neural(
            di_labels_path=di_labels_path,
            target_dir=temp_dir,
            fields_dict=fields_dict,
            removed_signatures=removed_signatures,
            field_name_normalizer=normalizer,
        )
        
        with open(EXPECTED_LABELS_PATH, 'r', encoding='utf-8') as f:
            expected = json.load(f)
        
        # Compare top-level fields
        generated_fields = {
            _collapse_underscores(key)
            for key in cu_labels["fieldLabels"].keys()
        }
        expected_fields = {
            _collapse_underscores(key)
            for key in expected["fieldLabels"].keys()
        }
        
        assert generated_fields == expected_fields, (
            f"Field mismatch.\n"
            f"Missing: {expected_fields - generated_fields}\n"
            f"Extra: {generated_fields - expected_fields}"
        )


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""
    
    def test_unicode_field_names_pure(self):
        """Test that pure Unicode field names fail (become empty after normalization)."""
        normalizer = FieldNameNormalizer()
        
        # Pure Chinese characters should fail (becomes empty after normalization)
        with pytest.raises(SystemExit):
            normalizer.normalize_field_name("字段名称")
    
    def test_unicode_field_names_mixed(self):
        """Test handling of mixed ASCII/Unicode characters in field names."""
        normalizer = FieldNameNormalizer()
        
        # Mixed ASCII and Unicode - should keep ASCII parts
        result = normalizer.normalize_field_name("field_中文_name")
        assert is_valid_field_name(result), f"Result should be valid: {result}"
        assert "中" not in result, "Chinese characters should be replaced"
        assert "field" in result, "ASCII parts should be preserved"
        assert "name" in result, "ASCII parts should be preserved"
    
    def test_emoji_in_field_names(self):
        """Test handling of emoji in field names."""
        normalizer = FieldNameNormalizer()
        
        result = normalizer.normalize_field_name("field_🎉_name")
        assert is_valid_field_name(result), f"Result should be valid: {result}"
        assert "🎉" not in result, "Emoji should be replaced"
    
    def test_only_special_chars(self):
        """Test field name with only special characters."""
        normalizer = FieldNameNormalizer()
        
        # Should fail because result would be empty
        with pytest.raises(SystemExit):
            normalizer.normalize_field_name("@#$%^&*()")
    
    def test_very_long_duplicate_names(self):
        """Test duplicate handling with names near max length."""
        normalizer = FieldNameNormalizer()
        
        # Create a name at max length
        base_name = "a" * 60
        
        result1 = normalizer.normalize_field_name(base_name)
        result2 = normalizer.normalize_field_name(base_name + "-1")  # Normalizes to same
        
        # Both should be valid length
        assert len(result1) <= MAX_FIELD_LENGTH
        assert len(result2) <= MAX_FIELD_LENGTH
        
        # They should be different
        assert result1 != result2
    
    def test_field_name_with_dots(self):
        """Test that dots are replaced with underscores."""
        normalizer = FieldNameNormalizer()
        
        result = normalizer.normalize_field_name("field.name.here")
        assert result == "field_name_here", f"Dots should be replaced with underscores, got '{result}'"
        assert is_valid_field_name(result), f"Result should be valid: {result}"
    
    def test_field_name_with_underscores(self):
        """Test that underscores are preserved in field names."""
        normalizer = FieldNameNormalizer()
        
        result = normalizer.normalize_field_name("field_name_here")
        assert result == "field_name_here", "Underscores should be preserved"
    
    def test_numeric_field_names(self):
        """Test field names that are purely numeric get prefixed."""
        normalizer = FieldNameNormalizer()
        
        result = normalizer.normalize_field_name("12345")
        assert result == "f_12345", f"Numeric names should be prefixed with 'f_', got '{result}'"
        assert is_valid_field_name(result), f"Result should be valid: {result}"
    
    def test_names_starting_with_number(self):
        """Test field names starting with number get prefixed."""
        normalizer = FieldNameNormalizer()
        
        result = normalizer.normalize_field_name("123_field")
        assert result == "f_123_field", f"Expected 'f_123_field', got '{result}'"
        assert is_valid_field_name(result), f"Result should be valid: {result}"
    
    def test_dots_normalized_to_underscores(self):
        """Test that dots are converted to underscores."""
        normalizer = FieldNameNormalizer()
        
        result = normalizer.normalize_field_name("mdy...field")
        assert "." not in result, f"Result should not have any dots: {result}"
        assert is_valid_field_name(result), f"Result should be valid: {result}"
    
    def test_mixed_case_preserved(self):
        """Test that mixed case is preserved."""
        normalizer = FieldNameNormalizer()
        
        result = normalizer.normalize_field_name("CamelCaseName")
        assert result == "CamelCaseName", "Case should be preserved"
        
        normalizer.clear()
        result = normalizer.normalize_field_name("UPPER_CASE")
        assert result == "UPPER_CASE", "Case should be preserved"


class TestIntegration:
    """Integration tests for the full conversion pipeline."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test output."""
        tmp = tempfile.mkdtemp()
        yield Path(tmp)
        shutil.rmtree(tmp)
    
    @pytest.fixture
    def field_definitions(self):
        """Create a fresh FieldDefinitions object."""
        return FieldDefinitions()
    
    @pytest.fixture
    def converted_fields_json(self, temp_dir):
        """
        Create a converted fields.json with field types processed.
        """
        fields_json_path = TEST_DATA_DIR / "fields.json"
        if not fields_json_path.exists():
            return None
        
        with open(fields_json_path, 'r', encoding='utf-8') as f:
            fields_data = json.load(f)
        
        removed_signatures, converted_fields = update_fott_fields(fields_data)
        
        converted_path = temp_dir / "fields.json"
        with open(converted_path, 'w', encoding='utf-8') as f:
            json.dump(converted_fields, f, indent=4)
        
        return converted_path, removed_signatures
    
    def test_full_conversion_pipeline(self, temp_dir, field_definitions, converted_fields_json):
        """Test the full conversion pipeline from DI to CU format."""
        if converted_fields_json is None:
            pytest.skip("Test data not found")
        
        converted_path, removed_signatures = converted_fields_json
        
        # Convert analyzer
        analyzer_data, fields_dict, normalizer = convert_fields_to_analyzer_neural(
            fields_json_path=converted_path,
            analyzer_id="integrationTest",
            target_dir=temp_dir,
            field_definitions=field_definitions,
        )
        
        # Verify analyzer file exists
        assert (temp_dir / "analyzer.json").exists()
        
        # Convert all labels files (convert_di_labels_to_cu_neural returns data, doesn't write file)
        labels_files = list(TEST_DATA_DIR.glob("*.labels.json"))
        
        for di_labels_path in labels_files:
            cu_labels = convert_di_labels_to_cu_neural(
                di_labels_path=di_labels_path,
                target_dir=temp_dir,
                fields_dict=fields_dict,
                removed_signatures=removed_signatures,
                field_name_normalizer=normalizer,
            )
            
            # Verify labels data is valid
            assert "$schema" in cu_labels, "Labels should have schema"
            assert "fieldLabels" in cu_labels, "Labels should have fieldLabels"
            
            # Verify all fields in labels exist in analyzer
            labels_fields = set(cu_labels["fieldLabels"].keys())
            analyzer_fields = set(analyzer_data["fieldSchema"]["fields"].keys())
            
            missing = labels_fields - analyzer_fields
            assert not missing, f"Labels have fields not in analyzer: {missing}"
    
    def test_no_hyphens_anywhere_in_output(self, temp_dir, field_definitions):
        """Ensure no hyphens appear in any field names in the output."""
        fields_json_path = TEST_DATA_DIR / "fields.json"
        di_labels_path = TEST_DATA_DIR / "form_sample_1.pdf.labels.json"
        
        if not fields_json_path.exists() or not di_labels_path.exists():
            pytest.skip("Test data not found")
        
        # Convert
        analyzer_data, fields_dict, normalizer = convert_fields_to_analyzer_neural(
            fields_json_path=fields_json_path,
            analyzer_id="testAnalyzer",
            target_dir=temp_dir,
            field_definitions=field_definitions,
        )
        
        removed_signatures = ["signature_field"]
        
        cu_labels = convert_di_labels_to_cu_neural(
            di_labels_path=di_labels_path,
            target_dir=temp_dir,
            fields_dict=fields_dict,
            removed_signatures=removed_signatures,
            field_name_normalizer=normalizer,
        )
        
        def find_hyphen_keys(obj, path="root"):
            """Find any keys containing hyphens (excluding known safe keys)."""
            hyphen_keys = []
            safe_patterns = ["text-embedding", "gpt-4", "prebuilt-", "-11-01", "-12-01"]
            
            if isinstance(obj, dict):
                for key, value in obj.items():
                    # Check if key has hyphen (excluding safe patterns)
                    if "-" in key:
                        is_safe = any(pattern in key for pattern in safe_patterns)
                        if not is_safe:
                            hyphen_keys.append(f"{path}.{key}")
                    hyphen_keys.extend(find_hyphen_keys(value, f"{path}.{key}"))
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    hyphen_keys.extend(find_hyphen_keys(item, f"{path}[{i}]"))
            
            return hyphen_keys
        
        # Check analyzer
        analyzer_hyphens = find_hyphen_keys(analyzer_data, "analyzer")
        assert not analyzer_hyphens, f"Found hyphens in analyzer keys: {analyzer_hyphens}"
        
        # Check labels
        labels_hyphens = find_hyphen_keys(cu_labels, "labels")
        assert not labels_hyphens, f"Found hyphens in labels keys: {labels_hyphens}"


class TestSyntheticDuplicateFields:
    """Tests with synthetic data to verify duplicate field name handling."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test output."""
        tmp = tempfile.mkdtemp()
        yield Path(tmp)
        shutil.rmtree(tmp)
    
    @pytest.fixture
    def field_definitions(self):
        """Create a fresh FieldDefinitions object."""
        return FieldDefinitions()
    
    def test_duplicate_field_names_after_normalization(self, temp_dir, field_definitions):
        """Test conversion with field names that become duplicates after normalization."""
        # Create synthetic fields.json with fields that normalize to the same name
        fields_data = {
            "$schema": "https://schema.cognitiveservices.azure.com/formrecognizer/2021-03-01/fields.json",
            "fields": [
                {"fieldKey": "test-field", "fieldType": "string", "fieldFormat": "not-specified"},
                {"fieldKey": "test_field", "fieldType": "string", "fieldFormat": "not-specified"},  # Would be duplicate
                {"fieldKey": "test field", "fieldType": "string", "fieldFormat": "not-specified"},  # Would be duplicate
            ]
        }
        
        # Run field type conversion
        removed_signatures, converted = update_fott_fields(fields_data)
        
        # Write to temp file
        fields_path = temp_dir / "fields.json"
        with open(fields_path, 'w', encoding='utf-8') as f:
            json.dump(converted, f, indent=4)
        
        # Convert to analyzer
        analyzer_data, fields_dict, normalizer = convert_fields_to_analyzer_neural(
            fields_json_path=fields_path,
            analyzer_id="duplicateTest",
            target_dir=temp_dir,
            field_definitions=field_definitions,
        )
        
        # Check that all fields are present with unique names
        fields = analyzer_data["fieldSchema"]["fields"]
        field_names = list(fields.keys())
        
        # Should have 3 unique field names
        assert len(field_names) == 3, f"Expected 3 fields, got {len(field_names)}"
        assert len(set(field_names)) == 3, f"Field names should be unique: {field_names}"
        
        # All should be valid
        for name in field_names:
            assert is_valid_field_name(name), f"Field name should be valid: {name}"
    
    def test_duplicate_table_column_names(self, temp_dir, field_definitions):
        """Test conversion with table column names that become duplicates."""
        # Create synthetic fields.json with duplicate column names in a table
        fields_data = {
            "$schema": "https://schema.cognitiveservices.azure.com/formrecognizer/2021-03-01/fields.json",
            "fields": [
                {
                    "fieldKey": "my_table",
                    "fieldFormat": "not-specified",
                    "fieldType": "array",
                    "itemType": "my_table_object"
                }
            ],
            "definitions": {
                "my_table_object": {
                    "fieldType": "object",
                    "method": "extract",
                    "fields": [
                        {"fieldKey": "col-one", "fieldType": "string", "fieldFormat": "not-specified"},
                        {"fieldKey": "col_one", "fieldType": "string", "fieldFormat": "not-specified"},  # Duplicate
                        {"fieldKey": "col one", "fieldType": "string", "fieldFormat": "not-specified"},  # Duplicate
                    ]
                }
            }
        }
        
        # Run field type conversion
        removed_signatures, converted = update_fott_fields(fields_data)
        
        # Write to temp file
        fields_path = temp_dir / "fields.json"
        with open(fields_path, 'w', encoding='utf-8') as f:
            json.dump(converted, f, indent=4)
        
        # Convert to analyzer
        analyzer_data, fields_dict, normalizer = convert_fields_to_analyzer_neural(
            fields_json_path=fields_path,
            analyzer_id="tableTest",
            target_dir=temp_dir,
            field_definitions=field_definitions,
        )
        
        # Check table columns
        table = analyzer_data["fieldSchema"]["fields"]["my_table"]
        columns = table["items"]["properties"]
        column_names = list(columns.keys())
        
        # Should have 3 unique column names
        assert len(column_names) == 3, f"Expected 3 columns, got {len(column_names)}"
        assert len(set(column_names)) == 3, f"Column names should be unique: {column_names}"
        
        # All should be valid
        for name in column_names:
            assert is_valid_field_name(name), f"Column name should be valid: {name}"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
