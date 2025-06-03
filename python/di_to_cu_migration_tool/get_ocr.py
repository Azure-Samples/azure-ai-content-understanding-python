# imports from built-in packages
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import random
import sys
import time
from typing import Optional

# imports from external packages (in requirements.txt)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
import requests
from rich import print  # For colored output
import typer

def is_token_expired(token) -> bool:
    """
    Check if the token is expired or about to expire.
    Args:
        token: The token object to check for expiration.
    Returns:
        bool: True if the token is expired or about to expire, False otherwise.
    """
    # Get the current time in UTC
    current_time = datetime.now(timezone.utc).timestamp()
    # Add a buffer (e.g., 60 seconds) to refresh the token before it expires
    buffer_time = 60
    # Check if the token is expired or about to expire
    return current_time >= (token.expires_on - buffer_time)

def get_token(credential, current_token = None) -> str:
    """
    Function to get a valid token
    Args:
        credential: The Azure credential object to use for authentication.
        current_token: The current token object to check for expiration.
    Returns:
        str: The new access token.
    """
    # Refresh token if it's expired or about to expire
    if current_token is None or is_token_expired(current_token):
        # Refresh the token
        current_token = credential.get_token("https://cognitiveservices.azure.com/.default")
        print("Successfully refreshed token")
    return current_token

def build_analyzer(credential, current_token, host, api_version, subscriptionKey) -> str:
    """
    Function to create an analyzer with empty schema to get CU Layout results
    Args:
        credential: The Azure credential object to use for authentication.
        current_token: The current token object to check for expiration.
        host: The host URL for the Cognitive Services API.
        api_version: The API version enviornmental variable to use.
        subscriptionKey: The subscription key for the Cognitive Services API.
    Returns:
        str: The analyzer ID of the created analyzer.
    """
    # Get a valid token
    current_token = get_token(credential, current_token)
    access_token = current_token.token
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Ocp-Apim-Subscription-Key": f"{subscriptionKey}",
        "Content-Type": "application/json"
    }
    analyzer_id = "sampleAnalyzer" + str(random.randint(0, 1000000))
    request_body = {
        "analyzerId": analyzer_id,
        "description": "Sample analyzer",
        "baseAnalyzerId": "prebuilt-documentAnalyzer",
        "config": {
            "returnDetails": True,
            "enableOcr": True,
            "enableLayout": True,
            "enableFormula": False,
            "disableContentFiltering": False,
            "estimateFieldSourceAndConfidence": False
        },
        "fieldSchema": {},
        "warnings": [],
        "status": "ready",
        "processingLocation": "geography",
        "mode": "standard"
    }
    endpoint = f"{host}/contentunderstanding/analyzers/{analyzer_id}?api-version={api_version}"
    print("[yellow]Creating sample analyzer to attain CU Layout results...[/yellow]")
    response = requests.put(
        url=endpoint,
        headers=headers,
        json=request_body,
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
            print(f"[green]Successfully created sample analyzer to gather Layout results[/green]")
            break
        elif status == "failed":
            print(f"[red]Failed: {result}[/red]")
            break
        else:
            print(".", end="", flush=True)
            time.sleep(0.5)
    return analyzer_id

def run_cu_layout_ocr(input_files: list, output_dir_string: str, subscription_key: str) -> None:
    """
    Function to run the CU Layout OCR on the list of pdf files and write to the given output directory
    Args:
        input_files (list): List of input PDF files to process.
        output_dir_string (str): Path to the output directory where results will be saved.
        subscription_key (str): The subscription key for the Cognitive Services API.
    """

    print("Running CU Layout OCR...")

    load_dotenv()

   # Set the global variables
    api_version = os.getenv("API_VERSION")
    host = os.getenv("HOST")

    credential = DefaultAzureCredential()
    current_token = None

    output_dir = Path(output_dir_string)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Need to create analyzer with empty schema
    analyzer_id = build_analyzer(credential, current_token, host, api_version, subscription_key)
    url = f"{host}/contentunderstanding/analyzers/{analyzer_id}:analyze?api-version={api_version}"

    for file in input_files:
        try:
            file = Path(file)
            print(f"\nProcessing file: {file.name}")
            # Get a valid token
            current_token = get_token(credential, current_token)
            headers = {
                "Authorization": f"Bearer {current_token.token}",
                "Apim-Subscription-id": f"{subscription_key}",
                "Content-Type": "application/pdf",
            }

            with open(file, "rb") as f:
                response = requests.post(url=url, data=f, headers=headers)
            response.raise_for_status()

            operation_location = response.headers.get("Operation-Location")
            if not operation_location:
                print("Error: 'Operation-Location' header is missing.")
                continue

            print(f"Polling results from: {operation_location}")
            while True:
                 # Refresh the token if necessary
                current_token = get_token(credential, current_token)
                poll_response = requests.get(operation_location, headers=headers)
                poll_response.raise_for_status()

                result = poll_response.json()
                status = result.get("status", "").lower()

                if status == "succeeded":
                    output_file = output_dir / (file.name + ".result.json")
                    with open(output_file, "w") as out_f:
                        json.dump(result, out_f, indent=4)
                    print(f"[green]Success: Results saved to {output_file}[/green]")
                    break
                elif status == "failed":
                    print(f"[red]Failed: {result}[/red]")
                    break
                else:
                    print(".", end="", flush=True)
                    time.sleep(0.5)

        except requests.RequestException as e:
            print(f"Request error for file {file.name}: {e}")
        except Exception as e:
            print(f"Unexpected error for file {file.name}: {e}")
