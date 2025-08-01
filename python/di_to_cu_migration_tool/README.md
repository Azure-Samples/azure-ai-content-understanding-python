# Document Intelligence to Content Understanding Migration Tool (Python)

Welcome! This tool is designed to help convert your Document Intelligence (DI) datasets to the Content Understanding (CU) **Preview.2** 2025-05-01-preview format, as used in AI Foundry. The following DI versions are supported:

- Custom Extraction Model DI 3.1 GA (2023-07-31) to DI 4.0 GA (2024-11-30) (Document Intelligence Studio) → DI-version = neural  
- Document Field Extraction Model 4.0 Preview (2024-07-31-preview) (AI Foundry/AI Services/Vision + Document/Document Field Extraction) → DI-version = generative

To identify which version of Document Intelligence your dataset uses, please consult the sample documents provided in this folder to determine which format matches yours. Additionally, you can identify the version through your DI project's user interface:

- Custom Extraction DI 3.1/4.0 GA is part of Document Intelligence Studio (https://documentintelligence.ai.azure.com/studio)  
- Document Field Extraction DI 4.0 Preview is available only on Azure AI Foundry as a preview service (https://ai.azure.com/explore/aiservices/vision/document/extraction)  

For migration from these DI versions to Content Understanding Preview.2, this tool first converts the DI dataset to a CU-compatible format. Once converted, you can optionally create a Content Understanding Analyzer trained on the converted CU dataset. Additionally, you may test this model to ensure its quality.

## Details About the Tools

Below is a detailed breakdown of the three CLI tools and their capabilities:

* **di_to_cu_converter.py**  
     * This CLI tool performs the initial migration step by converting your labeled Document Intelligence dataset into a Content Understanding compatible dataset. It maps the following files accordingly:  
       - fields.json → analyzer.json  
       - labels.json (DI) → labels.json (CU)  
       - ocr.json → result.json  
     * Depending on the DI version, it uses either [cu_converter_neural.py](cu_converter_neural.py) or [cu_converter_generative.py](cu_converter_generative.py) to convert fields.json and labels.json.  
     * For OCR conversion, the tool creates a sample CU analyzer to collect raw OCR results via Analyze requests for each original file in the DI dataset. Since the sample analyzer contains no fields, the result.json files also contain no fields. For more details, see [get_ocr.py](get_ocr.py).

* **create_analyzer.py**  
     * After dataset conversion, this CLI tool creates a CU analyzer based on the converted dataset.

* **call_analyze.py**  
     * This CLI tool tests the migration by analyzing documents with the created analyzer to verify its quality.

## Setup

To set up this tool, follow these steps:

1. Install dependencies by running:  
   `pip install -r ./requirements.txt`

2. Rename the file **.sample_env** to **.env**

3. Update the following values in the **.env** file:  
   - **HOST:** Update with your Azure AI service endpoint (omit the trailing slash).  
     Example: `https://sample-azure-ai-resource.services.ai.azure.com`  
     ![Azure AI Service](assets/sample-azure-resource.png)  
     ![Azure AI Service Endpoints](assets/endpoint.png)
   - **SUBSCRIPTION_KEY:** Update with your Azure AI Service API Key or Subscription ID for authentication.  
     - Locate your API Key here: ![Azure AI Service Endpoints With Keys](assets/endpoint-with-keys.png)  
     - If using Azure Active Directory (AAD), use your Subscription ID: ![Azure AI Service Subscription ID](assets/subscription-id.png)  
   - **API_VERSION:** This must remain set to convert the dataset to CU Preview.2 (no changes required).

## How to Locate Your Document Field Extraction Dataset for Migration

To migrate your Document Field Extraction dataset from AI Foundry, follow these steps:

1. On the bottom left of your Document Field Extraction project page, select **Management Center**.  
   ![Management Center](assets/management-center.png)  
2. On the Management Center page, select **View All** under the Connected Resources section.  
   ![Connected Resources](assets/connected-resources.png)  
3. Locate the resource of type **Azure Blob Storage**. The resource's target URL contains your dataset's storage account (highlighted in yellow) and blob container (highlighted in blue).  
   ![Manage Connections](assets/manage-connections.png)  
4. Using these values, navigate to your blob container. Select the **labelingProjects** folder, then select the folder with the blob container's name. Inside, you will find the project's contents in the **data** folder.

Example of a sample Document Field Extraction project stored location:  
![Azure Portal](assets/azure-portal.png)

## How to Find Your Source and Target SAS URLs

To migrate, you must specify the source SAS URL (location of your Document Intelligence dataset) and target SAS URL (location for your Content Understanding dataset).

To obtain the SAS URL for a file or folder (used in container URL arguments), follow these steps:

1. In the Azure Portal, open your storage account, then select **Storage Browser** from the left pane.  
   ![Storage Browser](assets/storage-browser.png)
2. Select the source or target blob container (for your DI or CU dataset). Click the extended menu and select **Generate SAS**.  
   ![Generate SAS](assets/generate-sas.png)
3. Configure permissions and expiry for your SAS URL accordingly:  
   - For the DI source dataset, select: **Read** & **List** permissions  
   - For the CU target dataset, select: **Read**, **Add**, **Create**, & **Write** permissions  

4. Click **Generate SAS Token and URL**, then copy the URL shown under **Blob SAS URL**.  
   ![Generate SAS Pop-Up](assets/generate-sas-pop-up.png)

Notes:  
- Since SAS URLs do not point to specific folders, specify the correct dataset folder with the `--source-blob-folder` or `--target-blob-folder` arguments to ensure the correct path.  
- To get a SAS URL for a single file, navigate to that file and repeat these steps, for example:  
  ![Generate SAS for Individual File](assets/individual-file-generate-sas.png)

## How to Run

To run the three tools, use the commands below. For readability, the commands are shown split across lines—remove line breaks before executing.

_**Note:** Use quotes `""` when inserting URLs._

### 1. Convert Document Intelligence to Content Understanding Dataset

For migrating a _DI 3.1/4.0 GA Custom Extraction_ dataset, run:

```
python ./di_to_cu_converter.py --DI-version neural --analyzer-prefix mySampleAnalyzer 
--source-container-sas-url "https://sourceStorageAccount.blob.core.windows.net/sourceContainer?sourceSASToken" --source-blob-folder diDatasetFolderName 
--target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" --target-blob-folder cuDatasetFolderName
```

- Specifying an analyzer prefix is required. Because no "doc_type" is defined in `fields.json`, the created analyzer ID will be the specified prefix.

For migrating a _DI 4.0 Preview Document Field Extraction_ dataset, run:

```
python ./di_to_cu_converter.py --DI-version generative --analyzer-prefix mySampleAnalyzer 
--source-container-sas-url "https://sourceStorageAccount.blob.core.windows.net/sourceContainer?sourceSASToken" --source-blob-folder diDatasetFolderName 
--target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" --target-blob-folder cuDatasetFolderName
```

- Specifying an analyzer prefix is optional. To create multiple analyzers from the same `analyzer.json`, provide a prefix. If specified, the analyzer ID becomes `analyzer-prefix_doc-type`; otherwise, it remains the `doc_type` in `fields.json`.

_**Note:** Only one analyzer can be created per analyzer ID._

### 2. Create an Analyzer

To create an analyzer from the converted CU `analyzer.json`, run:

```
python ./create_analyzer.py 
--analyzer-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer/cuDatasetFolderName/analyzer.json?targetSASToken" 
--target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" 
--target-blob-folder cuDatasetFolderName
```

- The `analyzer.json` file is stored in the specified target container and folder. Obtain its SAS URL accordingly.  
- Use the analyzer ID output from this step when running `call_analyze.py`.

Example output:  
![Sample Analyzer Creation](assets/analyzer.png)

### 3. Run Analyze

To analyze a specific PDF or original file, run:

```
python ./call_analyze.py --analyzer-id mySampleAnalyzer 
--pdf-sas-url "https://storageAccount.blob.core.windows.net/container/folder/sample.pdf?SASToken" 
--output-json "./desired-path-to-analyzer-results.json"
```

- Use the analyzer ID created in the previous step for the `--analyzer-id` argument.  
- The `--output-json` argument is optional; by default, output is saved in `./sample_documents/analyzer_result.json`.

## Possible Issues

### Creating an Analyzer

For **400** errors, verify:  
- The endpoint is valid, e.g.,  
  `https://yourEndpoint/contentunderstanding/analyzers/yourAnalyzerID?api-version=2025-05-01-preview`  
- Your converted CU dataset meets naming constraints. Check all fields in `analyzer.json` and modify manually if necessary:  
  - Field names start with a letter or underscore  
  - Field names are 1–64 characters in length  
  - Only letters, numbers, and underscores used  
- Your analyzer ID meets these requirements:  
  - Length between 1 and 64 characters  
  - Only letters, numbers, dots, underscores, and hyphens used  

A **401** error indicates authentication failure. Confirm your API key and/or subscription ID are correct and have access to the specified endpoint.

A **409** error means the analyzer ID is already in use. Try another analyzer ID.

### Calling Analyze

- A **400** error suggests a possibly incorrect endpoint or SAS URL. Confirm your endpoint format:  
  `https://yourendpoint/contentunderstanding/analyzers/yourAnalyzerID:analyze?api-version=2025-05-01-preview`  
  Also verify the SAS URL for the document under analysis is correct.
- A **401** error means authentication failed. Confirm API key and/or subscription ID validity and access permissions.
- A **404** error means no analyzer exists with the specified analyzer ID. Use the correct analyzer ID or create the analyzer before retrying.

## Points to Note

1. Use Python version 3.9 or above.
2. Signature field types (found in previous DI versions) are not yet supported in Content Understanding; these will be ignored during migration when creating the analyzer.
3. The content of training documents is retained in CU model metadata under storage. More information:  
   https://learn.microsoft.com/en-us/legal/cognitive-services/content-understanding/transparency-note?toc=%2Fazure%2Fai-services%2Fcontent-understanding%2Ftoc.json&bc=%2Fazure%2Fai-services%2Fcontent-understanding%2Fbreadcrumb%2Ftoc.json  
5. All data conversion targets Content Understanding preview.2 version only.