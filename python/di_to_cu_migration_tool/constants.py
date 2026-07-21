# Supported DI custom model types
DI_MODEL_TYPES = ["generative", "neural"]
CU_API_VERSION = "2025-11-01"

# Models
COMPLETION_DEPLOYMENT = "gpt-4.1"
EMBEDDING_DEPLOYMENT = "text-embedding-3-large"

# constants
MAX_FIELD_COUNT = 100
MAX_FIELD_LENGTH = 64
# Valid field name pattern for Content Understanding API
VALID_FIELD_NAME_PATTERN = r'^[a-zA-Z_][a-zA-Z0-9_]{0,63}$'

# standard file names
FIELDS_JSON = "fields.json"
ANALYZER_JSON = "analyzer.json"
LABELS_JSON = ".labels.json"
VALIDATION_TXT = "validation.txt"
PDF = ".pdf"
OCR_JSON = ".ocr.json"
RESULT_JSON = ".result.json"

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

# Map from DI-only field types to their CU-supported equivalents.
# CU's ContentFieldType only supports: string, date, time, number, integer, boolean, array, object.
# All other DI types (selectionMark, currency, phoneNumber, address, signature) must be coerced
# to a supported type before the analyzer/labels are emitted.
CONVERT_TYPE_MAP = {
    "selectionMark": "boolean",
    "currency": "number",
    "phoneNumber": "string",  # CU has no phoneNumber type
    "address": "string",      # CU has no address type
}

# Map from DI field types to their DI value-key names. Used to strip DI-specific
# value keys (e.g., valuePhoneNumber, valueAddress) from labels during type coercion.
# Do not treat this as the CU spec; see VALID_CU_FIELD_TYPES for that.
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
# spec for valid CU field types. phoneNumber and address are intentionally omitted
# because CU's ContentFieldType union does not include them; they must be coerced
# to "string" via CONVERT_TYPE_MAP before emission.
VALID_CU_FIELD_TYPES = {
    "string": "valueString",
    "date": "valueDate",
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

# Time formats DI may produce. CU requires ISO 8601 hh:mm:ss.
# The first format that parses wins; dateutil.parser is used as a final fallback.
TIME_FORMATS = [
    "%H:%M:%S",     # 15:30:45 (already ISO)
    "%H:%M",        # 15:30
    "%I:%M:%S %p",  # 03:30:45 PM
    "%I:%M %p",     # 03:30 PM
    "%I %p",        # 3 PM
    "%H:%M:%S.%f",  # 15:30:45.123
]
