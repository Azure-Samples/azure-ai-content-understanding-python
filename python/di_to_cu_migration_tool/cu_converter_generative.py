# imports from built-in packages
from dateutil.parser import parse
from datetime import datetime
import json
from pathlib import Path
import re
import sys
import typer
from typing import Optional, Tuple

# imports from external packages (need to use pip install)
from rich import print  # For colored output

# imports from same project
from constants import CU_API_VERSION, MAX_FIELD_LENGTH, VALID_CU_FIELD_TYPES
from field_definitions import FieldDefinitions

# schema constants subject to change
ANALYZER_FIELDS = "fieldSchema"
# REPLACE THIS WITH YOUR OWN DESCRIPTION IF NEEDED
# Remember that dynamic tables are arrays and fixed tables are objects
ANALYZER_DESCRIPTION = "1. Define your schema by specifying the fields you want to extract from the input files. Choose clear and simple `field names`. Use `field descriptions` to provide explanations, exceptions, rules of thumb, and other details to clarify the desired behavior.\n\n2. For each field, indicate the `value type` of the desired output. Besides basic types like strings, dates, and numbers, you can define more complex structures such as `tables` (repeated items with subfields) and `fixed tables` (groups of fields with common subfields)."
CU_LABEL_SCHEMA = f"https://schema.ai.azure.com/mmi/{CU_API_VERSION}/labels.json"

def convert_bounding_regions_to_source(page_number: int, polygon: list) -> str:
    """
    Convert bounding regions (DI) to source string (CU) format.
    Args:
        page_number (int): The page number.
        polygon (list): The polygon coordinates.
    Returns:
        str: The source string in the format D(page_number, x1,y1,x2,y2,...).
    """
    # Convert polygon to string format
    polygon_str = ",".join(str(coord) for coord in polygon)
    source = f"D({page_number},{polygon_str})"
    return source

def format_angle(angle: float) -> float:
   """
   Format the angle to 7 decimal places and remove trailing zeros.
    Args:
       angle (float): The angle to format.
    Returns:
       float: The formatted angle.
   """
   rounded_angle = round(angle, 7)
   formatted_num = f"{rounded_angle:.7f}".rstrip('0')  # Remove trailing zeros
   return float(formatted_num)

def convert_fields_to_analyzer(fields_json_path: Path, analyzer_prefix: Optional[str], target_dir: Path, field_definitions: FieldDefinitions) -> dict:
    """
    Convert DI 4.0 preview Custom Document fields.json to analyzer.json format.
    Args:
        fields_json_path (Path): Path to the input DI fields.json file.
        analyzer_prefix (Optional(str)): Prefix for the analyzer name.
        target_dir (Optional[Path]): Output directory for the analyzer.json file.
        field_definitions (FieldDefinitions): Field definitions object to store definitions in case of fixed tables.
    Returns:
        dict: The generated analyzer.json data.
    """
    try:
        with open(fields_json_path, 'r') as f:
            fields_data = json.load(f)
    except FileNotFoundError:
        print(f"[red]Error: fields.json file not found at {fields_json_path}.[/red]")
        sys.exit(1)
    except json.JSONDecodeError:
        print("[red]Error: Invalid JSON in fields.json.[/red]")
        sys.exit(1)

    doc_type = fields_data.get('docType')

    field_definitions.clear_definitions()

    # Build analyzer.json content
    analyzer_id = f"{analyzer_prefix}_{doc_type}" if analyzer_prefix else doc_type

    # build analyzer.json appropriately
    analyzer_data = {
        "analyzerId": analyzer_id,
        "baseAnalyzerId": "prebuilt-documentAnalyzer",
        "config": {
            "returnDetails": True,
            # Add the following line as a temp workaround before service issue is fixed.
            "enableLayout": True,
            "enableBarcode": False,
            "enableFormula": False,
            "estimateFieldSourceAndConfidence": True
        },
        ANALYZER_FIELDS: {
            "name": doc_type,
            "description": ANALYZER_DESCRIPTION,
            "fields": {},
            "definitions": {}
        },
        "warnings": fields_data.get("warnings", []),
        "status": fields_data.get("status", "undefined"),
        "templateId": fields_data.get("templateId", "document-2024-12-01")
    }

    # Update field schema to be in CU format
    fields = fields_data.get(ANALYZER_FIELDS, {})
    if (len(fields) == 0):
        print("[red]Error: Fields.json should not be empty.[/red]")
        sys.exit(1)
    for key, value in fields.items():
        if len(key) > MAX_FIELD_LENGTH:
            print(f"[red]Error: Field key '{key}' contains {len(key)}, which exceeds the limit of {MAX_FIELD_LENGTH} characters. [/red]")
            sys.exit(1)
        analyzer_field = recursive_convert_field_to_analyzer_helper(key, value, field_definitions)

        # Add field to fieldLabels
        analyzer_data[ANALYZER_FIELDS]["fields"][key] = analyzer_field

    # Update defintions accordingly
    analyzer_data[ANALYZER_FIELDS]["definitions"] = field_definitions.get_all_definitions()
    # Determine output path
    if target_dir:
        analyzer_json_path = target_dir / 'analyzer.json'
    else:
        analyzer_json_path = fields_json_path.parent / 'analyzer.json'

    # Ensure target directory exists
    analyzer_json_path.parent.mkdir(parents=True, exist_ok=True)

    # Write analyzer.json
    with open(analyzer_json_path, 'w') as f:
        json.dump(analyzer_data, f, indent=4)

    print(f"[green]Successfully converted {fields_json_path} to analyzer.json at {analyzer_json_path}[/green]\n")
    return analyzer_data

def recursive_convert_field_to_analyzer_helper(key: str, value: dict, field_definitions: FieldDefinitions) -> dict:
    """
    Recursively convert each DI field to CU analyzer.json format
    Args:
        key (str): The field key.
        value (dict): The field value.
        field_definitions (FieldDefinitions): Field definitions object that stores definitions in case of fixed tables.
    Returns:
        dict: The converted field in analyzer.json format.
    """
    # this is the method that does the conversion of the fields itself

    analyzer_field = {
        "type": value.get("type"),
        "method": "extract",
    }

    if value.get("type") == "array":
        analyzer_field["method"] = value.get("method", "generate")
        analyzer_field["description"] = value.get("description", "")
        analyzer_field["items"] = recursive_convert_field_to_analyzer_helper(key, value.get("items"), field_definitions)
    elif value.get("type") == "object":
        # if the properties are objects, this is a fixed sized table
        # if the properties are not objects, this is a dynamic sized table
        fixed_table = False
        first_value = next(iter(value.get("properties").values()))
        if(first_value.get("type") == "object"):
            fixed_table = True
            analyzer_field["description"] = value.get("description", "")
        analyzer_field["properties"] = {}

        if not fixed_table:
            for i, (key, item) in enumerate(value.get("properties").items()):
                analyzer_field["properties"][key] = recursive_convert_field_to_analyzer_helper(key, item, field_definitions)
        else:
            analyzer_field["method"] = value.get("method", "generate")
            first_row_key = "" # only need to use the first row for creating a definition, since the rest will be the same as it is a fixed table
            for i, (row_key, row_item) in enumerate(value.get("properties").items()):
                if i == 0:
                    first_row_key = row_key
                    definitions_key = f"{key}_{row_key}"
                    if len(definitions_key) > MAX_FIELD_LENGTH:
                        print(f"[red]Error: The fixed table definition '{definitions_key}' will contain {len(definitions_key)}, which exceeds the limit of {MAX_FIELD_LENGTH} characters. Please shorten either the table name or row name. [/red]")
                        sys.exit(1)
                    # need to add methods to all the columns
                    for property_key, property_data in row_item["properties"].items():
                        if property_data.get("method") is None:
                            property_data["method"] = "extract"
                        if property_data.get("description") is None:
                            property_data["description"] = ""
                    definitions_value = row_item
                    field_definitions.add_definition(definitions_key, definitions_value)
                analyzer_field["properties"][row_key] = {}
                analyzer_field["properties"][row_key]["$ref"] = f"#/$defs/{key}_{first_row_key}"

    else:
        analyzer_field["description"] = value.get("description", "")

    return analyzer_field

def convert_di_labels_to_cu(di_labels_path: Path, target_dir: Path) -> None:
    """
    Convert DI 4.0 preview Custom Document format labels.json to Content Understanding format labels.json.
    Args:
        di_labels_path (Path): Path to the Document Intelligence labels.json file.
        target_dir (Path): Output directory for the Content Understanding labels.json file.
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

    field_labels = di_data.get("fieldLabels", {})
    for key, value in field_labels.items():
        cu_field = recursive_convert_di_label_to_cu_helper(value)

        # Include original label in metadata

        # Add field to fieldLabels
        cu_data["fieldLabels"][key] = cu_field

    # Write Content Understanding labels.json
    target_dir.mkdir(parents=True, exist_ok=True)
    cu_labels_path = target_dir / di_labels_path.name

    with open(cu_labels_path, 'w') as f:
        json.dump(cu_data, f, indent=4, ensure_ascii=False)

    print(f"[green]Successfully converted Document Intelligence labels.json to Content Understanding labels.json at {cu_labels_path}[/green]\n")

def recursive_convert_di_label_to_cu_helper(value: dict) -> dict:
    """
    Recursively convert each DI field to CU labels.json format
    Args:
        value (dict): The field value.
    Returns:
        dict: The converted field in labels.json format.
    """
    
    value_type = value.get("type")
    if(value_type not in VALID_CU_FIELD_TYPES and value_type != "selectionMark"):
        print(f"[red]Unexpected field type: {value_type}. Please refer to the specification for valid field types.[/red]")
        sys.exit(1)

    di_label = {
        "type": value_type
    }

    if value_type == "array":
        value_array = value.get("valueArray")
        di_label["kind"] = value.get("kind", "confirmed")
        di_label["valueArray"] = value_array
        for i, item in enumerate(value_array):
            value_array[i] = recursive_convert_di_label_to_cu_helper(item)
    elif value_type == "object":
        value_object = value.get("valueObject")
        di_label["kind"] = value.get("kind", "confirmed")
        di_label["valueObject"] = value_object
        for i, item in value_object.items():
            value_object[i] = recursive_convert_di_label_to_cu_helper(item)
    else:
        value_part = VALID_CU_FIELD_TYPES[value_type]
        if value.get(value_part) is not None and value.get(value_part) != "":
            di_label[value_part] = value.get(value_part)
        else:
            if value_type == "date":
                date_string = value.get("content")
                formats_to_try = ["%B %d,%Y", "parse", "%B %d, %Y", "%m/%d/%Y"]
                finished_date_normalization = False # to keep track of whether we have finished normalizing the date, if not, date will be set to originalDate
                for fmt in formats_to_try:
                    try:
                        if fmt == "parse":
                            di_label["valueDate"] = parse(date_string).date().strftime("%Y-%m-%d")
                        else:
                            date_obj = datetime.strptime(date_string, fmt)
                            di_label["valueDate"] = date_obj.strftime("%Y-%m-%d")
                        finished_date_normalization = True
                    except Exception as ex:
                        continue
                if not finished_date_normalization:
                    di_label["valueDate"] = date_string # going with the default
            elif value_type == "number":
                try:
                    di_label["valueNumber"] = float(value.get("content"))  # content can be easily converted to a float
                except Exception as ex:
                    # strip the string of all non-numerical values and periods
                    string_value = value.get("content")
                    cleaned_string = re.sub(r'[^0-9.]', '', string_value)
                    cleaned_string = cleaned_string.strip('.')  # Remove any leading or trailing periods
                    # if more than one period exists, remove them all
                    if cleaned_string.count('.') > 1:
                        print("More than one decimal point exists, so will be removing them all.")
                        cleaned_string = cleaned_string = re.sub(r'\.', '', string_value)
                    di_label["valueNumber"] = float(cleaned_string)
            elif value_type == "integer":
                try:
                    di_label["valueInteger"] = int(value.get("content"))  # content can be easily converted to an int
                except Exception as ex:
                     # strip the string of all non-numerical values
                    string_value = value.get("content")
                    cleaned_string = re.sub(r'[^0-9]', '', string_value)
                    di_label["valueInteger"] = int(cleaned_string)
            else:
                di_label[value_part] = value.get("content")
        di_label["spans"] = value.get("spans", [])

    if(value.get("kind", "confirmed") == "confirmed" and di_label["type"] != "array" and di_label["type"] != "object"):
        # Copy confidence if present
        di_label["confidence"] = value.get("confidence", None)

     # Convert boundingRegions to source
    bounding_regions = value.get("boundingRegions", [])
    sources = []
    for region in bounding_regions:
        page_number = region.get("pageNumber")
        polygon = region.get("polygon")
        if page_number is None or polygon is None:
            continue
        # Convert polygon to string format
        source = convert_bounding_regions_to_source(page_number, polygon)
        sources.append(source)
    if sources:
        di_label["source"] = ";".join(sources)

    if(value.get("type") != "array" and value.get("type") != "object"):
        di_label["kind"] = value.get("kind", "confirmed")
        di_label["metadata"] = value.get("metadata", {})

    return di_label

def convert_ocr_to_result(di_ocr_path: Path, target_dir: Path) -> None:
    """
    Convert Document Intelligence format ocr.json to Content Understanding format result.json
    Args:
        di_ocr_path (Path): Path to the Document Intelligence ocr.json file.
        target_dir (Path): Output directory for the Content Undrestanding result.json file.
    """
    try:
        with open(di_ocr_path, 'r', encoding="utf-8") as f:
            ocr_data = json.load(f)
    except FileNotFoundError:
        print(f"[red]Error: Document Intelligence ocr.json file not found at {di_ocr_path}.[/red]")
        sys.exit(1)
    except json.JSONDecodeError:
        print("[red]Error: Invalid JSON in Document Intelligence ocr.json.[/red]")
        sys.exit(1)

    # Start building Content Understanding results.json
    cu_results_data = {
        "id": ocr_data.get("id", ""),
        "status": (ocr_data.get("status", "")).capitalize(),
        "result": {}
    }

    # Setting up the result section
    di_results = ocr_data.get("analyzeResult")
    cu_results_data["result"]["analyzerId"] = di_results["modelId"]
    cu_results_data["result"]["apiVersion"] = CU_API_VERSION
    cu_results_data["result"]["createdAt"] = ocr_data.get("createdDateTime", "")
    if ocr_data.get("warnings") is not None:
        cu_results_data["result"]["warnings"] = ocr_data.get("warnings")

    # Setting up the contents subsection within result section
    cu_results_data["result"]["contents"] = [{}]
    cu_results_data["result"]["contents"][0]["markdown"] = di_results["content"]
    cu_results_data["result"]["contents"][0]["kind"] = di_results.get("kind", "document")
    cu_results_data["result"]["contents"][0]["startPageNumber"] = di_results["pages"][0]["pageNumber"]
    cu_results_data["result"]["contents"][0]["endPageNumber"] = di_results["pages"][-1]["pageNumber"]
    cu_results_data["result"]["contents"][0]["unit"] = di_results["pages"][0].get("unit", "inch")

    # Configuring pages
    if (di_results.get("pages") is not None):
        cu_results_data["result"]["contents"][0]["pages"] = []
        for page in di_results["pages"]:
            cu_page = {
                "pageNumber": page["pageNumber"],
                "angle": format_angle(page["angle"]),
                "width": page["width"],
                "height": page["height"],
                "spans": page["spans"],
                "words": [],
                "lines": []
            }
            if(page.get("selectionMarks") is not None):
                cu_page["selectionMarks"] = page.get("selectionMarks")
            for word in page["words"]:
                cu_word = {
                    "content": word["content"],
                    "span": word["span"],
                    "confidence": word["confidence"],
                    "source": convert_bounding_regions_to_source(page['pageNumber'], word['polygon']) # map str function to each element in polygon and then joins it all together with ,
                }
                cu_page["words"].append(cu_word)
            for line in page["lines"]:
                cu_line = {
                    "content": line["content"],
                    "source": convert_bounding_regions_to_source(page['pageNumber'], line['polygon']), # map str function to each element in polygon and then joins it all together with ,
                }
                if len(line["spans"]) == 1:
                    cu_line["span"] = line["spans"][0]
                else:
                    # If mulitple spans, offset becomes the lowest offset
                    # and length becomes max offset + length of max offset - min offset
                    min_offset = min([span["offset"] for span in line["spans"]])
                    max_offset = max([span["offset"] for span in line["spans"]])
                    max_length = next(span for span in line["spans"] if span["offset"] == max_offset)["length"]
                    cu_line["span"] = {
                        "offset": min_offset,
                        "length": max_offset + max_length - min_offset
                    }
                cu_page["lines"].append(cu_line)
            cu_results_data["result"]["contents"][0]["pages"].append(cu_page)

    # Configuring paragraphs
    if (di_results.get("paragraphs") is not None):
        cu_results_data["result"]["contents"][0]["paragraphs"] = []
        for paragraph in di_results["paragraphs"]:
            cu_paragraph = {
                "role": paragraph.get("role", ""),
                "content": paragraph["content"],
                "source": paragraph.get("boundingRegions", None),
                "span": paragraph["spans"][0]
            }
            if (cu_paragraph["source"] is not None):
                cu_paragraph["source"] = convert_bounding_regions_to_source(paragraph['boundingRegions'][0]['pageNumber'], paragraph['boundingRegions'][0]['polygon'])
            else:
                del cu_paragraph["source"]
            if (cu_paragraph["role"] == ""):
                del cu_paragraph["role"]
            cu_results_data["result"]["contents"][0]["paragraphs"].append(cu_paragraph)

    # Configuring sections
    if (di_results.get("sections") is not None):
        cu_results_data["result"]["contents"][0]["sections"] = []
        for section in di_results["sections"]:
            cu_section = {
                "span": section["spans"][0],
                "elements": section["elements"]
            }
            cu_results_data["result"]["contents"][0]["sections"].append(cu_section)

    # Configuring tables
    if (di_results.get("tables") is not None):
        cu_results_data["result"]["contents"][0]["tables"] = []
        for table in di_results["tables"]:
            cu_table = {
                "rowCount": table["rowCount"],
                "columnCount": table["columnCount"],
                "cells": [],
            }
             # Convert boundingRegions to source for cross page tables
            sources = []
            for region in table.get("boundingRegions"):
                page_number = region.get("pageNumber")
                polygon = region.get("polygon")
                if page_number is None or polygon is None:
                    continue
                # Convert polygon to string format
                source = convert_bounding_regions_to_source(page_number, polygon)
                sources.append(source)

            if sources:
                cu_table["source"] = ";".join(sources)

            cu_table["span"] = table["spans"][0]

            # if table has a caption
            if table.get("caption") is not None:
                caption = table.get("caption")
                cu_caption = {
                    "content": caption.get("content", ""),
                    "source":convert_bounding_regions_to_source(caption["boundingRegions"][0]['pageNumber'], caption['boundingRegions'][0]['polygon']),
                    "span": caption["spans"][0],
                    "elements": caption.get("elements", [])
                }
                cu_table["caption"] = cu_caption

            # if table has a footnotes --> multiple
            if table.get("footnotes") is not None:
                footnotes= table.get("footnotes")
                cu_footnotes = []
                for footnote in footnotes:
                    cu_footnote = {
                        "content": footnote["content"],
                        "source": convert_bounding_regions_to_source(footnote["boundingRegions"][0]['pageNumber'], footnote['boundingRegions'][0]['polygon']),
                        "span": footnote["spans"][0],
                        "elements": footnote.get("elements", [])
                    }
                    cu_footnotes.append(cu_footnote)
                cu_table["footnotes"] = cu_footnotes

            for cell in table["cells"]:
                cu_cell = {
                    "kind": cell.get("kind", "content"),
                    "rowIndex": cell["rowIndex"],
                    "columnIndex": cell["columnIndex"],
                    "rowSpan": cell.get("rowSpan", 1),
                    "columnSpan": cell.get("columnSpan", 1),
                    "content": cell["content"],
                    "source": convert_bounding_regions_to_source(cell['boundingRegions'][0]['pageNumber'], cell['boundingRegions'][0]['polygon']),
                }

                # sometimes spans is empty
                if (len(cell["spans"]) == 0):
                    cu_cell["span"] = []
                else:
                    cu_cell["span"] = cell["spans"][0]

                # sometimes elements doesn't exist if content isn't blank
                if (cell.get("elements") is not None):
                    cu_cell["elements"] = cell["elements"]
                cu_table["cells"].append(cu_cell)
            cu_results_data["result"]["contents"][0]["tables"].append(cu_table)

    # Configuring figures
    if (di_results.get("figures") is not None):
        cu_results_data["result"]["contents"][0]["figures"] = []
        for figure in di_results["figures"]:
            if(figure.get("elements") is not None): # using if block to keep the same order as CU
                cu_figure = {
                    "source": convert_bounding_regions_to_source(figure['boundingRegions'][0]['pageNumber'], figure['boundingRegions'][0]['polygon']),
                    "span": figure["spans"][0],
                    "elements": figure["elements"],
                    "id": figure.get("id", "")
                }
            else:
                cu_figure = {
                    "source": convert_bounding_regions_to_source(figure['boundingRegions'][0]['pageNumber'], figure['boundingRegions'][0]['polygon']),
                    "span": figure["spans"][0],
                    "id": figure.get("id", "")
                }
            cu_results_data["result"]["contents"][0]["figures"].append(cu_figure)

    # Write Content Understanding results.json
    target_dir.mkdir(parents=True, exist_ok=True)
    new_path_name = di_ocr_path.name.replace('.ocr', '.result')
    cu_results_path = target_dir / new_path_name

    with open(cu_results_path, 'w') as f:
        json.dump(cu_results_data, f, indent=4,ensure_ascii=False)

    print(f"[green]Successfully converted Document Intelligence ocr.json to Content Understanding results.json at {cu_results_path}[/green]\n")
