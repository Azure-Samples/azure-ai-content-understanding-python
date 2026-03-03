# imports from built-in packages
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
import json
import os
from pathlib import Path
import requests
import time
import typer

# imports from external packages (in requirements.txt)
from rich import print  # For colored output

# imports from local packages
from constants import CU_API_VERSION

app = typer.Typer()

@app.command()
def main(
        analyzer_id: str = typer.Option(..., "--analyzer-id", help="Analyzer ID to use for the analyze API"),
        document_sas_url: str = typer.Option(..., "--document-sas-url", help="SAS URL for the document to analyze (PDF, image, etc.)"),
        output_json: str = typer.Option("./sample_documents/analyzer_result.json", "--output-json", help="Output JSON file for the analyze result")
):
    """
    Main function to call the analyze API.

    Sends the document URL to the Content Understanding analyze endpoint.
    Supports any document type accepted by the service (PDF, JPEG, PNG, TIFF, etc.).
    """
    assert analyzer_id != "", "Please provide the analyzer ID to use for the analyze API"
    assert document_sas_url != "", "Please provide the SAS URL for the document you wish to analyze"

    load_dotenv()
    # Acquire a token for the desired scope
    credential = DefaultAzureCredential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default")

    # Extract the access token
    access_token = token.token
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Only include subscription key header if provided
    subscription_key = os.getenv("SUBSCRIPTION_KEY")
    if subscription_key:
        headers["Ocp-Apim-Subscription-Key"] = subscription_key

    host = os.getenv("HOST")
    endpoint = f"{host}/contentunderstanding/analyzers/{analyzer_id}:analyze?api-version={CU_API_VERSION}&stringEncoding=codePoint"

    # Send the document URL to the service
    request_body = {
        "inputs": [
            {"url": document_sas_url}
        ]
    }
    response = requests.post(url=endpoint, data=json.dumps(request_body), headers=headers)

    if not response.ok:
        print(f"[red]Error {response.status_code}: {response.text}[/red]")
    response.raise_for_status()
    print(f"[yellow]Analyzing document with analyzer {analyzer_id}...[/yellow]")

    operation_location = response.headers.get("Operation-Location", None)
    if not operation_location:
        print("[red]Error: 'Operation-Location' header is missing.[/red]")
        return

    while True:
        poll_response = requests.get(operation_location, headers=headers)
        poll_response.raise_for_status()

        result = poll_response.json()
        status = result.get("status", "").lower()

        if status == "succeeded":
            print(f"\n[green]Successfully analyzed document with analyzer {analyzer_id}.[/green]")
            analyze_result_file = Path(output_json)
            analyze_result_file.parent.mkdir(parents=True, exist_ok=True)
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