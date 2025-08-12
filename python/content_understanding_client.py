import base64
import json
import logging
import os
import requests
import time

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from requests.models import Response
from typing import Any, Dict, List, Optional
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.storage.blob import (
    BlobServiceClient,
    generate_container_sas,
    ContainerSasPermissions
)
from azure.storage.blob.aio import ContainerClient


POLL_TIMEOUT_SECONDS = 120


@dataclass
class ReferenceDocItem:
    filename: str
    file_path: str
    result_file_name: str
    result_file_path: Optional[str] = None


class AzureContentUnderstandingClient:

    PREBUILT_DOCUMENT_ANALYZER_ID: str = "prebuilt-documentAnalyzer"
    OCR_RESULT_FILE_SUFFIX: str = ".result.json"
    LABEL_FILE_SUFFIX: str = ".labels.json"
    KNOWLEDGE_SOURCE_LIST_FILE_NAME: str = "sources.jsonl"
    SAS_EXPIRY_HOURS: int = 1

    # https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/service-limits#document-and-text
    SUPPORTED_FILE_TYPES_DOCUMENT_TXT: List[str] = [
        ".pdf",
        ".tiff",
        ".jpg",
        ".jpeg",
        ".png",
        ".bmp",
        ".heif",
        ".docx",
        ".xlsx",
        ".pptx",
        ".txt",
        ".html",
        ".md",
        ".eml",
        ".msg",
        ".xml",
    ]

    SUPPORTED_FILE_TYPES_DOCUMENT: List[str] = [
        ".pdf",
        ".tiff",
        ".jpg",
        ".jpeg",
        ".png",
        ".bmp",
        ".heif",
    ]  # Pro mode and Training for Standard mode only support document data

    def __init__(
        self,
        endpoint: str,
        api_version: str,
        subscription_key: str = None,
        token_provider: callable = None,
        x_ms_useragent: str = "cu-sample-code",
    ):
        if not subscription_key and not token_provider:
            raise ValueError(
                "Either subscription key or token provider must be provided."
            )
        if not api_version:
            raise ValueError("API version must be provided.")
        if not endpoint:
            raise ValueError("Endpoint must be provided.")

        self._endpoint = endpoint.rstrip("/")
        self._api_version = api_version
        self._logger = logging.getLogger(__name__)

        token = token_provider() if token_provider else None

        self._headers = self._get_headers(subscription_key, token, x_ms_useragent)

    def _get_analyzer_url(self, endpoint: str, api_version: str, analyzer_id: str) -> str:
        return f"{endpoint}/contentunderstanding/analyzers/{analyzer_id}?api-version={api_version}"  # noqa

    def _get_analyzer_list_url(self, endpoint: str, api_version: str) -> str:
        return f"{endpoint}/contentunderstanding/analyzers?api-version={api_version}"

    def _get_analyze_url(self, endpoint: str, api_version: str, analyzer_id: str) -> str:
        return f"{endpoint}/contentunderstanding/analyzers/{analyzer_id}:analyze?api-version={api_version}"  # noqa

    def _get_training_data_config(
        self, storage_container_sas_url: str, storage_container_path_prefix: str
    ) -> Dict[str, str]:
        return {
            "containerUrl": storage_container_sas_url,
            "kind": "blob",
            "prefix": storage_container_path_prefix,
        }
    
    def _get_pro_mode_reference_docs_config(
        self, storage_container_sas_url: str, storage_container_path_prefix: str
    ) -> List[Dict[str, str]]:
        return [{
            "kind": "reference",
            "containerUrl": storage_container_sas_url,
            "prefix": storage_container_path_prefix,
            "fileListPath": self.KNOWLEDGE_SOURCE_LIST_FILE_NAME,
        }]

    def _get_classifier_url(self, endpoint: str, api_version: str, classifier_id: str) -> str:
        return f"{endpoint}/contentunderstanding/classifiers/{classifier_id}?api-version={api_version}"

    def _get_classify_url(self, endpoint: str, api_version: str, classifier_id: str) -> str:
        return f"{endpoint}/contentunderstanding/classifiers/{classifier_id}:classify?api-version={api_version}"

    def _get_headers(
        self, subscription_key: str, api_token: str, x_ms_useragent: str
    ) -> Dict[str, str]:
        """Returns the headers for the HTTP requests.
        Args:
            subscription_key (str): The subscription key for the service.
            api_token (str): The API token for the service.
            enable_face_identification (bool): A flag to enable face identification.
        Returns:
            dict: A dictionary containing the headers for the HTTP requests.
        """
        headers = (
            {"Ocp-Apim-Subscription-Key": subscription_key}
            if subscription_key
            else {"Authorization": f"Bearer {api_token}"}
        )
        headers["x-ms-useragent"] = x_ms_useragent
        return headers
    
    @staticmethod
    def is_supported_doc_type_by_file_ext(file_ext: str, is_document: bool=False) -> bool:
        """
        Checks if the given file extension is supported.

        Args:
            file_ext (str): The file extension to check.
            is_document (bool): If True, checks against Document supported file types.

        Returns:
            bool: True if the file type is supported, False otherwise.
        """
        supported_types = (
            AzureContentUnderstandingClient.SUPPORTED_FILE_TYPES_DOCUMENT
            if is_document else AzureContentUnderstandingClient.SUPPORTED_FILE_TYPES_DOCUMENT_TXT
        )
        return file_ext.lower() in supported_types
    
    @staticmethod
    def is_supported_doc_type_by_file_path(file_path: Path, is_document: bool=False) -> bool:
        """
        Checks if the given file path has a supported file type.

        Args:
            file_path (Path): The local path to the file to check.
            is_document (bool): If True, checks against Document supported file types.

        Returns:
            bool: True if the file type is supported, False otherwise.
        """
        if not file_path.is_file():
            return False
        file_ext = file_path.suffix.lower()
        return AzureContentUnderstandingClient.is_supported_doc_type_by_file_ext(file_ext, is_document)

    @staticmethod
    def generate_temp_container_sas_url(
        account_name: str,
        container_name: str,
        permissions: Optional[ContainerSasPermissions] = None,
        expiry_hours: Optional[int] = None,
    ) -> str:
        """
        Generate a temporary SAS URL for an Azure Blob container using Azure AD authentication.

        Args:
            account_name (str): The Azure Storage account name.
            container_name (str): The name of the container.
            permissions (ContainerSasPermissions, optional): Permissions to assign to the SAS token.
                Defaults to read and list permissions.
            expiry_hours (int, optional): Number of hours until the SAS token expires.
                Defaults to `AzureContentUnderstandingClient.SAS_EXPIRY_HOURS`.

        Returns:
            str: The SAS URL for the container.
        """
        if permissions is None:
            permissions = ContainerSasPermissions(read=True, list=True)
        expiry_duration = timedelta(hours=expiry_hours or AzureContentUnderstandingClient.SAS_EXPIRY_HOURS)

        account_url = f"https://{account_name}.blob.core.windows.net"
        blob_service_client = BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential())

        # Get user delegation key
        start_time = datetime.now(timezone.utc)
        expiry_time = start_time + expiry_duration
        delegation_key = blob_service_client.get_user_delegation_key(start_time, expiry_time)

        sas_token = generate_container_sas(
            account_name=account_name,
            container_name=container_name,
            user_delegation_key=delegation_key,
            permission=permissions,
            expiry=expiry_time,
            start=start_time,
        )

        return f"{account_url}/{container_name}?{sas_token}"

    def get_all_analyzers(self) -> Dict[str, Any]:
        """
        Retrieves a list of all available analyzers from the content understanding service.

        This method sends a GET request to the service endpoint to fetch the list of analyzers.
        It raises an HTTPError if the request fails.

        Returns:
            dict: A dictionary containing the JSON response from the service, which includes
                  the list of available analyzers.

        Raises:
            requests.exceptions.HTTPError: If the HTTP request returned an unsuccessful status code.
        """
        response = requests.get(
            url=self._get_analyzer_list_url(self._endpoint, self._api_version),
            headers=self._headers,
        )
        response.raise_for_status()
        return response.json()

    def get_analyzer_detail_by_id(self, analyzer_id: str) -> Dict[str, Any]:
        """
        Retrieves a specific analyzer detail through analyzerid from the content understanding service.
        This method sends a GET request to the service endpoint to get the analyzer detail.

        Args:
            analyzer_id (str): The unique identifier for the analyzer.

        Returns:
            dict: A dictionary containing the JSON response from the service, which includes the target analyzer detail.

        Raises:
            HTTPError: If the request fails.
        """
        response = requests.get(
            url=self._get_analyzer_url(self._endpoint, self._api_version, analyzer_id),
            headers=self._headers,
        )
        response.raise_for_status()
        return response.json()

    def begin_create_analyzer(
        self,
        analyzer_id: str,
        analyzer_template: dict = None,
        analyzer_template_path: str = "",
        training_storage_container_sas_url: str = "",
        training_storage_container_path_prefix: str = "",
        pro_mode_reference_docs_storage_container_sas_url: str = "",
        pro_mode_reference_docs_storage_container_path_prefix: str = "",
    ) -> Response:
        """
        Initiates the creation of an analyzer with the given ID and schema.

        Args:
            analyzer_id (str): The unique identifier for the analyzer.
            analyzer_template (dict, optional): The schema definition for the analyzer. Defaults to None.
            analyzer_template_path (str, optional): The file path to the analyzer schema JSON file. Defaults to "".
            training_storage_container_sas_url (str, optional): The SAS URL for the training storage container. Defaults to "".
            training_storage_container_path_prefix (str, optional): The path prefix within the training storage container. Defaults to "".

        Raises:
            ValueError: If neither `analyzer_template` nor `analyzer_template_path` is provided.
            requests.exceptions.HTTPError: If the HTTP request to create the analyzer fails.

        Returns:
            requests.Response: The response object from the HTTP request.
        """
        if analyzer_template_path and Path(analyzer_template_path).exists():
            with open(analyzer_template_path, "r") as file:
                analyzer_template = json.load(file)

        if not analyzer_template:
            raise ValueError("Analyzer schema must be provided.")

        if (
            training_storage_container_sas_url
            and training_storage_container_path_prefix
        ):  # noqa
            if not training_storage_container_path_prefix.endswith("/"):
                training_storage_container_path_prefix += "/"
            analyzer_template["trainingData"] = self._get_training_data_config(
                training_storage_container_sas_url,
                training_storage_container_path_prefix,
            )

        if (
            pro_mode_reference_docs_storage_container_sas_url
            and pro_mode_reference_docs_storage_container_path_prefix
        ):  # noqa
            if not pro_mode_reference_docs_storage_container_path_prefix.endswith("/"):
                pro_mode_reference_docs_storage_container_path_prefix += "/"
            analyzer_template["knowledgeSources"] = self._get_pro_mode_reference_docs_config(
                pro_mode_reference_docs_storage_container_sas_url,
                pro_mode_reference_docs_storage_container_path_prefix,
            )

        headers = {"Content-Type": "application/json"}
        headers.update(self._headers)

        response = requests.put(
            url=self._get_analyzer_url(self._endpoint, self._api_version, analyzer_id),
            headers=headers,
            json=analyzer_template,
        )
        response.raise_for_status()
        self._logger.info(f"Analyzer {analyzer_id} create request accepted.")
        return response

    def delete_analyzer(self, analyzer_id: str) -> Response:
        """
        Deletes an analyzer with the specified analyzer ID.

        Args:
            analyzer_id (str): The ID of the analyzer to be deleted.

        Returns:
            response: The response object from the delete request.

        Raises:
            HTTPError: If the delete request fails.
        """
        response = requests.delete(
            url=self._get_analyzer_url(self._endpoint, self._api_version, analyzer_id),
            headers=self._headers,
        )
        response.raise_for_status()
        self._logger.info(f"Analyzer {analyzer_id} deleted.")
        return response

    def begin_analyze(self, analyzer_id: str, file_location: str) -> Response:
        """
        Begins the analysis of a file or URL using the specified analyzer.

        Args:
            analyzer_id (str): The ID of the analyzer to use.
            file_location (str): The local path to the file or the URL to analyze.

        Returns:
            Response: The response from the analysis request.

        Raises:
            ValueError: If the file location is not a valid path or URL.
            HTTPError: If the HTTP request returned an unsuccessful status code.
        """
        data = None
        file_path = Path(file_location)
        if file_path.exists():
            if file_path.is_dir():
                # Only Pro mode supports multiple input files
                data = {
                    "inputs": [
                        {
                            "name": "_".join(f.relative_to(file_path).parts),  # flatten the relative file path into a single string using underscores
                            "data": base64.b64encode(f.read_bytes()).decode("utf-8")
                        }
                        for f in file_path.rglob("*")
                        if f.is_file() and self.is_supported_doc_type_by_file_path(f, is_document=True)
                    ]
                }
                headers = {"Content-Type": "application/json"}
            elif file_path.is_file():
                with open(file_location, "rb") as file:
                    data = file.read()
                headers = {"Content-Type": "application/octet-stream"}
            else:
                raise ValueError("File location must be a valid and supported file or directory path.")
        elif "https://" in file_location or "http://" in file_location:
            data = {"url": file_location}
            headers = {"Content-Type": "application/json"}
        else:
            raise ValueError("File location must be a valid path or URL.")

        headers.update(self._headers)
        if isinstance(data, dict):
            response = requests.post(
                url=self._get_analyze_url(
                    self._endpoint, self._api_version, analyzer_id
                ),
                headers=headers,
                json=data,
            )
        else:
            response = requests.post(
                url=self._get_analyze_url(
                    self._endpoint, self._api_version, analyzer_id
                ),
                headers=headers,
                data=data,
            )

        response.raise_for_status()
        self._logger.info(
            f"Analyzing file {file_location} with analyzer: {analyzer_id}"
        )
        return response
    
    def get_prebuilt_document_analyze_result(self, file_location: str) -> Dict[str, Any]:
        response = self.begin_analyze(
            analyzer_id=self.PREBUILT_DOCUMENT_ANALYZER_ID,
            file_location=file_location,
        )
        
        return self.poll_result(response, timeout_seconds=POLL_TIMEOUT_SECONDS)
    
    async def _upload_file_to_blob(
        self, container_client: ContainerClient, file_path: str, target_blob_path: str
    ) -> None:
        with open(file_path, "rb") as data:
            await container_client.upload_blob(name=target_blob_path, data=data, overwrite=True)
        self._logger.info(f"Uploaded file to {target_blob_path}")

    async def _upload_json_to_blob(
        self, container_client: ContainerClient, data: Dict[str, Any], target_blob_path: str
    ) -> None:
        json_str = json.dumps(data, indent=4)
        json_bytes = json_str.encode('utf-8')
        await container_client.upload_blob(name=target_blob_path, data=json_bytes, overwrite=True)
        self._logger.info(f"Uploaded json to {target_blob_path}")
    
    async def upload_jsonl_to_blob(
        self, container_client: ContainerClient, data_list: List[Dict[str, Any]], target_blob_path: str
    ) -> None:
        jsonl_string = "\n".join(json.dumps(record) for record in data_list)
        jsonl_bytes = jsonl_string.encode("utf-8")
        await container_client.upload_blob(name=target_blob_path, data=jsonl_bytes, overwrite=True)
        self._logger.info(f"Uploaded jsonl to blob '{target_blob_path}'")

    async def generate_training_data_on_blob(
        self,
        training_docs_folder: str,
        storage_container_sas_url: str,
        storage_container_path_prefix: str,
    ) -> None:
        if not storage_container_path_prefix.endswith("/"):
            storage_container_path_prefix += "/"
        
        async with ContainerClient.from_container_url(storage_container_sas_url) as container_client:
            for filename in os.listdir(training_docs_folder):
                file_path = os.path.join(training_docs_folder, filename)
                _, file_ext = os.path.splitext(filename)
                if os.path.isfile(file_path) and (
                        file_ext == "" or file_ext.lower() in self.SUPPORTED_FILE_TYPES_DOCUMENT):
                    # Training feature only supports Standard mode with document data
                    # Document files uploaded to AI Foundry will be convert to uuid without extension
                    label_filename = filename + self.LABEL_FILE_SUFFIX
                    label_path = os.path.join(training_docs_folder, label_filename)
                    ocr_result_filename = filename + self.OCR_RESULT_FILE_SUFFIX
                    ocr_result_path = os.path.join(training_docs_folder, ocr_result_filename)
                    if os.path.exists(label_path) and os.path.exists(ocr_result_path):
                        file_blob_path = storage_container_path_prefix + filename
                        label_blob_path = storage_container_path_prefix + label_filename
                        ocr_result_blob_path = storage_container_path_prefix + ocr_result_filename

                        # Upload files
                        await self._upload_file_to_blob(container_client, file_path, file_blob_path)
                        await self._upload_file_to_blob(container_client, label_path, label_blob_path)
                        await self._upload_file_to_blob(container_client, ocr_result_path, ocr_result_blob_path)
                        self._logger.info(f"Uploaded training data for {filename}")
                    else:
                        raise FileNotFoundError(
                            f"Label file '{label_filename}' or OCR result file '{ocr_result_filename}' "
                            f"does not exist in '{training_docs_folder}'. "
                            f"Please ensure both files exist for '{filename}'."
                        )

    def _get_analyze_list(
        self,
        reference_docs_folder: str,
    ) -> List[ReferenceDocItem]:
        """
        Returns a list of ReferenceDocItem objects for files in the given folder that need to be analyzed.
        """
        analyze_list: List[ReferenceDocItem] = []

        for dirpath, _, filenames in os.walk(reference_docs_folder):
            for filename in filenames:
                _, file_ext = os.path.splitext(filename)
                if self.is_supported_doc_type_by_file_ext(file_ext, is_document=True):
                    file_path = os.path.join(dirpath, filename)
                    result_file_name = filename + self.OCR_RESULT_FILE_SUFFIX
                    analyze_list.append(
                        ReferenceDocItem(
                            filename=filename,
                            file_path=file_path,
                            result_file_name=result_file_name,
                        )
                    )
                else:
                    raise ValueError(
                        f"File '{filename}' is not a supported document type, "
                        f"please remove it or convert it to a supported type."
                    )

        return analyze_list

    def _get_upload_only_list(
        self,
        reference_docs_folder: str,
    ) -> List[ReferenceDocItem]:
        """
        Returns a list of ReferenceDocItem objects for files in the given folder that already have OCR results
        """
        upload_only_list: List[ReferenceDocItem] = []

        for dirpath, _, filenames in os.walk(reference_docs_folder):
            for filename in filenames:
                _, file_ext = os.path.splitext(filename)
                if self.is_supported_doc_type_by_file_ext(file_ext, is_document=True):
                    file_path = os.path.join(dirpath, filename)
                    result_file_name = filename + self.OCR_RESULT_FILE_SUFFIX
                    result_file_path = os.path.join(dirpath, result_file_name)
                    if not os.path.exists(result_file_path):
                        raise FileNotFoundError(
                            f"Result file '{result_file_name}' does not exist in '{dirpath}'. "
                            f"Please run analyze first or remove this file from the folder."
                        )
                    upload_only_list.append(
                        ReferenceDocItem(
                            filename=filename,
                            file_path=file_path,
                            result_file_name=result_file_name,
                            result_file_path=result_file_path,
                        )
                    )
                elif filename.endswith(self.OCR_RESULT_FILE_SUFFIX):
                    original_filename = filename.replace(self.OCR_RESULT_FILE_SUFFIX, "")
                    if original_filename in filenames:
                        # skip result.json files corresponding to the file with supported document type
                        _, original_file_ext = os.path.splitext(original_filename)
                        if self.is_supported_doc_type_by_file_ext(original_file_ext, is_document=True):
                            continue
                        else:
                            raise ValueError(
                                f"The '{original_filename}' is not a supported document type, "
                                f"please remove the result file '{filename}' and '{original_filename}'."
                            )
                    else:
                        raise ValueError(
                            f"Result file '{filename}' is not corresponding to an original file, "
                            f"please remove it."
                        )
                else:
                    raise ValueError(
                        f"File '{filename}' is not a supported document type, "
                        f"please remove it or convert it to a supported type."
                    )

        return upload_only_list

    async def generate_knowledge_base_on_blob(
        self,
        reference_docs_folder: str,
        storage_container_sas_url: str,
        storage_container_path_prefix: str,
        skip_analyze: bool = False,
    ) -> None:
        """
        Generates a knowledge base on Azure Blob Storage by analyzing or uploading files from the given folder.
        Args:
            reference_docs_folder (str): The local path to the folder containing reference documents.
            storage_container_sas_url (str): The SAS URL of the Azure Blob Storage container.
            storage_container_path_prefix (str): The path prefix within the storage container where files will be
            skip_analyze (bool): If True, skips the analysis step and only uploads existing result files.
        """
        if not storage_container_path_prefix.endswith("/"):
            storage_container_path_prefix += "/"
        
        resources = []
        async with ContainerClient.from_container_url(storage_container_sas_url) as container_client:
            if not skip_analyze:
                analyze_list = self._get_analyze_list(reference_docs_folder)
                for analyze_item in analyze_list:
                    self._logger.info(f"Analyzing result for {analyze_item.filename}")
                    try:
                        analyze_result = self.get_prebuilt_document_analyze_result(analyze_item.file_path)
                    except Exception as e:
                        self._logger.error(
                            f"Error of getting analyze result of '{analyze_item.filename}'. "
                            f"Please check the error message and consider retrying or removing this file."
                            )
                        raise e
                    result_file_blob_path = storage_container_path_prefix + analyze_item.result_file_name
                    file_blob_path = storage_container_path_prefix + analyze_item.filename
                    await self._upload_json_to_blob(container_client, analyze_result, result_file_blob_path)
                    await self._upload_file_to_blob(container_client, analyze_item.file_path, file_blob_path)
                    resources.append({"file": analyze_item.filename, "resultFile": analyze_item.result_file_name})
            else:
                upload_list = self._get_upload_only_list(reference_docs_folder)
                for upload_item in upload_list:
                    self._logger.info(f"Using existing result.json for '{upload_item.filename}'")
                    result_file_blob_path = storage_container_path_prefix + upload_item.result_file_name
                    file_blob_path = storage_container_path_prefix + upload_item.filename
                    await self._upload_file_to_blob(container_client, upload_item.file_path, file_blob_path)
                    await self._upload_file_to_blob(container_client, upload_item.result_file_path, result_file_blob_path)
                    resources.append({"file": upload_item.filename, "resultFile": upload_item.result_file_name})

            # Upload sources.jsonl
            await self.upload_jsonl_to_blob(
                container_client, resources, storage_container_path_prefix + self.KNOWLEDGE_SOURCE_LIST_FILE_NAME)

    def get_image_from_analyze_operation(
        self, analyze_response: Response, image_id: str
    ) -> Optional[bytes]:
        """Retrieves an image from the analyze operation using the image ID.
        Args:
            analyze_response (Response): The response object from the analyze operation.
            image_id (str): The ID of the image to retrieve.
        Returns:
            bytes: The image content as a byte string.
        """
        operation_location = analyze_response.headers.get("operation-location", "")
        if not operation_location:
            raise ValueError(
                "Operation location not found in the analyzer response header."
            )
        operation_location = operation_location.split("?api-version")[0]
        image_retrieval_url = (
            f"{operation_location}/files/{image_id}?api-version={self._api_version}"
        )
        try:
            response = requests.get(url=image_retrieval_url, headers=self._headers)
            response.raise_for_status()

            assert response.headers.get("Content-Type") == "image/jpeg"

            return response.content
        except requests.exceptions.RequestException as e:
            print(f"HTTP request failed: {e}")
            return None

    def begin_create_classifier(
        self,
        classifier_id: str,
        classifier_schema: Dict[str, Any],
    ) -> Response:
        """
        Initiates the creation of an classifier with the given ID and schema.

        Args:
            classifier_id (str): The unique identifier for the classifier.
            classifier_schema (dict): The schema definition for the classifier.

        Raises:
            requests.exceptions.HTTPError: If the HTTP request to create the classifier fails.
            ValueError: If the classifier schema or ID is not provided.

        Returns:
            requests.Response: The response object from the HTTP request.
        """

        if not classifier_schema:
            raise ValueError("Classifier schema must be provided.")
        if not classifier_id:
            raise ValueError("Classifier ID must be provided.")

        headers = {"Content-Type": "application/json"}
        headers.update(self._headers)

        response = requests.put(
            url=self._get_classifier_url(self._endpoint, self._api_version, classifier_id),
            headers=headers,
            json=classifier_schema,
        )
        response.raise_for_status()
        self._logger.info(f"Classifier {classifier_id} create request accepted.")
        return response

    def begin_classify(self, classifier_id: str, file_location: str) -> Response:
        """
        Begins the analysis of a file or URL using the specified classifier.

        Args:
            classifier_id (str): The ID of the classifier to use.
            file_location (str): The local path to the file or the URL to analyze.

        Returns:
            Response: The response from the analysis request.

        Raises:
            ValueError: If the file location is not a valid path or URL.
            HTTPError: If the HTTP request returned an unsuccessful status code.
        """
        data = None
        if Path(file_location).exists():
            with open(file_location, "rb") as file:
                data = file.read()
            headers = {"Content-Type": "application/octet-stream"}
        elif "https://" in file_location or "http://" in file_location:
            data = {"url": file_location}
            headers = {"Content-Type": "application/json"}
        else:
            raise ValueError("File location must be a valid path or URL.")

        headers.update(self._headers)
        if isinstance(data, dict):
            response = requests.post(
                url=self._get_classify_url(
                    self._endpoint, self._api_version, classifier_id
                ),
                headers=headers,
                json=data,
            )
        else:
            response = requests.post(
                url=self._get_classify_url(
                    self._endpoint, self._api_version, classifier_id
                ),
                headers=headers,
                data=data,
            )

        response.raise_for_status()
        self._logger.info(
            f"Analyzing file {file_location} with classifier_id: {classifier_id}"
        )
        return response

    def poll_result(
        self,
        response: Response,
        timeout_seconds: int = POLL_TIMEOUT_SECONDS,
        polling_interval_seconds: int = 2,
    ) -> Dict[str, Any]:
        """
        Polls the result of an asynchronous operation until it completes or times out.

        Args:
            response (Response): The initial response object containing the operation location.
            timeout_seconds (int, optional): The maximum number of seconds to wait for the operation to complete. Defaults to 120.
            polling_interval_seconds (int, optional): The number of seconds to wait between polling attempts. Defaults to 2.

        Raises:
            ValueError: If the operation location is not found in the response headers.
            TimeoutError: If the operation does not complete within the specified timeout.
            RuntimeError: If the operation fails.

        Returns:
            dict: The JSON response of the completed operation if it succeeds.
        """
        operation_location = response.headers.get("operation-location", "")
        if not operation_location:
            raise ValueError("Operation location not found in response headers.")

        headers = {"Content-Type": "application/json"}
        headers.update(self._headers)

        start_time = time.time()
        while True:
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout_seconds:
                raise TimeoutError(
                    f"Operation timed out after {timeout_seconds:.2f} seconds."
                )

            response = requests.get(operation_location, headers=self._headers)
            response.raise_for_status()
            status = response.json().get("status").lower()
            if status == "succeeded":
                self._logger.info(
                    f"Request result is ready after {elapsed_time:.2f} seconds."
                )
                return response.json()
            elif status == "failed":
                self._logger.error(f"Request failed. Reason: {response.json()}")
                raise RuntimeError("Request failed.")
            else:
                self._logger.info(
                    f"Request {operation_location.split('/')[-1].split('?')[0]} in progress ..."
                )
            time.sleep(polling_interval_seconds)
