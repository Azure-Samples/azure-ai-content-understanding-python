# Document Intelligence to Content Understanding Migration Tool (Python)

Welcome! This tool assists in converting your Document Intelligence (DI) datasets to the Content Understanding (CU) **Preview.2** 2025-05-01-preview format, as used in AI Foundry. The following DI versions are supported:

- Custom Extraction Model DI 3.1 GA (2023-07-31) to DI 4.0 GA (2024-11-30) (Document Intelligence Studio) → **DI-version = neural**
- Document Field Extraction Model 4.0 Preview (2024-07-31-preview) (AI Foundry/AI Services/Vision + Document/Document Field Extraction) → **DI-version = generative**

To identify which DI version your dataset uses, please refer to the sample documents provided in this folder to compare formats. You can also check your DI project's user experience (UX):

- Custom Extraction DI 3.1/4.0 GA is part of Document Intelligence Studio (https://documentintelligence.ai.azure.com/studio).
- Document Field Extraction DI 4.0 Preview is available only via Azure AI Foundry as a preview service (https://ai.azure.com/explore/aiservices/vision/document/extraction).

For migration to Content Understanding Preview.2, this tool first converts your DI dataset into a CU-compatible format. After conversion, you can create a Content Understanding Analyzer trained on the converted dataset, and optionally test the analyzer to verify its quality.

## Tool Details

This migration consists of three CLI tools:

- **di_to_cu_converter.py**  
  Performs the initial conversion from your labeled DI dataset to a CU-compatible dataset. Specifically, it maps:  
  - `fields.json` → `analyzer.json`  
  - DI `labels.json` → CU `labels.json`  
  - `ocr.json` → `result.json`  
  Depending on the DI version, it uses either [cu_converter_neural.py](cu_converter_neural.py) or [cu_converter_generative.py](cu_converter_generative.py) to convert the `fields.json` and `labels.json` files.  
  For OCR conversion, the tool creates a sample CU analyzer to extract raw OCR results via Analyze requests on each original DI file. Since this sample analyzer has no defined fields, corresponding `result.json` files contain only OCR data. See [get_ocr.py](get_ocr.py) for details.

- **create_analyzer.py**  
  Creates a CU analyzer based on the converted dataset.

- **call_analyze.py**  
  Tests the created analyzer on specified documents to verify successful migration and model quality.

## Setup Instructions

1. Install dependencies:  
   ```sh
   pip install -r ./requirements.txt
   ```
2. Rename the file `.sample_env` to `.env`.
3. Edit `.env` and update the following values:

   - **HOST:** Your Azure AI service endpoint (omit trailing slash).  
     Example:  
     `"https://sample-azure-ai-resource.services.ai.azure.com"`  
     ![Azure AI Service](assets/sample-azure-resource.png)  
     ![Azure Endpoints](assets/endpoint.png)

   - **SUBSCRIPTION_KEY:** Your Azure AI Service's API Key or Subscription ID used for authentication.  
     - API Key location:  
       ![API Key](assets/endpoint-with-keys.png)  
     - Subscription ID (if using AAD):  
       ![Subscription ID](assets/subscription-id.png)

   - **API_VERSION:** Leave as is for CU Preview.2 conversion.

## Locating Your Document Field Extraction Dataset for Migration

To migrate a Document Field Extraction dataset from AI Foundry:

1. On your Document Field Extraction project page, click **Management Center** (bottom left).  
   ![Management Center](assets/management-center.png)

2. In Management Center, under Connected Resources, click **View All**.  
   ![Connected Resources](assets/connected-resources.png)

3. Look for a resource of type **Azure Blob Storage**. Its target URL contains your dataset's storage account (highlighted in yellow) and blob container (highlighted in blue).  
   ![Manage Connections](assets/manage-connections.png)  
   Navigate to this blob container, then open the **labelingProjects** folder. Inside, find the folder named after your blob container, which contains all project data under its **data** folder.

For example, a sample Document Field Extraction project is shown here:  
![Azure Portal](assets/azure-portal.png)

## Finding Source and Target SAS URLs

To run migration, you need:

- **Source SAS URL:** Location of your DI dataset  
- **Target SAS URL:** Location where the CU dataset will be stored

To obtain the SAS URL for a file or folder:

1. In Azure Portal, go to your storage account and select **Storage Browser** from the left pane.  
   ![Storage Browser](assets/storage-browser.png)

2. Select the relevant blob container (source or target). Open the menu on the right and select **Generate SAS**.  
   ![Generate SAS](assets/generate-sas.png)

3. Configure permissions and expiry:

   - For the DI source dataset, select permissions: **Read & List**  
   - For the CU target dataset, select permissions: **Read, Add, Create, & Write**

   Click **Generate SAS Token and URL** and copy the URL shown under **Blob SAS URL**:  
   ![Generate SAS Pop-Up](assets/generate-sas-pop-up.png)

**Notes:**
- Since SAS URLs do not point to a specific folder, use the `--source-blob-folder` and `--target-blob-folder` arguments to specify the correct dataset folders.
- To generate a SAS URL for an individual file, navigate to that file and repeat the steps:  
  ![Generate SAS for Individual File](assets/individual-file-generate-sas.png)

## Usage Instructions

Below are the commands for running each tool. For readability, commands are split across lines—remove line breaks before running.

> **Note:** Wrap all URL arguments in double quotes `" "`.

### 1. Convert Document Intelligence Dataset to Content Understanding

For _DI 3.1/4.0 GA Custom Extraction_, run:

```sh
python ./di_to_cu_converter.py --DI-version neural --analyzer-prefix mySampleAnalyzer \
--source-container-sas-url "https://sourceStorageAccount.blob.core.windows.net/sourceContainer?sourceSASToken" --source-blob-folder diDatasetFolderName \
--target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" --target-blob-folder cuDatasetFolderName
```

- Specifying an `analyzer-prefix` is required, as `fields.json` lacks a `"doc_type"` for identification.
- The created analyzer will have an ID equal to the provided prefix.

For _DI 4.0 Preview Document Field Extraction_, run:

```sh
python ./di_to_cu_converter.py --DI-version generative --analyzer-prefix mySampleAnalyzer \
--source-container-sas-url "https://sourceStorageAccount.blob.core.windows.net/sourceContainer?sourceSASToken" --source-blob-folder diDatasetFolderName \
--target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" --target-blob-folder cuDatasetFolderName
```

- Specifying `analyzer-prefix` is optional.
- If provided, the analyzer ID will be `analyzer-prefix_doc-type`; if omitted, it will be the `doc_type` from `fields.json`.
- You may only create one analyzer per analyzer ID.

### 2. Create an Analyzer

Use the converted `analyzer.json` to create an analyzer:

```sh
python ./create_analyzer.py \
--analyzer-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer/cuDatasetFolderName/analyzer.json?targetSASToken" \
--target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" \
--target-blob-folder cuDatasetFolderName
```

- The `analyzer.json` file is stored in your specified target container and folder.
- Use the analyzer ID from the command output when running `call_analyze.py`.

Example output:  
![Sample Analyzer Creation](assets/analyzer.png)

### 3. Run Analyze

To analyze a specific document (e.g., PDF), run:

```sh
python ./call_analyze.py --analyzer-id mySampleAnalyzer \
--pdf-sas-url "https://storageAccount.blob.core.windows.net/container/folder/sample.pdf?SASToken" \
--output-json "./desired-path-to-analyzer-results.json"
```

- Use the analyzer ID created in the previous step.
- The `--output-json` argument is optional; by default, results will be saved to `./sample_documents/analyzer_result.json`.

## Troubleshooting

### Issues Creating an Analyzer

- **400 Bad Request** error:  
  - Verify that your endpoint URL is valid, e.g.,  
    `https://yourEndpoint/contentunderstanding/analyzers/yourAnalyzerID?api-version=2025-05-01-preview`  
  - Ensure `analyzer.json` follows naming constraints:  
    - Field names must start with a letter or underscore (`_`)
    - Length between 1 and 64 characters  
    - Only letters, numbers, and underscores allowed  
  - Analyzer ID also must:  
    - Be 1 to 64 characters in length  
    - Contain only letters, numbers, dots (`.`), underscores (`_`), and hyphens (`-`)

- **401 Unauthorized** error: Authentication failed. Confirm your API key or subscription ID and permissions for the endpoint.

- **409 Conflict** error: Analyzer ID already exists. Use a different analyzer ID.

### Issues When Calling Analyze

- **400 Bad Request** error:  
  - Endpoint or SAS URL might be incorrect. Verify endpoint matches the format:  
    `https://yourendpoint/contentunderstanding/analyzers/yourAnalyzerID:analyze?api-version=2025-05-01-preview`  
  - Ensure the SAS URL matches the document being analyzed.

- **401 Unauthorized** error: Authentication failure. Check API keys and access permissions.

- **404 Not Found** error: No analyzer exists for the specified analyzer ID. Confirm the ID or create the analyzer first.

## Additional Notes

1. Use Python 3.9 or newer.
2. Signature field types (present in earlier DI versions) are **not supported** in Content Understanding and will be ignored during migration.
3. Training document content is retained in CU model metadata under storage. More details:  
   https://learn.microsoft.com/en-us/legal/cognitive-services/content-understanding/transparency-note?toc=%2Fazure%2Fai-services%2Fcontent-understanding%2Ftoc.json&bc=%2Fazure%2Fai-services%2Fcontent-understanding%2Fbreadcrumb%2Ftoc.json
4. All data conversion is strictly for Content Understanding Preview.2 version only.