# Supported DI versions
DI_VERSIONS = ["generative", "neural"]
CU_API_VERSION = "2025-05-01-preview"

# constants
MAX_FIELD_COUNT = 100
MAX_FIELD_LENGTH = 64

# standard file names
FIELDS_JSON = "fields.json"
LABELS_JSON = ".labels.json"
VALIDATION_TXT = "validation.txt"
PDF = ".pdf"
OCR_JSON = ".ocr.json"

# for field type conversion
SUPPORT_FIELD_TYPE = [
    "string",
    "number",
    "integer",
    "array",
    "object",
    "date",
    "time",
    "boolean",
]

CONVERT_TYPE_MAP = {
    "selectionMark": "boolean",
    "currency": "number",
}

FIELD_VALUE_MAP = {
    "number": "valueNumber",
    "integer": "valueInteger",
    "date": "valueDate",
    "time": "valueTime",
    "selectionMark": "valueSelectionMark",
    "address": "valueAddress",
    "phoneNumber": "valuePhoneNumber",
    "currency": "valueCurrency",
    "string": "valueString",
    "boolean": "valueBoolean",
}

CHECKED_SYMBOL = "☒"
UNCHECKED_SYMBOL = "☐"

# for CU conversion
# spec for valid field types
VALID_CU_FIELD_TYPES = {
    "string": "valueString",
    "date": "valueDate",
    "phoneNumber": "valuePhoneNumber",
    "integer": "valueInteger",
    "number": "valueNumber",
    "array": "valueArray",
    "object": "valueObject",
    "boolean": "valueBoolean",
    "time": "valueTime",
    "selectionMark": "valueSelectionMark" # for DI only
}

DATE_FORMATS_SLASHED = ["%d/%m/%y", "%m/%d/%y", "%y/%m/%d","%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"] # %Y is for 4-year format (Ex: 2015) and %y is for 2-year format (Ex: 15)
DATE_FORMATS_DASHED = ["%d-%m-%y", "%m-%d-%y", "%y-%m-%d","%d-%m-%Y", "%m-%d-%Y", "%Y-%m-%d"] # can have dashes, instead of slashes
COMPLETE_DATE_FORMATS = DATE_FORMATS_SLASHED + DATE_FORMATS_DASHED # combine the two formats
