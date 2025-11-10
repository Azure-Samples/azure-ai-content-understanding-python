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
from azure.ai.contentunderstanding.models import (
    ContentField,
)


def get_field_value(fields: Dict[str, ContentField], field_name: str) -> Any:
    """
    Extract the actual value from a ContentField using the unified .value property.

    Args:
        fields: A dictionary of field names to ContentField objects.
        field_name: The name of the field to extract.

    Returns:
        The extracted value or None if not found.
    """
    if not fields or field_name not in fields:
        return None

    field_data = fields[field_name]

    # Simply use the .value property which works for all ContentField types
    return field_data.value  # type: ignore[attr-defined] # pyright: ignore[reportAttributeAccessIssue]


def save_json_to_file(result, output_dir: str = "test_output", filename_prefix: str = "analysis_result") -> str:
    """Persist the full AnalyzeResult as JSON and return the file path."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"{filename_prefix}_{timestamp}.json")
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(result, fp, indent=2, ensure_ascii=False)
    print(f"💾 Analysis result saved to: {path}")
    return path
