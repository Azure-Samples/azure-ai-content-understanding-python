# imports from built-in packages
import json
import os
from pathlib import Path

# imports from external packages (in requirements.txt)
from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.ai.contentunderstanding.models import AnalysisResult
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from rich import print  # For colored output


def run_cu_layout_ocr(input_files: list, output_dir_string: str, subscription_key: str) -> None:
    """
    Function to run the CU Layout OCR on the list of pdf files and write to the given output directory.
    Uses the Content Understanding Python SDK with prebuilt-layout analyzer.
    Args:
        input_files (list): List of input PDF files to process.
        output_dir_string (str): Path to the output directory where results will be saved.
        subscription_key (str): The subscription key for the Cognitive Services API (optional, ignored if empty).
    """

    print("Running CU Layout OCR...")

    load_dotenv()

    endpoint = os.environ["CONTENTUNDERSTANDING_ENDPOINT"]
    # Use subscription key if provided, otherwise fall back to DefaultAzureCredential
    credential = AzureKeyCredential(subscription_key) if subscription_key else DefaultAzureCredential()

    client = ContentUnderstandingClient(endpoint=endpoint, credential=credential)

    output_dir = Path(output_dir_string)
    output_dir.mkdir(parents=True, exist_ok=True)

    for file in input_files:
        try:
            file = Path(file)
            print(f"\nProcessing file: {file.name}")

            with open(file, "rb") as f:
                file_bytes = f.read()

            # Use SDK's begin_analyze_binary with prebuilt-layout
            poller = client.begin_analyze_binary(
                analyzer_id="prebuilt-layout",
                binary_input=file_bytes,
            )
            result: AnalysisResult = poller.result()

            # Save the result as JSON
            output_file = output_dir / (file.name + ".result.json")
            result_dict = result.as_dict()
            with open(output_file, "w") as out_f:
                json.dump(result_dict, out_f, indent=4)
            print(f"[green]Success: Results saved to {output_file}[/green]")

        except Exception as e:
            print(f"[red]Error for file {file.name}: {e}[/red]")
