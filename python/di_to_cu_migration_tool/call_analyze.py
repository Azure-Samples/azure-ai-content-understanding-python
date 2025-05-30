# imports from built-in packages
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobClient
from dotenv import load_dotenv
import json
import os
from pathlib import Path
import requests
import time
import typer

# imports from external packages (in requirements.txt)
from rich import print  # For colored output

app = typer.Typer()

@app.command()
def main(
        analyzer_id: str = typer.Option(..., "--analyzer-id", help="Analyzer ID to use for the analyze API"),
        pdf_sas_url: str = typer.Option(..., "--pdf-sas-url", help="SAS URL for the PDF file to analyze"),
        output_json: str = typer.Option("./sample_documents/analyzer_result.json", "--output-json", help="Output JSON file for the analyze result")
):
    """
    Main function to call the analyze API
    """
    assert analyzer_id != "", "Please provide the analyzer ID to use for the analyze API"
    assert pdf_sas_url != "", "Please provide the SAS URL for the PDF file you wish to analyze"

    load_dotenv()
    # Request Header - Content-Type
    # Acquire a token for the desired scope
    credential = DefaultAzureCredential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default")

    # Extract the access token
    access_token = token.token
    subscription_key = os.getenv("SUBSCRIPTION_KEY")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Ocp-Apim-Subscription-Key": f"{subscription_key}",
        "Content-Type": "application/pdf"
    }

    host  = os.getenv("HOST")
    api_version = os.getenv("API_VERSION")
    endpoint = f"{host}/contentunderstanding/analyzers/{analyzer_id}:analyze?api-version={api_version}"

    blob = BlobClient.from_blob_url(pdf_sas_url)
    blob_data = blob.download_blob().readall()
    response = requests.post(url=endpoint, data=blob_data, headers=headers)

    response.raise_for_status()
    print(f"[yellow]Analyzing file {pdf_sas_url} with analyzer {analyzer_id}[/yellow]")

    operation_location = response.headers.get("Operation-Location", None)
    if not operation_location:
        print("Error: 'Operation-Location' header is missing.")

    while True:
        poll_response = requests.get(operation_location, headers=headers)
        poll_response.raise_for_status()

        result = poll_response.json()
        status = result.get("status", "").lower()

        if status == "succeeded":
            print(f"[green]Successfully analyzed file {pdf_sas_url} with analyzer ID of {analyzer_id}.[/green]\n")
            analyze_result_file = Path(output_json)
            with open(analyze_result_file, "w") as f:
                json.dump(result, f, indent=4)
            print(f"[green]Analyze result saved to {analyze_result_file}[/green]")
            break
        elif status == "failed":
            print(f"[red]Failed: {result}[/red]")
            break
        else:
            print(".", end="", flush=True)
            time.sleep(0.5)

if __name__ == "__main__":
    app()