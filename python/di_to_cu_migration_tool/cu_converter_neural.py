# imports from built-in packages
from dateutil.parser import parse
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from typing import Optional, Tuple

# imports from external packages (need to use pip install)
from rich import print  # For colored output

# imports from same project
from constants import COMPLETE_DATE_FORMATS, CU_API_VERSION, MAX_FIELD_LENGTH, VALID_CU_FIELD_TYPES, COMPLETION_DEPLOYMENT, EMBEDDING_DEPLOYMENT, ANALYZER_JSON
from field_definitions import FieldDefinitions
from field_name_utils import FieldNameNormalizer

# schema constants subject to change
ANALYZER_FIELDS = "fieldSchema"
# The analyzer description is left empty by default.
# Please review the converted analyzer.json and provide a meaningful description
# that helps Content Understanding extract your fields accurately.
DEFAULT_ANALYZER_DESCRIPTION = ""
CU_LABEL_SCHEMA = f"https://schema.ai.azure.com/mmi/{CU_API_VERSION}/labels.json"

def convert_bounding_regions_to_source(page_number: int, polygon: list) -> str:
    """
    Convert bounding regions to source format.
    Args:
        page_number (int): The page number of the bounding region.
        polygon (list): The coordinates of the bounding region
    Returns:
        str: The source string in the format D(page_number, x1,y1,x2,y2,...).
    """

    # Convert polygon to string format
    polygon_str = ",".join(str(coord) for coord in polygon)
    source = f"D({page_number},{polygon_str})"
    return source

def convert_fields_to_analyzer_neural(fields_json_path: Path, analyzer_id: Optional[str], target_dir: Optional[Path], field_definitions: FieldDefinitions, target_container_sas_url: str = None, target_blob_folder: str = None, field_name_normalizer: FieldNameNormalizer = None, completion_deployment: Optional[str] = None, embedding_deployment: Optional[str] = None) -> Tuple[dict, dict, FieldNameNormalizer]:
    """
    Convert DI 3.1/4.0GA Custom Neural fields.json to analyzer.json format.
    Args:
        fields_json_path (Path): Path to the input fields.json file.
        analyzer_id (Optional(str)): The analyzer ID for the created CU analyzer.
        target_dir (Optional[Path]): Output directory for the analyzer.json file.
        field_definitions (FieldDefinitions): Field definitions object to store field definitions for analyzer.json if there are any fixed tables.
        target_container_sas_url (str): Optional target container SAS URL for training data.
        target_blob_folder (str): Optional target blob folder prefix for training data.
        field_name_normalizer (FieldNameNormalizer): Optional normalizer instance for field names.
    Returns:
        Tuple[dict, dict, FieldNameNormalizer]: The analyzer data, a dictionary of the fields and their types for label conversion, and the field name normalizer.
    """
    try:
        with open(fields_json_path, 'r', encoding="utf-8") as f:
            fields_data = json.load(f)
    except FileNotFoundError:
        print(f"[red]Error: fields.json file not found at {fields_json_path}.[/red]")
        sys.exit(1)
    except json.JSONDecodeError:
        print("[red]Error: Invalid JSON in fields.json.[/red]")
        sys.exit(1)

    # Good to do before each analyzer.json conversion
    field_definitions.clear_definitions()
    
    # Initialize field name normalizer if not provided
    if field_name_normalizer is None:
        field_name_normalizer = FieldNameNormalizer()
    else:
        field_name_normalizer.clear()

    # Need to store the fields and types, so that we can access them when converting the labels.json files
    # Keys in fields_dict use ORIGINAL names for label lookup, but we also track normalized names
    fields_dict = {}
    # Map from original field names to normalized names for label conversion
    original_to_normalized = {}

    completion_deployment = completion_deployment or COMPLETION_DEPLOYMENT
    embedding_deployment = embedding_deployment or EMBEDDING_DEPLOYMENT

    # Build analyzer.json content
    analyzer_data = {
        "analyzerId": analyzer_id,
        "baseAnalyzerId": "prebuilt-document",
        "models": {
            "completion": completion_deployment,
            "embedding": embedding_deployment
        },
        "config": {
            "returnDetails": True,
            "enableLayout": True,
            "enableFormula": False,
            "estimateFieldSourceAndConfidence": True
        },
        ANALYZER_FIELDS: {
            "name": analyzer_id,
            "description": DEFAULT_ANALYZER_DESCRIPTION,
            "fields": {},
            "definitions": {}
        }
    }

    # Update field schema to be in CU format
    fields = fields_data.get("fields", [])
    definitions = fields_data.get("definitions", {})

    if (len(fields) == 0):
        print("[red]Error: Fields.json should not be empty.[/red]")
        sys.exit(1)

    for field in fields:
        original_key = field.get("fieldKey")
        # Normalize the field key to match CU API requirements
        analyzer_key = field_name_normalizer.normalize_field_name(original_key, context="analyzer fields")
        
        analyzer_type = field.get("fieldType")
        analyzer_field = {
            "type": analyzer_type,
            "method": field.get("method", "extract"),
            "description": field.get("description", "")
        }

        # Store mapping from original to normalized for label conversion
        original_to_normalized[original_key] = analyzer_key
        fields_dict[original_key] = analyzer_type # Adds the field type to our dictionary using ORIGINAL key

        if analyzer_type == "array": # for dynamic tables
            analyzer_field["method"] = "generate"
            # need to get the items from the definition
            item_definition = definitions.get(field.get("itemType"))
            array_fields_dict, analyzer_field["items"] = convert_array_items(analyzer_key, item_definition, field_name_normalizer, original_key, original_to_normalized)
            fields_dict.update(array_fields_dict)

        elif analyzer_type == "object": # for fixed tables
            analyzer_field["method"] = "generate"
            object_fields_dict, analyzer_field["properties"] = convert_object_properties(field, definitions, analyzer_key, field_definitions, field_name_normalizer, original_key, original_to_normalized)
            fields_dict.update(object_fields_dict)

        # Add to analyzer fields with normalized key
        analyzer_data[ANALYZER_FIELDS]["fields"][analyzer_key] = analyzer_field

    analyzer_data[ANALYZER_FIELDS]["definitions"] = field_definitions.get_all_definitions()

    # Determine output path
    if target_dir:
        analyzer_json_path = target_dir / ANALYZER_JSON
    else:
        analyzer_json_path = fields_json_path.parent / ANALYZER_JSON

    # Add knowledgeSources section if container info is provided
    if target_container_sas_url and target_blob_folder:
        analyzer_data["knowledgeSources"] = [
            {
                "kind": "labeledData",
                "containerUrl": target_container_sas_url,
                "prefix": target_blob_folder,
                "fileListPath": ""
            }
        ]
    
    # Ensure target directory exists
    analyzer_json_path.parent.mkdir(parents=True, exist_ok=True)

    # Write analyzer.json
    with open(analyzer_json_path, 'w') as f:
        json.dump(analyzer_data, f, indent=4)

    print(f"[green]Successfully converted {fields_json_path} to analyzer.json at {analyzer_json_path}[/green]\n")

    return analyzer_data, fields_dict, field_name_normalizer

def convert_array_items(analyzer_key: str, item_definition: dict, field_name_normalizer: FieldNameNormalizer, original_table_key: str, original_to_normalized: dict) -> Tuple[dict, dict]:
    """
    Helper function to convert array items for the analyzer.
    Args:
        analyzer_key (str): The normalized dictionary key for the array item (i.e., the name of the dynamic table).
        item_definition (dict): The item definition from the fields.json file (i.e. the itemType value)
        field_name_normalizer (FieldNameNormalizer): Field name normalizer for column names.
        original_table_key (str): The original table key before normalization.
        original_to_normalized (dict): Mapping from original to normalized field names.
    Returns:
        Tuple[dict, dict]: A tuple containing two dictionaries:
            - The first dictionary contains the field names and types for the array items (using original keys for label lookup).
            - The second dictionary contains the items or rows within the dynamic table (using normalized keys)
    """
    array_fields_dict = {}
    items = {
        "type": item_definition.get("fieldType"),
        "method": item_definition.get("method", "extract"),
        "properties": {}
    }

    for column in item_definition.get("fields", []):
        original_column_key = column.get("fieldKey")
        # Normalize the column key
        normalized_column_key = field_name_normalizer.normalize_field_name(original_column_key, context=f"array '{analyzer_key}' column")
        column_type = column.get("fieldType")
        items["properties"][normalized_column_key] = {
            "type": column_type,
            "method": column.get("method", "extract"),
            "description": column.get("description", ""),
        }
        # Note: fieldFormat is not included in CU output - it's a DI-only field
        # Store with ORIGINAL key for label lookup (using original table name and column name)
        array_fields_dict[f"{original_table_key}/{original_column_key}"] = column_type
        # Track the normalized name mapping
        original_to_normalized[f"{original_table_key}/{original_column_key}"] = f"{analyzer_key}/{normalized_column_key}"

    return array_fields_dict, items

def convert_object_properties(field: dict, definitions: dict, analyzer_key: str, field_definitions: FieldDefinitions, field_name_normalizer: FieldNameNormalizer, original_table_key: str, original_to_normalized: dict) -> Tuple[dict, dict]:
    """
    Helper function to convert object properties for the analyzer.
    Args:
        field (dict): The field from the fields.json file for the fixed table.
        definitions (dict): The definitions from the fields.json file definitions section for the fixed table.
        analyzer_key (str): The normalized dictionary key for the object (i.e., the name of the fixed table).
        field_definitions (FieldDefinitions): Field definitions object to store field definitions for analyzer.json if there are any fixed tables.
        field_name_normalizer (FieldNameNormalizer): Field name normalizer for row and column names.
        original_table_key (str): The original table key before normalization.
        original_to_normalized (dict): Mapping from original to normalized field names.
    Returns:
        Tuple[dict, dict]: A tuple containing two dictionaries:
            - The first dictionary contains the field names in fott format and types for the object properties.
            - The second dictionary contains the properties or rows within the fixed table
    """
    object_fields_dict = {}
    properties = {}
    di_rows = field.get("fields", [])
    original_first_row_name = di_rows[0].get("fieldKey") if di_rows else ""
    normalized_first_row_name = field_name_normalizer.normalize_field_name(original_first_row_name, context=f"fixed table '{analyzer_key}' first row") if original_first_row_name else ""

    for i, di_row in enumerate(di_rows):
        original_row_name = di_row.get("fieldKey")
        normalized_row_name = field_name_normalizer.normalize_field_name(original_row_name, context=f"fixed table '{analyzer_key}' row")
        if i == 0:
            row_definition = definitions.get(di_row.get("fieldType"))
            column_fields_dict = _add_object_definition(row_definition, analyzer_key, normalized_first_row_name, field_definitions, field_name_normalizer, original_table_key, original_first_row_name, original_to_normalized)
        properties[normalized_row_name] = {"$ref": f"#/$defs/{analyzer_key}_{normalized_first_row_name}"}
        for original_column_name, column_type in column_fields_dict.items():
            # Store with ORIGINAL key pattern for label lookup (using backslash as in original code)
            object_fields_dict[f"{original_table_key}\\{original_row_name}\\{original_column_name}"] = column_type
            # Track the normalized name mapping
            normalized_column_name = field_name_normalizer.get_normalized_name(original_column_name)
            original_to_normalized[f"{original_table_key}\\{original_row_name}\\{original_column_name}"] = f"{analyzer_key}/{normalized_row_name}/{normalized_column_name}"

    return object_fields_dict, properties

def _add_object_definition(row_definition: dict, analyzer_key: str, first_row_name: str, field_definitions: FieldDefinitions, field_name_normalizer: FieldNameNormalizer, original_table_key: str, original_first_row_name: str, original_to_normalized: dict) -> dict:
    """
    Helper function to add object definitions to the analyzer.
    Args:
        row_definition (dict): The row definition from the fields.json file for the fixed table.
        analyzer_key (str): The normalized dictionary key for the object (i.e., the name of the fixed table).
        first_row_name (str): The normalized name of the first row in the fixed table.
        field_definitions (FieldDefinitions): Field definitions object to store field definitions for analyzer.json if there are any fixed tables.
        field_name_normalizer (FieldNameNormalizer): Field name normalizer for column names.
        original_table_key (str): The original table key before normalization.
        original_first_row_name (str): The original first row name before normalization.
        original_to_normalized (dict): Mapping from original to normalized field names.
    Returns:
        dict: A dictionary containing the ORIGINAL field names and types for the object properties (for label lookup).
    """
    column_fields_dict = {}  # Maps original column names to types
    definition = {
        "type": "object",
        "properties": {}
    }

    for column in row_definition.get("fields", []):
        original_column_key = column.get("fieldKey")
        # Normalize the column key
        normalized_column_key = field_name_normalizer.normalize_field_name(original_column_key, context=f"fixed table '{analyzer_key}' column")
        column_type = column.get("fieldType")
        definition["properties"][normalized_column_key] = {
            "type": column_type,
            "method": column.get("method", "extract"),
            "description": column.get("description", ""),
        }
        # Note: fieldFormat is not included in CU output - it's a DI-only field
        # Store ORIGINAL column key for label lookup
        column_fields_dict[original_column_key] = column_type
    
    definitions_key = f"{analyzer_key}_{first_row_name}"
    if len(definitions_key) > MAX_FIELD_LENGTH:
        print(f"[red]Error: The fixed table definition '{definitions_key}' will contain {len(definitions_key)}, which exceeds the limit of {MAX_FIELD_LENGTH} characters. Please shorten either the table name or row name. [/red]")
        sys.exit(1)
    field_definitions.add_definition(definitions_key, definition)
    return column_fields_dict

def convert_di_labels_to_cu_neural(di_labels_path: Path, target_dir: Path, fields_dict: dict, removed_signatures: list, field_name_normalizer: FieldNameNormalizer = None) -> dict:
    """
    Convert DI 3.1/4.0 GA Custom Neural format labels.json to Content Understanding format labels.json.
    Args:
        di_labels_path (Path): Path to the Document Intelligence labels.json file.
        target_dir (Path): Output directory for the Content Understanding labels.json file.
        fields_dict (dict): Dictionary of field names and types for the labels.json conversion (uses original keys).
        removed_signatures (list): List of removed signatures that we will skip when converting the labels.json file.
        field_name_normalizer (FieldNameNormalizer): Optional normalizer with pre-existing mappings from analyzer conversion.
    Returns:
        dict: The Content Understanding labels.json data.
    """
    try:
        with open(di_labels_path, 'r', encoding="utf-8") as f:
            di_data = json.load(f)
    except FileNotFoundError:
        print(f"[red]Error: Document Intelligence labels.json file not found at {di_labels_path}.[/red]")
        sys.exit(1)
    except json.JSONDecodeError:
        print("[red]Error: Invalid JSON in Document Intelligence labels.json.[/red]")
        sys.exit(1)

    # Start building Content Understanding labels.json
    cu_data = {
        "$schema": CU_LABEL_SCHEMA,
        "fileId": di_data.get("fileId", ""),
        "fieldLabels": {},
        "metadata": di_data.get("metadata", {})
    }

    labels = di_data.get("labels", {})

    for label in labels:
        label_name = label.get("label", None)
        converted_label_name = label_name # for escape logic
        converted_label_name = converted_label_name.replace("~1", "/") # if a slash exists in the label_name, it is replaced with ~1
        converted_label_name = converted_label_name.replace("~0", "~") # if a ~ exists in the label_name, it is replaced with ~0

        label_type = fields_dict.get(label_name, None) # if primitive type, label_type will not be None
        converted_label_type = fields_dict.get(converted_label_name, None)

        if label_name in removed_signatures or converted_label_name in removed_signatures:
            # Skip the label if it is in the removed_signatures list
            continue

        if label_type is None and converted_label_type is None: # for dynamic and fixed tables
            # divide the label_name into table_name, rowNumber/Name, and column_name
            # Example for dynamic tables: ItemList/0/NumOfPackage --> row is number
            # Example for fixed tables: table/wiring/part --> row is name

            parts = label_name.split("/",2)
            table_name = parts[0].replace("~1", "/").replace("~0", "~")
            row = parts[1].replace("~1", "/").replace("~0", "~")
            column_name = parts[2].replace("~1", "/").replace("~0", "~")
            
            # Get normalized names if normalizer is provided
            normalized_table_name = table_name
            normalized_row = row
            normalized_column_name = column_name
            if field_name_normalizer is not None:
                normalized_table_name = field_name_normalizer.get_normalized_name(table_name)
                # For dynamic tables, row is a number index so don't normalize
                # For fixed tables, row is a name so normalize
                normalized_column_name = field_name_normalizer.get_normalized_name(column_name)

            # determine if the table is a fixed or dynamic table
            table_type = fields_dict.get(table_name)
            label_type = table_type

            if label_type == "array": # for dynamic tables
                # need to check if the table already exists & if it doesnt, need to create the cu_label for the table
                if normalized_table_name not in cu_data["fieldLabels"]:
                    cu_label = {
                        "type": label_type,
                        "kind": label.get("kind", "confirmed"),
                        "valueArray": []
                    }
                    # Add table to fieldLabels with normalized name
                    cu_data["fieldLabels"][normalized_table_name] = cu_label
                # need to check if any rows have been defined yet in valueArray
                if len(cu_data["fieldLabels"][normalized_table_name]["valueArray"]) == 0:
                    value_object = {
                        "type": "object",
                        "kind": label.get("kind", "confirmed"),
                        "valueObject": {}
                    }
                    cu_data["fieldLabels"][normalized_table_name]["valueArray"].append(value_object)
                # check if the amount of valueObjects match the rowNumber, if not --> add that many rows
                # this is because sometimes the first label for that table is not for the first row
                if len(cu_data["fieldLabels"][normalized_table_name]["valueArray"]) <= int(row):
                    value_object = {
                        "type": "object",
                        "kind": label.get("kind", "confirmed"),
                        "valueObject": {}
                    }
                    number_of_rows_missing = int(row) - len(cu_data["fieldLabels"][normalized_table_name]["valueArray"]) + 1
                    for i in range(number_of_rows_missing):
                        cu_data["fieldLabels"][normalized_table_name]["valueArray"].append(value_object)

                # actually need to add the column to the valueObject with normalized column name
                label_type = fields_dict.get(f"{table_name}/{column_name}")
                cu_data["fieldLabels"][normalized_table_name]["valueArray"][int(row)]["valueObject"][normalized_column_name] = creating_cu_label_for_neural(label, label_type)

            elif label_type == "object": # for fixed tables
                # For fixed tables, normalize row name as well
                if field_name_normalizer is not None:
                    normalized_row = field_name_normalizer.get_normalized_name(row)
                
                # need to check if the table already exists & if it doesnt, need to create the cu_label for the table
                if normalized_table_name not in cu_data["fieldLabels"]:
                    cu_label = {
                        "type": label_type,
                        "kind": label.get("kind", "confirmed"),
                        "valueObject": {}
                    }
                    # Add table to fieldLabels with normalized name
                    cu_data["fieldLabels"][normalized_table_name] = cu_label
                # need to check if row has been defined, if not define it (using normalized row name)
                if (cu_data["fieldLabels"][normalized_table_name]["valueObject"].get(normalized_row) is None):
                    value_object = {
                        "type": "object",
                        "kind": label.get("kind", "confirmed"),
                        "valueObject": {}
                    }
                    cu_data["fieldLabels"][normalized_table_name]["valueObject"][normalized_row] = value_object

                # actually need to add the column to the valueObject with normalized names
                label_type = fields_dict.get(f"{table_name}\\{row}\\{column_name}")
                cu_data["fieldLabels"][normalized_table_name]["valueObject"][normalized_row]["valueObject"][normalized_column_name] = creating_cu_label_for_neural(label, label_type)
        else:
            # Add field to fieldLabels with normalized name
            original_label_name = converted_label_name
            label_type = converted_label_type
            # Get normalized name if normalizer is provided
            normalized_label_name = original_label_name
            if field_name_normalizer is not None:
                normalized_label_name = field_name_normalizer.get_normalized_name(original_label_name)
            cu_data["fieldLabels"][normalized_label_name] = creating_cu_label_for_neural(label, label_type)

    return cu_data

def creating_cu_label_for_neural(label:dict, label_type: str) -> dict:
    """
    Create a CU label for DI 3.1/4.0 Custom Neural format labels.json.
    Args:
        label (dict): The label to be converted and created.
        label_type (str): The type of the label.
    Returns:
        dict: The converted CU label.
    """
    label_value = VALID_CU_FIELD_TYPES[label_type]
    label_spans = label.get("spans", [])
    label_confidence = label.get("confidence", None)
    label_kind = label.get("kind", "confirmed")
    label_meta_data = label.get("metadata", {})

    value_list = label.get("value") # comes from the label itself & is a list of {page, text, & bounding boxes}
    content = ""
    bounding_regions = []

    for value in value_list:
        content += value.get("text") + " "
        bounding_boxes = value.get("boundingBoxes")[0]
        page_number = value.get("page")
        rounded_regions = [round(value, 4) for value in bounding_boxes] # round to 4 decimal places
        bounding_regions.append(
            {
                "pageNumber": page_number,
                "polygon": rounded_regions
            }
        )

    # Dates seem to be normalized already, but need to convert numbers and integers into the right format of float or int
    final_content = content.strip() # removes trailing space
    if label_type == "number":
        try:
            final_content = float(final_content)
        except Exception as ex:
            # strip the string of all non-numerical values and periods
            string_value = final_content
            cleaned_string = re.sub(r'[^0-9.]', '', string_value)
            cleaned_string = cleaned_string.strip('.')  # Remove any leading or trailing periods
            # if more than one period exists, remove them all
            if cleaned_string.count('.') > 1:
                print("More than one decimal point exists, so will be removing them all.")
                cleaned_string = re.sub(r'\.', '', string_value)
            if not cleaned_string:
                final_content = None
            else:
                final_content = float(cleaned_string)
    elif label_type == "integer":
        try:
            if not final_content:
                final_content = None
            else:
                final_content = int(final_content)
        except Exception as ex:
            # strip the string of all non-numerical values
            string_value = final_content
            cleaned_string = re.sub(r'[^0-9]', '', string_value)
            if not cleaned_string:
                final_content = None
            else:
                final_content = int(cleaned_string)
    elif label_type == "date":
        # dates can be dmy, mdy, ydm, or not specified
        # for CU, the format of our dates should be "%Y-%m-%d"
        original_date = final_content
        format_name = "not specified"
        for fmt in COMPLETE_DATE_FORMATS:
            try:
                date_obj = datetime.strptime(original_date, fmt)
                final_content = date_obj.strftime("%Y-%m-%d")
                format_name = fmt
                break # going with the first format that works
            except ValueError:
                continue
        if format_name == "not specified": # unable to find a format that works
            formats_to_try = ["%B %d,%Y", "parse", "%B %d, %Y", "%m/%d/%Y"]
            finished_date_normalization = False # to keep track of whether we have finished normalizing the date, if not, date will be set to original_date
            for fmt in formats_to_try:
                try:
                    if fmt == "parse":
                        final_content = parse(original_date).date().strftime("%Y-%m-%d")
                    else:
                        date_obj = datetime.strptime(original_date, fmt)
                        final_content = date_obj.strftime("%Y-%m-%d")
                    finished_date_normalization = True
                except Exception as ex:
                    continue
            if not finished_date_normalization:
                final_content = original_date # going with the default

    # Convert bounding_regions to source
    sources = []
    for region in bounding_regions:
        page_number = region.get("pageNumber")
        polygon = region.get("polygon")
        if page_number is None or polygon is None:
            continue
        # Convert polygon to string format
        source = convert_bounding_regions_to_source(page_number, polygon)
        sources.append(source)

    cu_label = {
        "type": label_type,
        label_value: final_content,
        "spans": label_spans,
        "confidence": label_confidence,
        "source": ";".join(sources),
        "kind": label_kind,
        "metadata": label_meta_data
    }
    return cu_label
