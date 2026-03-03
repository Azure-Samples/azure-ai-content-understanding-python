# imports from built-in packages
import json
import os
from pathlib import Path
import typer

# imports from external packages (in requirements.txt)
from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.ai.contentunderstanding.models import AnalysisInput
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from rich import print  # For colored output

app = typer.Typer()

@app.command()
def main(
        analyzer_id: str = typer.Option(..., "--analyzer-id", help="Analyzer ID to use for the analyze API"),
        document_sas_url: str = typer.Option(..., "--document-sas-url", help="SAS URL for the document to analyze (PDF, image, etc.)"),
        output_json: str = typer.Option("./sample_documents/analyzer_result.json", "--output-json", help="Output JSON file for the analyze result")
):
    """
    Main function to call the analyze API using the Content Understanding Python SDK.

    Sends the document URL to the Content Understanding analyze endpoint.
    Supports any document type accepted by the service (PDF, JPEG, PNG, TIFF, etc.).
    """
    assert analyzer_id != "", "Please provide the analyzer ID to use for the analyze API"
    assert document_sas_url != "", "Please provide the SAS URL for the document you wish to analyze"

    load_dotenv()

    # Set up credentials and client
    endpoint = os.environ["CONTENTUNDERSTANDING_ENDPOINT"]
    key = os.getenv("CONTENTUNDERSTANDING_KEY")
    credential = AzureKeyCredential(key) if key else DefaultAzureCredential()

    client = ContentUnderstandingClient(endpoint=endpoint, credential=credential)

    print(f"[yellow]Analyzing document with analyzer {analyzer_id}...[/yellow]")

    # Call the analyze API with the document URL
    poller = client.begin_analyze(
        analyzer_id=analyzer_id,
        inputs=[AnalysisInput(url=document_sas_url)],
    )
    result = poller.result()

    # Save the result as JSON
    analyze_result_file = Path(output_json)
    analyze_result_file.parent.mkdir(parents=True, exist_ok=True)
    # Convert the SDK model to a dict for JSON serialization
    result_dict = result.as_dict()
    with open(analyze_result_file, "w") as f:
        json.dump(result_dict, f, indent=4)

    print(f"[green]Successfully analyzed document with analyzer {analyzer_id}.[/green]")
    print(f"[green]Analyze result saved to {analyze_result_file}[/green]")

if __name__ == "__main__":
    app()