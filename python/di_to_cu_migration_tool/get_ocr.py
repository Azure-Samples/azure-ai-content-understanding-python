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
# imports from same project (in constants.py)
from constants import CU_API_VERSION, COMPLETION_MODEL, EMBEDDING_MODEL

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
    api_version = CU_API_VERSION
    if not api_version:
        api_version = os.getenv("API_VERSION")
    host = os.getenv("HOST")

    credential = DefaultAzureCredential()
    current_token = None

    output_dir = Path(output_dir_string)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use prebuilt-layout analyzer directly - no need to create a custom analyzer
    url = f"{host.rstrip('/')}/contentunderstanding/analyzers/prebuilt-layout:analyzeBinary?api-version={api_version}"

    for file in input_files:
        try:
            file = Path(file)
            print(f"\nProcessing file: {file.name}")
            # Get a valid token
            current_token = get_token(credential, current_token)
            headers = {
                "Authorization": f"Bearer {current_token.token}",
                "Ocp-Apim-Subscription-Key": f"{subscription_key}",
                "Content-Type": "application/octet-stream",
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
