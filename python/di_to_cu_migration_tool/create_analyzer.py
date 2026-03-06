# imports from built-in packages
import json
import os
import typer

# imports from external packages (in requirements.txt)
from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobClient
from dotenv import load_dotenv
from rich import print  # For colored output

app = typer.Typer()

@app.command()
def main(
    analyzer_sas_url: str = typer.Option("", "--analyzer-sas-url", help="SAS URL for the created analyzer.json"),
    target_container_sas_url: str = typer.Option("", "--target-container-sas-url", help="Target blob container SAS URL."),
    target_blob_folder: str = typer.Option("", "--target-blob-folder", help="Target blob storage folder prefix."),
):
    """
    Main function to create the CU analyzer using the Content Understanding Python SDK.
    """
    assert analyzer_sas_url != "", "Please provide the SAS URL for the created CU analyzer.json so we are able to call the Build Analyzer API"
    assert target_container_sas_url != "", "Please provide the SAS URL for the target blob container so we are able to refer to the created CU dataset"
    assert target_blob_folder != "", "Please provide the target blob folder so we are able to refer to the created CU dataset"

    # Load the analyzer.json file from blob storage
    print(f"Loading analyzer.json from...")
    blob_client = BlobClient.from_blob_url(analyzer_sas_url)
    analyzer_json = blob_client.download_blob().readall()
    analyzer_json = analyzer_json.decode("utf-8")
    analyzer_json = json.loads(analyzer_json)
    print("[yellow]Finished loading analyzer.json.[/yellow]\n")

    # Set up credentials and client
    load_dotenv()
    endpoint = os.environ["CONTENTUNDERSTANDING_ENDPOINT"]
    key = os.getenv("CONTENTUNDERSTANDING_KEY")
    credential = AzureKeyCredential(key) if key else DefaultAzureCredential()

    client = ContentUnderstandingClient(endpoint=endpoint, credential=credential)

    analyzer_id = analyzer_json["analyzerId"]
    print(f"[yellow]Creating analyzer with analyzer ID: {analyzer_id}...[/yellow]")

    # Use SDK's begin_create_analyzer with the raw JSON dict
    poller = client.begin_create_analyzer(
        analyzer_id=analyzer_id,
        resource=analyzer_json,
        allow_replace=True,
    )
    result = poller.result()

    field_count = len(result.field_schema.fields) if result.field_schema and result.field_schema.fields else 0
    print(f"\n[green]Successfully created analyzer with ID: {analyzer_id} ({field_count} fields)[/green]")

if __name__ == "__main__":
    app()
