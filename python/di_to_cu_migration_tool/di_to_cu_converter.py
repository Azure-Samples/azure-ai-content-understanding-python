# imports from built-in packages
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobClient, ContainerClient
from dotenv import load_dotenv
import json
import os
from pathlib import Path
import shutil
import tempfile
import typer
from typing import Tuple

# imports from external packages (in requirements.txt)
from rich import print  # For colored output

# imports from same project
from constants import DI_VERSIONS, FIELDS_JSON, LABELS_JSON, MAX_FIELD_COUNT, OCR_JSON, VALIDATION_TXT
import cu_converter_neural as cu_converter_neural
import cu_converter_generative as cu_converter_generative
from field_definitions import FieldDefinitions
import field_type_conversion
from get_ocr import run_cu_layout_ocr

app = typer.Typer()

def validate_field_count(DI_version, byte_fields) -> Tuple[int, bool]:
    """
    Function to check if the fields.json is valid
    Checking to see if the number of fields is less than or equal to 100
    Args:
        DI_version (str): The version of DI being used
        byte_fields (bytes): The fields.json file in bytes
    Returns:
        field_count (int): The number of fields in the fields.json file
        is_valid (bool): True if the fields.json file is valid, False otherwise
    """
    string_fields = byte_fields.decode("utf-8")
    fields = json.loads(string_fields)

    field_count = 0
    if DI_version == "generative":
        field_schema = fields["fieldSchema"]
        if len(field_schema) > MAX_FIELD_COUNT:
            return len(field_schema), False
        for _, field in field_schema.items(): # need to account for tables
            if field["type"] == "array":
                field_count += (len(field["items"]["properties"]) + 1)
            elif field["type"] == "object":
                number_of_rows = len(field["properties"])
                _, first_row_value = next(iter(field["properties"].items()))
                number_of_columns = len(first_row_value["properties"])
                field_count += (number_of_rows + number_of_columns + 2)
            else:
                field_count += 1 # need to account for other primitive fields
        if field_count > MAX_FIELD_COUNT:
            return field_count, False
    else: # DI 3.1/4.0 GA Custom Neural
        field_schema = fields["fields"]
        definitions = fields["definitions"]
        if len(fields) > MAX_FIELD_COUNT:
            return len(fields), False
        for field in field_schema:
            if field["fieldType"] == "array":
                definition = definitions[field["itemType"]]
                field_count += (len(definition["fields"]) + 1)
            elif field["fieldType"] == "object":
                number_of_rows = len(field["fields"])
                row_definition = field["fields"][0]["fieldType"]
                definition = definitions[row_definition]
                number_of_columns = len(definition["fields"])
                field_count += (number_of_rows + number_of_columns + 2)
            elif field["fieldType"] == "signature":
                continue # will be skipping over signature fields anyways, shouldn't add to field count
            else:
                field_count += 1 # need to account for other primitive fields
        if field_count > MAX_FIELD_COUNT:
            return field_count, False
    print(f"[green]Successfully validated fields.json. Number of fields: {field_count}[/green]")
    return field_count, True

@app.command()
def main(
    analyzer_prefix: str = typer.Option("", "--analyzer-prefix", help="Prefix for analyzer name."),
    DI_version: str = typer.Option("generative", "--DI-version", help="DI versions: generative, neural"),
    source_container_sas_url: str = typer.Option("", "--source-container-sas-url", help="Source blob container SAS URL."),
    source_blob_folder: str = typer.Option("", "--source-blob-folder", help="Source blob storage folder prefix."),
    target_container_sas_url: str = typer.Option("", "--target-container-sas-url", help="Target blob container SAS URL."),
    target_blob_folder: str = typer.Option("", "--target-blob-folder", help="Target blob storage folder prefix."),
) -> None:
    """
    Wrapper tool to convert an entire DI dataset to CU format
    """

    assert DI_version in DI_VERSIONS, f"Please provide a valid DI version out of {DI_VERSIONS}."
    assert source_container_sas_url != "" and target_container_sas_url != "", "Please provide a valid source and target blob container SAS URL."
    assert source_blob_folder != "", "Please provide a valid source blob storage folder prefix to specify your DI dataset name."
    assert target_blob_folder != "", "Please provide a valid target blob storage folder prefix to specify your CU dataset name."

    print(f"[yellow]You have specified the following DI version: {DI_version} out of {DI_VERSIONS}.If this is not expected, feel free to change this with the --DI-version parameter.\n[/yellow]")

    # if DI_version 3.1/4.0 GA Custom Neural, then analyzer prefix needs to be set
    if DI_version == "neural":
        assert analyzer_prefix != "", "Please provide a valid analyzer prefix, since you are using DI 3.1/4.0 GA Custom Neural."

    # Getting the environmental variables
    load_dotenv()
    subscription_key = os.getenv("SUBSCRIPTION_KEY")

    print("Creating a temporary directory for storing source blob storage content...")
    temp_source_dir = Path(tempfile.mkdtemp())
    temp_target_dir = Path(tempfile.mkdtemp())

    # Configure access to source blob storage
    container_client = ContainerClient.from_container_url(source_container_sas_url)

    # List of blobs under the "folder" in source
    blob_list = container_client.list_blobs(name_starts_with=source_blob_folder)

    for blob in blob_list: # each file is a blob that's being read into local directory
        print(f"Reading: {blob.name}")
        blob_client = container_client.get_blob_client(blob.name)
        content = blob_client.download_blob().readall()

        # Create local file path (preserving folder structure)
        filename = Path(blob.name).name
        local_file_path = temp_source_dir /filename
        local_file_path.parent.mkdir(parents=True, exist_ok=True)

        if filename == FIELDS_JSON:
            print(f"[yellow]Checking if fields.json is valid for being able to create an analyzer.[/yellow]")
            fields_count, is_valid = validate_field_count(DI_version, content)
            assert is_valid, f"Too many fields in fields.json, we only support up to {MAX_FIELD_COUNT} fields. Right now, you have {fields_count} fields."

        # Write to file
        with open(local_file_path, "wb") as f:
            f.write(content)
            print(f"Writing to {local_file_path}")

    # Confirming access to target blob storage here because doing so before can cause SAS token to expire
    # Additionally, best to confirm access to target blob storage before running any conversion
    target_container_client = ContainerClient.from_container_url(target_container_sas_url)

    # First need to run field type conversion --> Then run DI to CU conversion
    # Creating a temporary directory to store field type converted dataset
    # Without this temp directory, your ocr.json files will not be carried over for cu conversion
    # DI dataset converter will use temp directory as its source
    # TO DO: remove the instance of temp_dir all together and rely on source_target_dir for field type conversion only
    temp_dir = Path(tempfile.mkdtemp())

    for item in temp_source_dir.iterdir():
        shutil.copy2(item, temp_dir / item.name)

    print(f"Creating temporary directory for running valid field type conversion. Output will be temporary stored at {temp_dir}...")

    print("First: Running valid field type conversion...")
    print("[yellow]WARNING: if any signature fields are present, they will be skipped...[/yellow]\n")
    # Taking the input source dir, and converting the valid field types into temp_dir
    removed_signatures = running_field_type_conversion(temp_source_dir, temp_dir, DI_version)

    if len(removed_signatures) > 0:
        print(f"[yellow]WARNING: The following signatures were removed from the dataset: {removed_signatures}[/yellow]\n")

    print("Second: Running DI to CU dataset conversion...")
    analyzer_data, ocr_files = running_cu_conversion(temp_dir, temp_target_dir, DI_version, analyzer_prefix, removed_signatures)

    # Run OCR on the pdf files
    run_cu_layout_ocr(ocr_files, temp_target_dir, subscription_key)
    print(f"[green]Successfully finished running CU Layout on all PDF files[/green]\n")

    # After processing files in temp_target_dir
    print("Uploading contents of temp_target_dir to target blob storage...")

    for item in temp_target_dir.rglob("*"):  # Recursively iterate through all files and directories
        if item.is_file():  # Only upload files
            # Create the blob path by preserving the relative path structure
            blobPath = str(item.relative_to(temp_target_dir)).replace('\\', '/') # Ensure path uses forward slashes
            blob_path = target_blob_folder + "/" + blobPath
            print(f"Uploading {item} to blob path {blob_path}...")

            # Create a BlobClient for the target blob
            blob_client = target_container_client.get_blob_client(blob_path)

            # Upload the file
            with open(item, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)

    print("[green]Successfully uploaded all files to target blob storage.[/green]")

def running_field_type_conversion(temp_source_dir: Path, temp_dir: Path, DI_version: str) -> list:
    """
    Function to run the field type conversion
    Args:
        temp_source_dir (Path): The path to the source directory
        temp_dir (Path): The path to the target directory
        DI_version (str): The version of DI being used
    Returns:
        removed_signatures (list): The list of removed signatures as they will not be used in the CU converter
    """
    # Taking the input source dir, and converting the valid field types into temp_dir
    for root, dirs, files in os.walk(temp_source_dir):
        root_path = Path(root)
        fields_path = root_path / FIELDS_JSON

        converted_fields = {}
        converted_field_keys = {}
        removed_signatures = []

        assert fields_path.exists(), "fields.json is needed. Fields.json is missing from the given dataset."
        with fields_path.open("r", encoding="utf-8") as fp: # running field type conversion for fields.json
            fields = json.load(fp)

        if DI_version == "generative":
            converted_fields, converted_field_keys = field_type_conversion.update_unified_schema_fields(fields)
            with open(str(temp_dir / FIELDS_JSON), "w", encoding="utf-8") as fp:
                json.dump(converted_fields, fp, ensure_ascii=False, indent=4)
            print("[yellow]Successfully handled field type conversion for DI 4.0 preview Custom Document fields.json[/yellow]\n")
        elif DI_version == "neural":
            removed_signatures, converted_fields = field_type_conversion.update_fott_fields(fields)
            with open(str(temp_dir / FIELDS_JSON), "w", encoding="utf-8") as fp:
                json.dump(converted_fields, fp, ensure_ascii=False, indent=4)
            print("[yellow]Successfully handled field type conversion for DI 3.1/4.0 GA Custom Document fields.json[/yellow]\n")

        if DI_version == "generative":
            for file in files:
                file_path = root_path / file
                if (file.endswith(LABELS_JSON)):
                    # running field type conversion for labels.json
                    with file_path.open("r", encoding="utf-8") as fp:
                        labels = json.load(fp)
                    field_type_conversion.update_unified_schema_labels(labels, converted_field_keys, temp_dir / file)
                    print(f"[yellow]Successfully handled field type conversion for {file}[/yellow]\n")

    return removed_signatures

def running_cu_conversion(temp_dir: Path, temp_target_dir: Path, DI_version: str, analyzer_prefix: str, removed_signatures: list) -> Tuple[dict, list]:
    """
    Function to run the DI to CU conversion
    Args:
        temp_dir (Path): The path to the source directory
        temp_target_dir (Path): The path to the target directory
        DI_version (str): The version of DI being used
        analyzer_prefix (str): The prefix for the analyzer name
        removed_signatures (list): The list of removed signatures that will not be used in the CU converter
    """
    # Creating a FieldDefinitons object to handle the converison of definitions in the fields.json
    field_definitions = FieldDefinitions()
    for root, dirs, files in os.walk(temp_dir):
        root_path = Path(root)  # Convert root to Path object for easier manipulation
        # Converting fields to analyzer
        fields_path = root_path / FIELDS_JSON

        assert fields_path.exists(), "fields.json is needed. Fields.json is missing from the given dataset."
        if DI_version == "generative":
            analyzer_data = cu_converter_generative.convert_fields_to_analyzer(fields_path, analyzer_prefix, temp_target_dir, field_definitions)
        elif DI_version == "neural":
            analyzer_data, fields_dict = cu_converter_neural.convert_fields_to_analyzer_neural(fields_path, analyzer_prefix, temp_target_dir, field_definitions)

        ocr_files = [] # List to store paths to pdf files to get OCR results from later
        for file in files:
            file_path = root_path / file
            if (file_path.name == FIELDS_JSON or file_path.name == VALIDATION_TXT):
                continue
            # Converting DI labels to CU labels
            if (file.endswith(LABELS_JSON)):
                if DI_version == "generative":
                    cu_converter_generative.convert_di_labels_to_cu(file_path, temp_target_dir)
                elif DI_version == "neural":
                    cu_labels = cu_converter_neural.convert_di_labels_to_cu_neural(file_path, temp_target_dir, fields_dict, removed_signatures)
                    # run field type conversion of label files here, because will be easier after getting it into CU format
                    field_type_conversion.update_fott_labels(cu_labels, temp_target_dir / file_path.name)
                    print(f"[green]Successfully converted Document Intelligence labels.json to Content Understanding labels.json at {temp_target_dir/file_path.name}[/green]\n")
            elif not file.endswith(OCR_JSON): # skipping over .orc.json files
                shutil.copy(file_path, temp_target_dir) # Copying over main file
                ocr_files.append(file_path) # Adding to list of files to run OCR on
    return analyzer_data, ocr_files

if __name__ == "__main__":
    app()

