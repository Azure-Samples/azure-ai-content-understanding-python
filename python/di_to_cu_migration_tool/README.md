# Document Intelligence to Content Understanding Migration Tool (Python)

Welcome! This tool helps convert your Document Intelligence (DI) datasets to the Content Understanding (CU) **Preview.2** 2025-05-01-preview format, as used in AI Foundry. The following DI versions are supported:

- Custom Extraction Model DI 3.1 GA (2023-07-31) to DI 4.0 GA (2024-11-30) (Document Intelligence Studio) --> DI-version = neural  
- Document Field Extraction Model 4.0 Preview (2024-07-31-preview) (AI Foundry / AI Services / Vision + Document / Document Field Extraction) --> DI-version = generative

To identify the version of your Document Intelligence dataset, consult the sample documents in this folder to match your format. You can also verify the version by reviewing your DI project's user experience: for example, Custom Extraction DI 3.1/4.0 GA appears in Document Intelligence Studio (https://documentintelligence.ai.azure.com/studio), whereas Document Field Extraction DI 4.0 Preview is available only on Azure AI Foundry preview service (https://ai.azure.com/explore/aiservices/vision/document/extraction).

For migrating from these DI versions to Content Understanding Preview.2, this tool first converts the DI dataset into a CU-compatible format. After conversion, you can create a Content Understanding Analyzer trained on the converted CU dataset and test it to validate its quality.

## Details About the Tools

Here is a detailed breakdown of the three CLI tools and their functionality:

* **di_to_cu_converter.py**  
    * This CLI tool performs the first migration step. It converts your labeled Document Intelligence dataset into a CU-compatible dataset. The tool maps the following files accordingly:  
      - fields.json → analyzer.json  
      - DI labels.json → CU labels.json  
      - ocr.json → result.json  
    * Depending on the DI version, the tool uses either [cu_converter_neural.py](cu_converter_neural.py) or [cu_converter_generative.py](cu_converter_generative.py) to convert your fields.json and labels.json files.  
    * For OCR data conversion, it creates a sample CU analyzer to extract raw OCR results via an Analyze request for each original file in the DI dataset. Since the sample analyzer contains no fields, the resulting result.json files contain no fields as well. Refer to [get_ocr.py](get_ocr.py) for more details.

* **create_analyzer.py**  
    * After converting the dataset to CU format, this CLI tool creates a CU analyzer referring to the converted dataset.

* **call_analyze.py**  
    * This CLI tool tests that the migration completed successfully and assesses the quality of the created analyzer.

## Setup

Follow these steps to set up the tool:

1. Install dependencies by running:  
   `pip install -r ./requirements.txt`
2. Rename the file **.sample_env** to **.env**
3. Edit the **.env** file to update the following values:  
   - **HOST:** Update to your Azure AI service endpoint.  
     - Example: `"https://sample-azure-ai-resource.services.ai.azure.com"`  
     - Do not include a trailing slash (`/`).  
       ![Azure AI Service](assets/sample-azure-resource.png)  
       ![Azure AI Service Endpoints](assets/endpoint.png)  
   - **SUBSCRIPTION_KEY:** Update to your Azure AI Service API Key or Subscription ID to authenticate the API requests.  
     - Locate your API Key here: ![Azure AI Service Endpoints With Keys](assets/endpoint-with-keys.png)  
     - If using Azure Active Directory (AAD), refer to your Subscription ID: ![Azure AI Service Subscription ID](assets/subscription-id.png)  
   - **API_VERSION:** This is preset to the CU Preview.2 version; no changes are needed.

## How to Locate Your Document Field Extraction Dataset for Migration

To migrate your Document Field Extraction dataset from AI Foundry, follow these steps:

1. On the bottom-left of your Document Field Extraction project page, select **Management Center**.  
   ![Management Center](assets/management-center.png)  
2. On the Management Center page, select **View All** in the Connected Resources section.  
   ![Connected Resources](assets/connected-resources.png)  
3. Locate the resource with type **Azure Blob Storage**. The resource's target URL contains your dataset’s storage account (highlighted in yellow) and blob container (in blue).  
   ![Manage Connections](assets/manage-connections.png)  
   Using these values, navigate to your blob container, then select the **labelingProjects** folder. Next, select the folder named after the blob container. Here you will find your project contents in the **data** folder.

Example of a sample Document Field Extraction project location:  
![Azure Portal](assets/azure-portal.png)

## How to Find Your Source and Target SAS URLs

To run migration, you need to specify the source SAS URL (location of your Document Intelligence dataset) and the target SAS URL (location for your Content Understanding dataset).

To obtain SAS URLs for a file or folder for any container URL arguments, follow these steps:

1. In the Azure Portal, navigate to your storage account and select **Storage Browser** from the left pane.  
   ![Storage Browser](assets/storage-browser.png)  
2. Select the source or target blob container where your DI dataset resides or where your CU dataset will be stored. Click the extended menu and select **Generate SAS**.  
   ![Generate SAS](assets/generate-sas.png)  
3. Configure permissions and expiry for your SAS URL as follows:

   - For the **DI source dataset**, select permissions: _**Read & List**_  
   - For the **CU target dataset**, select permissions: _**Read, Add, Create, & Write**_  

   After configuring, click **Generate SAS Token and URL** and copy the URL shown under **Blob SAS URL**.  
   
   ![Generate SAS Pop-Up](assets/generate-sas-pop-up.png)

**Notes:**  
- SAS URLs do not specify a specific folder. To ensure the correct paths for source and target datasets, specify the dataset folder using `--source-blob-folder` and `--target-blob-folder`.  
- To generate a SAS URL for a specific file, navigate directly to that file and repeat the process, for example:  
  ![Generate SAS for Individual File](assets/individual-file-generate-sas.png)

## How to Run 

Below are example commands to run the three tools. For readability, commands are split across multiple lines; remove line breaks before execution.

_**NOTE:** Always enclose URLs in double quotes (`""`)._

### 1. Convert Document Intelligence to Content Understanding Dataset

If migrating a _DI 3.1/4.0 GA Custom Extraction_ dataset, run:

```
python ./di_to_cu_converter.py --DI-version neural --analyzer-prefix mySampleAnalyzer \
--source-container-sas-url "https://sourceStorageAccount.blob.core.windows.net/sourceContainer?sourceSASToken" --source-blob-folder diDatasetFolderName \
--target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" --target-blob-folder cuDatasetFolderName
```

For this migration, specifying an analyzer prefix is crucial for creating a CU analyzer. Since the fields.json does not define a "doc_type" for identification, the created analyzer ID will be the specified analyzer prefix.

If migrating a _DI 4.0 Preview Document Field Extraction_ dataset, run:

```
python ./di_to_cu_converter.py --DI-version generative --analyzer-prefix mySampleAnalyzer \
--source-container-sas-url "https://sourceStorageAccount.blob.core.windows.net/sourceContainer?sourceSASToken" --source-blob-folder diDatasetFolderName \
--target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" --target-blob-folder cuDatasetFolderName
```

For this migration, specifying an analyzer prefix is optional. However, to create multiple analyzers from the same analyzer.json, add an analyzer prefix. If provided, the analyzer ID becomes `analyzer-prefix_doc-type`; otherwise, it remains as the `doc_type` in fields.json.

_**NOTE:** Only one analyzer can be created per analyzer ID._

### 2. Create an Analyzer

After converting the CU analyzer.json, run:

```
python ./create_analyzer.py \
--analyzer-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer/cuDatasetFolderName/analyzer.json?targetSASToken" \
--target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" \
--target-blob-folder cuDatasetFolderName
```

The `analyzer.json` file is in the specified target blob container and folder. Obtain the SAS URL for `analyzer.json` from there.

Use the analyzer ID output here for the next step when running `call_analyze.py`.

Example:  
![Sample Analyzer Creation](assets/analyzer.png)

### 3. Run Analyze

To analyze a specific PDF or original file, run:

```
python ./call_analyze.py --analyzer-id mySampleAnalyzer \
--pdf-sas-url "https://storageAccount.blob.core.windows.net/container/folder/sample.pdf?SASToken" \
--output-json "./desired-path-to-analyzer-results.json"
```

For `--analyzer-id`, use the analyzer ID created in the prior step.

Specifying `--output-json` is optional; if omitted, the default output location is `./sample_documents/analyzer_result.json`.

## Possible Issues

Below are common issues you might encounter when creating an analyzer or running analysis.

### Creating an Analyzer

- **400 Bad Request** errors:  
  Validate the following:  
  - The endpoint URL is valid. Example:  
    `https://yourEndpoint/contentunderstanding/analyzers/yourAnalyzerID?api-version=2025-05-01-preview`  
  - Your converted CU dataset respects the naming constraints below. If needed, manually correct `analyzer.json` fields:  
    - Field names start with a letter or underscore  
    - Field name lengths are between 1 and 64 characters  
    - Only letters, numbers, and underscores are allowed  
  - Analyzer ID meets naming requirements:  
    - Length between 1 and 64 characters  
    - Only letters, numbers, dots, underscores, and hyphens allowed

- **401 Unauthorized**:  
  Authentication failure. Verify your API key and/or subscription ID are correct and have access to the endpoint.

- **409 Conflict**:  
  The analyzer ID has already been used. Try using a different analyzer ID.

### Calling Analyze

- **400 Bad Request**:  
  Possibly incorrect endpoint or SAS URL. Ensure your endpoint is valid:  
  `https://yourendpoint/contentunderstanding/analyzers/yourAnalyzerID:analyze?api-version=2025-05-01-preview`  
  Confirm you are using the correct SAS URL for the document.

- **401 Unauthorized**:  
  Authentication failure. Verify your API key and/or subscription ID.

- **404 Not Found**:  
  Analyzer with the specified ID does not exist. Use the correct analyzer ID or create an analyzer with that ID.

## Points to Note

1. Use Python version 3.9 or higher.  
2. Signature field types (e.g., in previous DI versions) are not yet supported in Content Understanding. These will be ignored during migration when creating the analyzer.  
3. The content of training documents is retained in Content Understanding model metadata, under storage specifically. More details at:  
   https://learn.microsoft.com/en-us/legal/cognitive-services/content-understanding/transparency-note?toc=%2Fazure%2Fai-services%2Fcontent-understanding%2Ftoc.json&bc=%2Fazure%2Fai-services%2Fcontent-understanding%2Fbreadcrumb%2Ftoc.json  
4. All conversions are for Content Understanding preview.2 version only.