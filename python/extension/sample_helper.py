# pylint: disable=line-too-long,useless-suppression
# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------
"""
Helper functions for Azure AI Content Understanding samples.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional, Dict


def get_field_value(fields: Dict[str, Any], field_name: str) -> Any:
    """
    Extract the actual value from a field dictionary.

    Args:
        fields: A dictionary of field names to field data dictionaries.
        field_name: The name of the field to extract.

    Returns:
        The extracted value or None if not found.
    """
    if not fields or field_name not in fields:
        return None

    field_data = fields[field_name]

    # Extract the value from the field dictionary
    if isinstance(field_data, dict):
        return field_data.get("value") or field_data.get("valueString") or field_data.get("content")
    return field_data


def save_json_to_file(result, output_dir: str = "test_output", filename_prefix: str = "analysis_result") -> str:
    """Persist the full AnalyzeResult as JSON and return the file path."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"{filename_prefix}_{timestamp}.json")
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(result, fp, indent=2, ensure_ascii=False)
    print(f"💾 Analysis result saved to: {path}")
    return path
