# Document Intelligence to Content Understanding Migration Tool (Python)

Welcome! This tool helps convert your Document Intelligence (DI) datasets to the Content Understanding (CU) **Preview.2** 2025-05-01-preview format, as used in AI Foundry. The following DI versions are supported:

- Custom Extraction Model DI 3.1 GA (2023-07-31) to DI 4.0 GA (2024-11-30) (Document Intelligence Studio) — DI-version = neural
- Document Field Extraction Model 4.0 Preview (2024-07-31-preview) (AI Foundry/AI Services/Vision + Document/Document Field Extraction) — DI-version = generative

To identify which version your Document Intelligence dataset is, please consult the sample documents provided in this folder to find the matching format. You can also check your DI project’s user experience:

- Custom Extraction DI 3.1/4.0 GA is available in Document Intelligence Studio (https://documentintelligence.ai.azure.com/studio)
- Document Field Extraction DI 4.0 Preview is available only on Azure AI Foundry as a preview service (https://ai.azure.com/explore/aiservices/vision/document/extraction)

For migration from these DI versions to Content Understanding Preview.2, this tool first converts the DI dataset into a CU-compatible format. After conversion, you can create a Content Understanding Analyzer trained on the parsed CU dataset and test the model to verify quality.

## Tool Overview

Here’s a detailed breakdown of the three CLI tools included and their features:

* **di_to_cu_converter.py**  
  - This is the first step in migration. It reads your labeled Document Intelligence dataset and converts it to a CU-compatible dataset. Specifically, it maps:
    - `fields.json` → `analyzer.json`
    - DI `labels.json` → CU `labels.json`
    - `ocr.json` → `result.json`  
  - Depending on your DI version, it uses either [cu_converter_neural.py](cu_converter_neural.py) or [cu_converter_generative.py](cu_converter_generative.py) to convert `fields.json` and `labels.json`.  
  - For OCR conversion, it creates a sample CU analyzer to retrieve raw OCR results via Analyze requests for each original DI file. Since the sample analyzer has no fields, the resulting `result.json` contains no fields as well. See [get_ocr.py](get_ocr.py) for details.

* **create_analyzer.py**  
  - Once your dataset is converted into CU format, this tool creates a CU analyzer referring to the converted dataset.

* **call_analyze.py**  
  - This tool tests whether migration completed successfully and allows you to evaluate the created analyzer’s quality.

## Setup Instructions

Perform the following steps to set up the tool:

1. Install dependencies:  
   ```bash
   pip install -r ./requirements.txt
   ```
2. Rename `.sample_env` to `.env`
3. Update values in your `.env` file:  
   - **HOST:** Your Azure AI service endpoint (without trailing slash)  
     Example: `https://sample-azure-ai-resource.services.ai.azure.com`  
     ![Azure AI Service](assets/sample-azure-resource.png)  
     ![Azure AI Service Endpoints](assets/endpoint.png)  
   - **SUBSCRIPTION_KEY:** Your Azure AI Service API Key or Subscription ID to authenticate API requests.  
     - Locate your API Key: ![API Keys](assets/endpoint-with-keys.png)  
     - For AAD users, refer to your Subscription ID: ![Subscription ID](assets/subscription-id.png)  
   - **API_VERSION:** Should be set to the CU Preview.2 version (no changes needed).

## Locating Your Document Field Extraction Dataset for Migration

To migrate a Document Field Extraction dataset from AI Foundry, follow these steps:

1. On your project page, select **Management Center** (bottom left).  
   ![Management Center](assets/management-center.png)  
2. On the Management Center page, choose **View All** under Connected Resources.  
   ![Connected Resources](assets/connected-resources.png)  
3. Identify the resource with type **Azure Blob Storage**. Its URL contains your dataset’s storage account (highlighted in yellow) and blob container (highlighted in blue).  
   ![Manage Connections](assets/manage-connections.png)  
4. Navigate to your blob container using these details. Then open the `labelingProjects` folder, followed by the folder matching your container’s name. Here you will find your project contents inside the `data` folder.

Example:  
![Azure Portal](assets/azure-portal.png)

## Finding Your Source and Target SAS URLs

For migration, specify:

- **Source SAS URL**: Location of your DI dataset  
- **Target SAS URL**: Location where your CU dataset will be stored

To generate a SAS URL for a container, folder, or file:

1. In Azure Portal, open your storage account and select **Storage Browser** from the left pane.  
   ![Storage Browser](assets/storage-browser.png)  
2. Select the source or target blob container. Open the menu and choose **Generate SAS**.  
   ![Generate SAS](assets/generate-sas.png)  
3. Configure permissions and expiry:

   - For the DI **source** dataset: select **Read & List** permissions  
   - For the CU **target** dataset: select **Read, Add, Create, & Write** permissions  

4. Click **Generate SAS Token and URL** and copy the **Blob SAS URL**.  
   ![Generate SAS Pop-Up](assets/generate-sas-pop-up.png)

Notes:  
- Since SAS URLs do not point to specific folders, specify the dataset folder paths explicitly using `--source-blob-folder` and `--target-blob-folder`.  
- To get a SAS URL for a single file, navigate to that file and repeat the SAS generation steps:  
  ![Generate SAS for Individual File](assets/individual-file-generate-sas.png)

## How to Run the Tools

Commands below are split across lines for readability; remove line breaks before execution.

**Note:** Use double quotes (`""`) when entering URLs.

### 1. Convert Document Intelligence to Content Understanding Dataset

For migrating a **DI 3.1/4.0 GA Custom Extraction** dataset, run:

```
python ./di_to_cu_converter.py --DI-version neural --analyzer-prefix mySampleAnalyzer \
--source-container-sas-url "https://sourceStorageAccount.blob.core.windows.net/sourceContainer?sourceSASToken" --source-blob-folder diDatasetFolderName \
--target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" --target-blob-folder cuDatasetFolderName
```

**Important:** Specifying an `--analyzer-prefix` is required. Because `fields.json` lacks `doc_type` identifiers, the created analyzer ID will be the specified prefix.

For migrating a **DI 4.0 Preview Document Field Extraction** dataset, run:

```
python ./di_to_cu_converter.py --DI-version generative --analyzer-prefix mySampleAnalyzer \
--source-container-sas-url "https://sourceStorageAccount.blob.core.windows.net/sourceContainer?sourceSASToken" --source-blob-folder diDatasetFolderName \
--target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" --target-blob-folder cuDatasetFolderName
```

In this case, `--analyzer-prefix` is optional. Use it if creating multiple analyzers from the same `analyzer.json`. If provided, analyzer IDs will be `analyzer-prefix_doc-type`. Otherwise, the analyzer ID will be the `doc_type` from `fields.json`.

**Note:** Only one analyzer can be created per analyzer ID.

### 2. Create an Analyzer

Create a CU analyzer from the converted dataset using:

```
python ./create_analyzer.py \
--analyzer-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer/cuDatasetFolderName/analyzer.json?targetSASToken" \
--target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" \
--target-blob-folder cuDatasetFolderName
```

Retrieve the SAS URL for `analyzer.json` from the target blob container and folder.

Use the analyzer ID output from this step when running the `call_analyze.py` tool.

Example:  
![Sample Analyzer Creation](assets/analyzer.png)

### 3. Run Analyze

To analyze a specific PDF or original file:

```
python ./call_analyze.py --analyzer-id mySampleAnalyzer \
--pdf-sas-url "https://storageAccount.blob.core.windows.net/container/folder/sample.pdf?SASToken" \
--output-json "./desired-path-to-analyzer-results.json"
```

- Use the analyzer ID created in the previous step for `--analyzer-id`.  
- The `--output-json` argument is optional; the default output path is `./sample_documents/analyzer_result.json`.

## Possible Issues and Troubleshooting

### Creating an Analyzer

- **400 Bad Request**  
  Check:  
  - The endpoint URL format is correct, e.g.,  
    `https://yourEndpoint/contentunderstanding/analyzers/yourAnalyzerID?api-version=2025-05-01-preview`  
  - Your converted CU dataset adheres to naming constraints in `analyzer.json`. Fix any violations manually:  
    - Field names start with a letter or underscore  
    - Field names are 1–64 characters in length  
    - Only use letters, numbers, and underscores  
  - Your analyzer ID meets these requirements:  
    - Length between 1 and 64 characters  
    - Only letters, numbers, dots, underscores, and hyphens  

- **401 Unauthorized**  
  Indicates authentication failure. Ensure your API key and/or subscription ID are correct and you have access to the specified endpoint.

- **409 Conflict**  
  Analyzer ID is already in use. Try a different analyzer ID.

### Calling Analyze

- **400 Bad Request**  
  Likely causes: incorrect endpoint or SAS URL. Verify endpoint format:  
  `https://yourendpoint/contentunderstanding/analyzers/yourAnalyzerID:analyze?api-version=2025-05-01-preview`  
  and ensure SAS URL is correct for the document to analyze.

- **401 Unauthorized**  
  Authentication failure. Confirm API key and/or subscription ID validity and endpoint access.

- **404 Not Found**  
  Specified analyzer ID does not exist. Use the correct analyzer ID or create an analyzer with that ID.

## Additional Notes

1. Use Python version **3.9** or above.  
2. Signature field types from previous DI versions are **not supported** in Content Understanding. These fields will be ignored during migration when creating the analyzer.  
3. Training document content is preserved in Content Understanding model metadata under storage. For more information, see:  
   https://learn.microsoft.com/en-us/legal/cognitive-services/content-understanding/transparency-note?toc=%2Fazure%2Fai-services%2Fcontent-understanding%2Ftoc.json&bc=%2Fazure%2Fai-services%2Fcontent-understanding%2Fbreadcrumb%2Ftoc.json  
4. All data conversion targets **Content Understanding Preview.2** version only.