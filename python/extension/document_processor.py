from datetime import datetime, timedelta, timezone
import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from azure.identity import DefaultAzureCredential
from azure.storage.blob.aio import ContainerClient
from azure.ai.contentunderstanding.aio import ContentUnderstandingClient
from azure.storage.blob import (
    BlobServiceClient,
    generate_container_sas,
    ContainerSasPermissions
)
from dataclasses import dataclass

@dataclass
class ReferenceDocItem:
    file_name: str = ""
    file_path: str = ""
    result_file_name: str = ""
    result_file_path: str = ""

class DocumentProcessor:
    OCR_RESULT_FILE_SUFFIX: str = ".result.json"
    LABEL_FILE_SUFFIX: str = ".labels.json"
    KNOWLEDGE_SOURCE_LIST_FILE_NAME: str = "sources.jsonl"
    SAS_EXPIRY_HOURS: int = 1

    SUPPORTED_FILE_TYPES_DOCUMENT_TXT: List[str] = [
        ".pdf", ".tiff", ".jpg", ".jpeg", ".png", ".bmp", ".heif", ".docx",
        ".xlsx", ".pptx", ".txt", ".html", ".md", ".eml", ".msg", ".xml",
    ]

    SUPPORTED_FILE_TYPES_DOCUMENT: List[str] = [
        ".pdf", ".tiff", ".jpg", ".jpeg", ".png", ".bmp", ".heif",
    ]

    def __init__(self, client: ContentUnderstandingClient):
        self._client = client

    def generate_container_sas_url(
        self,
        account_name: str,
        container_name: str,
        permissions: Optional[ContainerSasPermissions] = None,
        expiry_hours: Optional[int] = None,
    ) -> str:
        """Generate a temporary SAS URL for an Azure Blob container using Azure AD authentication."""
        print(f"account_name: {account_name}")
        if not all([account_name, container_name]):
            raise ValueError("Account name and container name must be provided.")
        
        permissions = permissions or ContainerSasPermissions(read=True, write=True, list=True)
        hours = expiry_hours or self.SAS_EXPIRY_HOURS

        now = datetime.now(timezone.utc)
        expiry = now + timedelta(hours=hours)
        account_url = f"https://{account_name}.blob.core.windows.net"
        client = BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential())

        delegation_key = client.get_user_delegation_key(now, expiry)
        sas_token = generate_container_sas(
            account_name=account_name,
            container_name=container_name,
            user_delegation_key=delegation_key,
            permission=permissions,
            expiry=expiry,
            start=now,
        )

        return f"{account_url}/{container_name}?{sas_token}"

    async def generate_knowledge_base_on_blob(
        self,
        reference_docs_folder: str,
        storage_container_sas_url: str,
        storage_container_path_prefix: str,
        skip_analyze: bool = False
    ):
        if not storage_container_path_prefix.endswith("/"):
            storage_container_path_prefix += "/"
        
        try:
            resources = []
            container_client = ContainerClient.from_container_url(storage_container_sas_url)

            if not skip_analyze:
                analyze_list: List[ReferenceDocItem] = self._get_analyze_list(reference_docs_folder)

                for analyze_item in analyze_list:
                    try:
                        print(analyze_item.file_path)

                        with open(analyze_item.file_path, "rb") as f:
                            pdf_bytes: bytes = f.read()

                        print(f"🔍 Analyzing {analyze_item.file_path} with prebuilt-documentAnalyzer...")
                        poller = await self._client.content_analyzers.begin_analyze_binary(
                            analyzer_id="prebuilt-documentAnalyzer",
                            input=pdf_bytes,
                            content_type="application/pdf",
                            cls=lambda pipeline_response, deserialized_obj, response_headers: (
                                deserialized_obj,
                                pipeline_response.http_response,
                            ),
                        )
                        _, raw_http_response = await poller.result()

                        print(f"Analysis completed for {raw_http_response}.")
                        json_string = json.dumps(raw_http_response.json())
                        print("json string type:", type(json_string))
                        print(f"Analysis result: {json_string}")

                        result_file_blob_path = storage_container_path_prefix + analyze_item.result_file_name
                        file_blob_path = storage_container_path_prefix + analyze_item.file_name

                        await self._upload_json_to_blob(container_client, json_string, result_file_blob_path)
                        await self._upload_file_to_blob(container_client, analyze_item.file_path, file_blob_path)

                        resources.append({
                            "file": analyze_item.file_name,
                            "resultFile": analyze_item.result_file_name
                        })
                    except json.JSONDecodeError as json_ex:
                        raise ValueError(
                            f"Failed to parse JSON result for file '{analyze_item.file_path}'. "
                            f"Ensure the file is a valid document and the analyzer is set up correctly."
                        ) from json_ex
                    except Exception as ex:
                        raise ValueError(
                            f"Failed to analyze file '{analyze_item.file_path}'. "
                            f"Ensure the file is a valid document and the analyzer is set up correctly."
                        ) from ex
            else:
                upload_list: List[ReferenceDocItem] = []

                # Process subdirectories
                for dir_path in Path(reference_docs_folder).rglob("*"):
                    if dir_path.is_dir():
                        self._process_directory(str(dir_path), upload_list)
                        
                # Process root directory
                self._process_directory(reference_docs_folder, upload_list)

                for upload_item in upload_list:
                    result_file_blob_path = storage_container_path_prefix + upload_item.result_file_name
                    file_blob_path = storage_container_path_prefix + upload_item.file_name

                    await self._upload_file_to_blob(container_client, upload_item.result_file_path, result_file_blob_path)
                    await self._upload_file_to_blob(container_client, upload_item.file_path, file_blob_path)

                    resources.append({
                        "file": upload_item.file_name,
                        "resultFile": upload_item.result_file_name
                    })
                    
            # Convert resources to JSON strings
            jsons = [json.dumps(record) for record in resources]

            await self._upload_jsonl_to_blob(container_client, jsons, storage_container_path_prefix + self.KNOWLEDGE_SOURCE_LIST_FILE_NAME)
        finally:
            if container_client:
                await container_client.close()

    def _process_directory(self, dir_path: str, upload_only_list: List[ReferenceDocItem]):
        # Get all files in the directory 
        try:
            file_names = set(os.listdir(dir_path))
            file_paths = [os.path.join(dir_path, f) for f in file_names if os.path.isfile(os.path.join(dir_path, f))]
        except OSError:
            return

        for file_path in file_paths:
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1]

            if self.is_supported_doc_type_by_file_ext(file_ext, is_document=True):
                result_file_name = file_name + self.OCR_RESULT_FILE_SUFFIX
                result_file_path = os.path.join(dir_path, result_file_name)

                if not os.path.exists(result_file_path):
                    raise FileNotFoundError(
                        f"Result file '{result_file_name}' not found in directory '{dir_path}'. "
                        f"Please run analyze first or remove this file from the folder."
                    )
                
                upload_only_list.append(ReferenceDocItem(
                    file_name=file_name,
                    file_path=file_path,
                    result_file_name=result_file_name,
                    result_file_path=result_file_path
                ))
            elif file_name.lower().endswith(self.OCR_RESULT_FILE_SUFFIX.lower()):
                ocr_suffix = self.OCR_RESULT_FILE_SUFFIX
                original_file_name = file_name[:-len(ocr_suffix)]
                original_file_path = os.path.join(dir_path, original_file_name)

                if os.path.exists(original_file_path):
                    origin_file_ext = os.path.splitext(original_file_name)[1]

                    if self.is_supported_doc_type_by_file_ext(origin_file_ext, is_document=True):
                        continue
                    else:
                        raise ValueError(
                            f"The '{original_file_name}' is not a supported document type, "
                            f"please remove the result file '{file_name}' and '{original_file_name}'."
                        )
                else:
                    raise ValueError(
                        f"Result file '{file_name}' is not corresponding to an original file, "
                        f"please remove it."
                    )
            else:
                raise ValueError(
                    f"File '{file_name}' is not a supported document type, "
                    f"please remove it or convert it to a supported type."
                )

    def _get_analyze_list(self, reference_docs_folder: str) -> List[ReferenceDocItem]:
        """
        Get a list of reference document items from the specified folder and its subdirectories.
        
        Args:
            reference_docs_folder: Path to the folder containing reference documents
            
        Returns:
            List of ReferenceDocItem objects for supported document types
            
        Raises:
            ValueError: If unsupported document types are found
        """
        analyze_list: List[ReferenceDocItem] = []
        root_path = Path(reference_docs_folder)
        
        # Check if the root path exists
        if not root_path.exists():
            return analyze_list
        
        # Get all files recursively (including root folder)
        for file_path in root_path.rglob("*"):
            if not file_path.is_file():
                continue
                
            try:
                file_name_only = file_path.name
                file_ext = file_path.suffix
                
                if self.is_supported_doc_type_by_file_ext(file_ext, is_document=True):
                    result_file_name = file_name_only + self.OCR_RESULT_FILE_SUFFIX
                    analyze_list.append(ReferenceDocItem(
                        file_name=file_name_only,
                        file_path=str(file_path),
                        result_file_name=result_file_name
                    ))
                else:
                    raise ValueError(
                        f"File '{file_name_only}' is not a supported document type, "
                        f"please remove it or convert it to a supported type."
                    )
            except OSError:
                # Skip files that can't be accessed
                continue
        
        return analyze_list
    
    async def generate_training_data_on_blob(
        self,
        training_docs_folder: str,
        storage_container_sas_url: str,
        storage_container_path_prefix: str,
    ) -> None:
        if not storage_container_path_prefix.endswith("/"):
            storage_container_path_prefix += "/"
        
        async with ContainerClient.from_container_url(storage_container_sas_url) as container_client:
            for file_name in os.listdir(training_docs_folder):
                file_path = os.path.join(training_docs_folder, file_name)
                _, file_ext = os.path.splitext(file_name)
                if os.path.isfile(file_path) and (
                    file_ext == "" or file_ext.lower() in self.SUPPORTED_FILE_TYPES_DOCUMENT):
                        # Training feature only supports Standard mode with document data
                        # Document files uploaded to AI Foundry will be convert to uuid without extension
                        label_file_name = file_name + self.LABEL_FILE_SUFFIX
                        label_path = os.path.join(training_docs_folder, label_file_name)
                        ocr_result_file_name = file_name + self.OCR_RESULT_FILE_SUFFIX
                        ocr_result_path = os.path.join(training_docs_folder, ocr_result_file_name)

                        if os.path.exists(label_path) and os.path.exists(ocr_result_path):
                            file_blob_path = storage_container_path_prefix + file_name
                            label_blob_path = storage_container_path_prefix + label_file_name
                            ocr_result_blob_path = storage_container_path_prefix + ocr_result_file_name

                            # Upload files
                            await self._upload_file_to_blob(container_client, file_path, file_blob_path)
                            await self._upload_file_to_blob(container_client, label_path, label_blob_path)
                            await self._upload_file_to_blob(container_client, ocr_result_path, ocr_result_blob_path)
                            print(f"Uploaded training data for {file_name}")
                        else:
                            raise FileNotFoundError(
                                f"Label file '{label_file_name}' or OCR result file '{ocr_result_file_name}' "
                                f"does not exist in '{training_docs_folder}'. "
                                f"Please ensure both files exist for '{file_name}'."
                            )

    async def _upload_file_to_blob(
        self, container_client: ContainerClient, file_path: str, target_blob_path: str
    ) -> None:
        with open(file_path, "rb") as data:
            await container_client.upload_blob(name=target_blob_path, data=data, overwrite=True)
        print(f"Uploaded file to {target_blob_path}")

    async def _upload_json_to_blob(
        self, container_client: ContainerClient, json_string: str, target_blob_path: str
    ) -> None:
        json_bytes = json_string.encode('utf-8')
        await container_client.upload_blob(name=target_blob_path, data=json_bytes, overwrite=True)
        print(f"Uploaded json to {target_blob_path}")
    
    async def _upload_jsonl_to_blob(
        self, container_client: ContainerClient, data_list: List[str], target_blob_path: str
    ) -> None:
        jsonl_string = "\n".join(data_list)
        jsonl_bytes = jsonl_string.encode("utf-8")
        await container_client.upload_blob(name=target_blob_path, data=jsonl_bytes, overwrite=True)
        print(f"Uploaded jsonl to blob '{target_blob_path}'")

    def is_supported_doc_type_by_file_ext(self, file_ext: str, is_document: bool=False) -> bool:
        supported_types = (
            self.SUPPORTED_FILE_TYPES_DOCUMENT
            if is_document else self.SUPPORTED_FILE_TYPES_DOCUMENT_TXT
        )
        return file_ext.lower() in supported_types
    
    def is_supported_doc_type_by_file_path(self, file_path: Path, is_document: bool=False) -> bool:
        if not file_path.is_file():
            return False
        file_ext = file_path.suffix.lower()
        return self.is_supported_doc_type_by_file_ext(file_ext, is_document)