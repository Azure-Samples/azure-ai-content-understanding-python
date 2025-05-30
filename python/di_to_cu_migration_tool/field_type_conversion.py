# imports from built-in packages
import json
from collections import defaultdict
from pathlib import Path
from typing import Tuple

# imports from same project
from constants import CHECKED_SYMBOL, CONVERT_TYPE_MAP, FIELD_VALUE_MAP, SUPPORT_FIELD_TYPE, UNCHECKED_SYMBOL

def update_unified_schema_fields(fields: dict) -> Tuple[dict, dict]:
    """
    Updaate the unified schema fields to have the proper field types
    Args:
        fields (dict): The unified schema fields to be updated
    Returns:
        Tuple[dict, dict]: The updated unified schema fields and the converted field keys
    """
    converted_field_keys = {
        "primary": [],
        "array": defaultdict(list),
        "object": defaultdict(lambda: defaultdict(list)),
    }
    if "fieldSchema" not in fields:
        return

    for field_key, field_object in fields["fieldSchema"].items():
        if field_object["type"] not in SUPPORT_FIELD_TYPE and field_object["type"] != "signature":
            _update_unified_schema_fields(field_object)
            converted_field_keys["primary"].append(field_key)
        elif field_object["type"] == "array":
            for sub_field_key, sub_field_object in field_object["items"][
                "properties"
            ].items():
                if sub_field_object["type"] not in SUPPORT_FIELD_TYPE:
                    _update_unified_schema_fields(sub_field_object)
                    converted_field_keys["array"][field_key].append(sub_field_key)
        elif field_object["type"] == "object":
            for sub_field_key, sub_field_object in field_object["properties"].items():
                for (
                    _sub_field_key,
                    _sub_field_object,
                ) in sub_field_object["properties"].items():
                    if _sub_field_object["type"] not in SUPPORT_FIELD_TYPE:
                        _update_unified_schema_fields(_sub_field_object)
                        converted_field_keys["object"][field_key][sub_field_key].append(
                            _sub_field_key
                        )
    return fields, converted_field_keys

def _update_unified_schema_fields(field_object: dict) -> None:
    """
    Helper function to update the unified schema field object to have the proper field type
    Args:
        field_object (dict): The unified schema field object to be updated
    """
    original_type = field_object["type"]
    field_object["type"] = CONVERT_TYPE_MAP[original_type] \
        if original_type in CONVERT_TYPE_MAP else "string"

def update_unified_schema_labels(
    labels: dict, converted_field_keys: list[str], output_path: Path
) -> None:
    """
    Update the unified schema labels to have the proper field types per the converted field keys
    Args:
        labels (dict): The unified schema labels to be updated
        converted_field_keys (list[str]): The converted field keys to be used to update the labels
        output_path (Path): The path to the output file (i.e. the updated labels)
    """
    for label_key, label_object in labels["fieldLabels"].items():
        if label_key in converted_field_keys.get("primary", []):
            _update_unified_schema_labels(label_key, label_object)
        elif label_object["type"] == "array" and label_key in converted_field_keys.get(
            "array", {}
        ):
            for sub_label_object in label_object["valueArray"]:
                for _sub_label_key, _sub_label_object in sub_label_object[
                    "valueObject"
                ].items():
                    if _sub_label_key in converted_field_keys.get("array", {}).get(
                        label_key, []
                    ):
                        _update_unified_schema_labels(_sub_label_key, _sub_label_object)
        elif label_object["type"] == "object" and label_key in converted_field_keys.get(
            "object", {}
        ):
            for sub_label_key, sub_label_object in label_object["valueObject"].items():
                for (
                    _sub_label_key,
                    _sub_label_object,
                ) in sub_label_object["valueObject"].items():
                    if _sub_label_key in converted_field_keys.get("object", {}).get(
                        label_key, {}
                    ).get(sub_label_key, []):
                        _update_unified_schema_labels(_sub_label_key, _sub_label_object)
    with open(str(output_path), "w") as fp:
        json.dump(labels, fp, ensure_ascii=False, indent=4)

def _update_unified_schema_labels(label_key: str, label_object: dict) -> None:
    """
    Helper function to update the unified schema label object to have the proper field type
    Args:
        label_key (str): The unified schema label key to be updated
        label_object (dict): The unified schema label object to be updated
    """
    value_key = FIELD_VALUE_MAP.get(label_object["type"])
    if value_key is None:
        print(f"Unsupported field type: '{label_object['type']}'")
    if label_object["type"] == "currency":
        try:
            label_object["valueNumber"] = label_object["valueCurrency"]["amount"]
        except KeyError:
            try:
                label_object["valueNumber"] = float(
                    label_object["content"].replace(",", "")
                )
            except Exception as e:
                print(f"Error converting currency: {e}")

        label_object["type"] = "number"
    elif label_object["type"] == "selectionMark":
        if label_object["content"] in ["selected", ":selected:"]:
            label_object["valueBoolean"] = True
            label_object["content"] = CHECKED_SYMBOL
        else:
            label_object["valueBoolean"] = False
            label_object["content"] = UNCHECKED_SYMBOL
        label_object["type"] = "boolean"
    elif label_object["type"] == "string":
        label_object["valueString"] = label_object["content"]
    else:
        label_object["type"] = "string"
        label_object["valueString"] = label_object["content"]
    label_object.pop(value_key) if value_key in label_object else None

def update_fott_fields(fields: dict) -> Tuple[list, dict]:
    """
    Update the FOTT fields to have the proper field types
    Args:
        fields (dict): The FOTT fields to be updated
    Returns:
        Tuple[list, dict]: The updated FOTT fields and the converted field keys
    """
    if "$schema" not in fields:
        return fields
    if "fields" not in fields:
        return fields
    signatures = []
     # Filter out fields with fieldType "signature" and collect their fieldKeys
    new_fields = []
    for field in fields["fields"]:
        if field["fieldType"] == "signature":
            signatures.append(field["fieldKey"])
            continue
        new_fields.append(field)

    for i, field in enumerate(new_fields):
        if field["fieldType"] not in SUPPORT_FIELD_TYPE:
            original_type = field["fieldType"]
            field["fieldType"] = CONVERT_TYPE_MAP[original_type] \
                if original_type in CONVERT_TYPE_MAP else "string"

    if "definitions" in fields:
        for field_key, field_definition in fields["definitions"].items():
            for field in field_definition.get("fields", []):
                if field["fieldType"] not in SUPPORT_FIELD_TYPE and field["fieldType"] != "signature":
                    original_type = field["fieldType"]
                    field["fieldType"] = CONVERT_TYPE_MAP[original_type] \
                        if original_type in CONVERT_TYPE_MAP else "string"

    fields["fields"] = new_fields
    return signatures, fields

def update_fott_labels(labels: dict, output_path: Path) -> None:
     """
     Update the FOTT labels to have the proper field types
     Args:
         labels (dict): The FOTT labels to be updated
         output_path (Path): The path to the output file (i.e. the updated labels)
     """
     for label_key, label_object in labels["fieldLabels"].items():
        if label_object["type"] == "array":
            for value_array in label_object["valueArray"]:
                for value_object_key, value_object_value in value_array["valueObject"].items():
                    _update_boolean_label(value_object_key, value_object_value)
        elif label_object["type"] == "object":
            for row_key, row_object in label_object["valueObject"].items():
                for col_key, col_object in row_object["valueObject"].items():
                    _update_boolean_label(col_key, col_object)
        else:
            _update_boolean_label(label_key, label_object)
     with open(str(output_path), "w") as fp:
        json.dump(labels, fp, ensure_ascii=False, indent=4)

def _update_boolean_label(label_key: str, label_object: dict) -> None:
    """
    Helper function to update the FOTT label object if it is a boolean type
    Args:
        label_key (str): The FOTT label key to be updated
        label_object (dict): The FOTT label object to be updated
    """
    if label_object["type"] == "boolean":
        if label_object["valueBoolean"] in ["selected", ":selected:"]:
            label_object["valueBoolean"] = True
        else:
            label_object["valueBoolean"] = False
