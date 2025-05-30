# imports from built-in packages
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobClient
from dotenv import load_dotenv
import json
import os
import requests
import time
import typer

# imports from external packages (in requirements.txt)
from rich import print  # For colored output

app = typer.Typer()

@app.command()
def main(
    analyzer_sas_url: str = typer.Option("", "--analyzer-sas-url", help="SAS URL for the created analyzer.json"),
    target_container_sas_url: str = typer.Option("", "--target-container-sas-url", help="Target blob container SAS URL."),
    target_blob_folder: str = typer.Option("", "--target-blob-folder", help="Target blob storage folder prefix."),
):
    """
    Main function to create the CU analyzer
    """
    assert analyzer_sas_url != "", "Please provide the SAS URL for the created CU analyzer.json so we are able to call the Build Analyzer API"
    assert target_container_sas_url != "", "Please provide the SAS URL for the target blob container so we are able to refer to the created CU dataset"
    assert target_blob_folder != "", "Please provide the target blob folder so we are able to refer to the created CU dataset"


    # Load the analyzer.json file
    print(f"Loading analyzer.json from...")
    blob_client = BlobClient.from_blob_url(analyzer_sas_url)
    analyzer_json = blob_client.download_blob().readall()
    analyzer_json = analyzer_json.decode("utf-8")
    analyzer_json = json.loads(analyzer_json)
    print("[yellow]Finished loading analyzer.json.[/yellow]\n")

    # URI Parameters - analyzerId, endpoint, & api-version
    load_dotenv()
    analyzer_id = analyzer_json["analyzerId"]
    host = os.getenv("HOST")
    api_version = os.getenv("API_VERSION")
    endpoint = f"{host}/contentunderstanding/analyzers/{analyzer_id}?api-version={api_version}"

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
        "Content-Type": "application/json"
    }


    print(f"[yellow]Creating analyzer with analyzer ID: {analyzer_id}...[/yellow]")
    response = requests.put(
        url=endpoint,
        headers=headers,
        json=analyzer_json,
    )
    response.raise_for_status()
    operation_location = response.headers.get("Operation-Location", None)
    if not operation_location:
        print("Error: 'Operation-Location' header is missing.")

    while True:
        poll_response = requests.get(operation_location, headers=headers)
        poll_response.raise_for_status()

        result = poll_response.json()
        status = result.get("status", "").lower()

        if status == "succeeded":
            print(f"\n[green]Successfully created analyzer with ID: {analyzer_id}[/green]")
            break
        elif status == "failed":
            print(f"[red]Failed: {result}[/red]")
            break
        else:
            print(".", end="", flush=True)
            time.sleep(0.5)

if __name__ == "__main__":
    app()
