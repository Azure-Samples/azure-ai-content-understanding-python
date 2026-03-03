# Document Intelligence to Content Understanding Migration Tool (Python)

This tool converts labeled datasets from Document Intelligence (DI) custom extraction models into the Content Understanding (CU) **GA** 2025-11-01 format. The converted labeled data can then be used as a training knowledge source when creating Content Understanding analyzers on Microsoft Foundry, improving field extraction accuracy through in-context learning examples.

### Supported DI Model Types

| Source DI Version | --di-model-type Flag | Original UI |
|---|---|---|
| Custom Extraction Model DI 3.1 GA (2023-07-31) to DI 4.0 GA (2024-11-30) | `neural` | [Document Intelligence Studio](https://documentintelligence.ai.azure.com/studio) |
| Document Field Extraction Model 4.0 Preview (2024-07-31-preview) | `generative` | [Microsoft Foundry](https://ai.azure.com/explore/aiservices/vision/document/extraction) |

To identify which model type your dataset uses, check where your project was created: Custom Extraction DI 3.1/4.0 GA appears in [Document Intelligence Studio](https://documentintelligence.ai.azure.com/studio), while Document Field Extraction DI 4.0 Preview is available in [Microsoft Foundry](https://ai.azure.com/explore/aiservices/vision/document/extraction). You can also compare your dataset files against the sample documents in this folder.

### Migration Workflow

1. **Convert** your DI labeled dataset to CU format using `di_to_cu_converter.py`
2. **Review** the generated `analyzer.json` — update analyzer and field descriptions for best accuracy
3. **Create** a Content Understanding analyzer from the converted dataset using `create_analyzer.py`
4. **Verify** extraction quality by analyzing sample documents using `call_analyze.py`

For overall repository setup and broader guidance, see the main [README.md](../../README.md).

## Details About the Tools

This migration tool consists of three CLI scripts, intended to be run in order:

* **di_to_cu_converter.py** — Converts a DI labeled dataset to CU format  
    * Converts the labeled data for a DI custom extraction model into labeled data (a knowledge base) for Content Understanding. The tool maps DI files to CU equivalents:  
      - `fields.json` → `analyzer.json` (analyzer definition with field schemas)  
      - DI `labels.json` → CU `labels.json` (labeled training data)  
      - `ocr.json` → `result.json` (OCR / layout results)  
    * Depending on the DI version, the tool uses either [cu_converter_neural.py](cu_converter_neural.py) or [cu_converter_generative.py](cu_converter_generative.py) for the conversion logic.  
    * For OCR data conversion, it creates a temporary CU analyzer (with no fields) to re-extract raw OCR/layout results for each document. See [get_ocr.py](get_ocr.py) for details.
    * **Language model deployment overrides**: By default, the tool uses deployment names `gpt-4.1` for the completion (large language model) deployment and `text-embedding-3-large` for the embedding deployment. If your Microsoft Foundry deployments use different names, specify them with:
      - `--completion-deployment <name>` (defaults to `gpt-4.1`)
      - `--embedding-deployment <name>` (defaults to `text-embedding-3-large`)

* **create_analyzer.py** — Creates a CU analyzer from the converted dataset  
    * Sends the converted `analyzer.json` (including field schemas, descriptions, and training data references) to the Content Understanding service to create an analyzer.

* **call_analyze.py** — Tests the created analyzer  
    * Runs an analysis on a sample document using the created analyzer and returns the extracted fields, allowing you to verify migration quality.


## Setup

### Prerequisites

⚠️ **IMPORTANT: Before using this migration tool**, ensure your Microsoft Foundry resource is properly configured for Content Understanding:

1. **Configure default model deployments**: You must set default model deployments in your Content Understanding resource before creating or running analyzers.
   - Follow the prerequisites in the [REST API Quickstart Guide](https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/quickstart/use-rest-api?tabs=portal%2Cdocument)
   - For more details, see the [Models and Deployments Documentation](https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/concepts/models-deployments)

2. **Required language model deployments**: Your Foundry resource must have a **completion** (large language model) deployment and an **embedding** model deployment. By default, this tool expects deployments named `gpt-4.1` (completion) and `text-embedding-3-large` (embedding). If your deployments use different names, provide them with `--completion-deployment` and `--embedding-deployment` when running `di_to_cu_converter.py`.

3. **Verify your setup**: Confirm you can create and use a basic Content Understanding analyzer in your Microsoft Foundry resource before attempting migration. This ensures all prerequisites (authentication, model deployments, permissions) are met.

4. Complete all setup steps in the REST API documentation above, including authentication and model deployment configuration.

### Tool Setup

1. Install dependencies:
   ```bash
   pip install -r ./requirements.txt
   ```
2. Rename **.sample_env** to **.env**.
3. Edit the **.env** file with your resource details:  
   - **HOST:** Update to your Azure AI service endpoint.  
     - Example: `"https://sample-azure-ai-resource.services.ai.azure.com"`  
     - Do not include a trailing slash (`/`).  
       ![Azure AI Service](assets/sample-azure-resource.png)  
       ![Azure AI Service Endpoints](assets/endpoint.png)  
   - **SUBSCRIPTION_KEY:** Update to your Azure AI Service API Key or Subscription ID to authenticate the API requests.  
     - Locate your API Key here: ![Azure AI Service Endpoints With Keys](assets/endpoint-with-keys.png)  
     - If using Azure Active Directory (AAD), please refer to your Subscription ID: ![Azure AI Service Subscription ID](assets/subscription-id.png)  
   - **API_VERSION:** This is preset to the CU GA version (2025-11-01); no changes are needed.

## How to Locate Your Document Field Extraction Dataset for Migration

To migrate your Document Field Extraction dataset from Microsoft Foundry, please follow these steps:

1. On the bottom-left of your Document Field Extraction project page, please select **Management Center**.  
   ![Management Center](assets/management-center.png)  
2. On the Management Center page, please select **View All** in the Connected Resources section.  
   ![Connected Resources](assets/connected-resources.png)  
3. Locate the resource with type **Azure Blob Storage**. The resource's target URL contains your dataset’s storage account (highlighted in yellow) and blob container (in blue).  
   ![Manage Connections](assets/manage-connections.png)  
   Using these values, navigate to your blob container, then select the **labelingProjects** folder. Next, select the folder named after the blob container. Here you will find your project contents in the **data** folder.

Example of a sample Document Field Extraction project location:  
![Azure Portal](assets/azure-portal.png)

## How to Find Your Source and Target SAS URLs

The migration tool requires two SAS URLs:
- **Source SAS URL**: Points to the blob container holding your Document Intelligence labeled dataset.
- **Target SAS URL**: Points to the blob container where the converted Content Understanding dataset will be stored.

To generate SAS URLs:

1. In the Azure Portal, navigate to your storage account and select **Storage Browser** from the left pane.  
   ![Storage Browser](assets/storage-browser.png)  
2. Select the source or target blob container where your DI dataset resides or where your CU dataset will be stored. Click the extended menu and select **Generate SAS**.  
   ![Generate SAS](assets/generate-sas.png)  
3. Configure permissions and expiry for your SAS URL as follows:

   - For the **DI source dataset**, please select permissions: _**Read & List**_  

   - For the **CU target dataset**, please select permissions: _**Read, Add, Create, & Write**_  

   After configuring, click **Generate SAS Token and URL** and copy the URL shown under **Blob SAS URL**.  
   
   ![Generate SAS Pop-Up](assets/generate-sas-pop-up.png)

**Notes:**  
- SAS URLs point to the container level, not a specific prefix (folder path). To specify the exact prefix within the container where your source or target dataset resides, use `--source-blob-folder` and `--target-blob-folder`.  
- To generate a SAS URL for a specific file, navigate directly to that file and repeat the process, for example:  
  ![Generate SAS for Individual File](assets/individual-file-generate-sas.png)

## How to Run

Below are example commands for each of the three tools. Commands are split across multiple lines using `\` for readability.

_**NOTE:** Always enclose SAS URLs in double quotes (`""`) to prevent shell interpretation of special characters._

### 1. Convert Document Intelligence Labeled Data to Content Understanding Knowledge Base

This command converts the labeled data from a Document Intelligence (DI) custom extraction model into a Content Understanding (CU) knowledge base format. After conversion, you can use the converted labeled data to create a Content Understanding analyzer with training data.

- **Source**: The DI labeled dataset located in the blob container specified by `--source-container-sas-url`, under the blob prefix specified by `--source-blob-folder` (e.g., `myDIProject/data`).
- **Target**: The converted CU knowledge base will be written to the blob container specified by `--target-container-sas-url`, under the blob prefix specified by `--target-blob-folder` (e.g., `myCUDataset`).

#### Migrating a DI 3.1/4.0 GA Custom Neural Extraction dataset

```
python ./di_to_cu_converter.py --di-model-type neural --analyzer-prefix mySampleAnalyzer \
--source-container-sas-url "https://sourceStorageAccount.blob.core.windows.net/sourceContainer?sourceSASToken" \
--source-blob-folder diDatasetPrefix \
--target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" \
--target-blob-folder cuDatasetPrefix
```

If your large language model or embedding deployment names differ from the defaults (`gpt-4.1` and `text-embedding-3-large`), specify them explicitly:

```
python ./di_to_cu_converter.py --di-model-type neural --analyzer-prefix mySampleAnalyzer \
--source-container-sas-url "https://sourceStorageAccount.blob.core.windows.net/sourceContainer?sourceSASToken" \
--source-blob-folder diDatasetPrefix \
--target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" \
--target-blob-folder cuDatasetPrefix \
--completion-deployment "<your-completion-deployment-name>" \
--embedding-deployment "<your-embedding-deployment-name>"
```

For this migration, specifying an `--analyzer-prefix` is **required**. Since the DI 3.1/4.0 GA `fields.json` does not define a `doc_type`, the created analyzer ID will be the specified analyzer prefix.

#### Migrating a DI 4.0 Preview Document Field Extraction dataset

```
python ./di_to_cu_converter.py --di-model-type generative --analyzer-prefix mySampleAnalyzer \
--source-container-sas-url "https://sourceStorageAccount.blob.core.windows.net/sourceContainer?sourceSASToken" \
--source-blob-folder diDatasetPrefix \
--target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" \
--target-blob-folder cuDatasetPrefix
```

If your large language model or embedding deployment names differ from the defaults (`gpt-4.1` and `text-embedding-3-large`), specify them explicitly:

```
python ./di_to_cu_converter.py --di-model-type generative --analyzer-prefix mySampleAnalyzer \
--source-container-sas-url "https://sourceStorageAccount.blob.core.windows.net/sourceContainer?sourceSASToken" \
--source-blob-folder diDatasetPrefix \
--target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" \
--target-blob-folder cuDatasetPrefix \
--completion-deployment "<your-completion-deployment-name>" \
--embedding-deployment "<your-embedding-deployment-name>"
```

For this migration, specifying an `--analyzer-prefix` is optional. If provided, the analyzer ID becomes `analyzer-prefix_doc-type`; otherwise, it defaults to the `doc_type` defined in `fields.json`. To create multiple analyzers from the same `analyzer.json`, you must provide an analyzer prefix.

_**NOTE:** Only one analyzer can be created per analyzer ID._

### 2. Create an Analyzer

After converting the dataset, use this command to create a Content Understanding analyzer from the converted `analyzer.json`. The command sends the analyzer definition—including field schemas, descriptions, and training data references—to the Content Understanding service.

```
python ./create_analyzer.py \
--analyzer-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer/cuDatasetPrefix/analyzer.json?targetSASToken" \
--target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" \
--target-blob-folder cuDatasetPrefix
```

The `analyzer.json` file is located in the target blob container under the prefix you specified during conversion. Obtain its SAS URL from there.

Use the analyzer ID printed in the output for the next step when running `call_analyze.py`.

> **💡 Important: Review Analyzer and Field Descriptions Before Creating the Analyzer**
>
> The Document Intelligence format **does not include descriptions** for the analyzer or individual fields. As a result, the converted `analyzer.json` will contain a **generic placeholder** analyzer description and **empty** field descriptions.
>
> The accuracy of your Content Understanding analyzer depends significantly on the quality of these descriptions, so we **strongly recommend** adding meaningful descriptions before creating the analyzer:
>
> - **Analyzer description** (`description` at the top level of `fieldSchema` in `analyzer.json`): Provide a clear summary of what the analyzer is designed to extract and what types of documents it processes.
> - **Field descriptions** (`description` on each field in the `fieldSchema`): Write a specific description for each field that explains what it represents and how to identify it in the source documents.
>
> Well-crafted descriptions help the underlying language model better understand the extraction task, leading to higher accuracy. You can edit `analyzer.json` directly in blob storage or download it, edit locally, and re-upload before running `create_analyzer.py`.

Example:  
![Sample Analyzer Creation](assets/analyzer.png)

### 3. Run Analyze

After creating the analyzer, use this command to verify the migration by analyzing a sample document. This sends the document to the Content Understanding service and returns the extracted fields, allowing you to assess the quality of the migrated analyzer.

```
python ./call_analyze.py --analyzer-id mySampleAnalyzer \
--document-sas-url "https://storageAccount.blob.core.windows.net/container/folder/sample.pdf?SASToken" \
--output-json "./desired-path-to-analyzer-results.json"
```

- `--analyzer-id`: The analyzer ID created in the previous step.
- `--document-sas-url`: A SAS URL pointing to the document you want to analyze (PDF, image, etc.).
- `--output-json` *(optional)*: Path for the output JSON file. Defaults to `./sample_documents/analyzer_result.json` if omitted.

Review the output to verify that the extracted fields match your expectations. If field accuracy is low, consider [reviewing and updating the analyzer and field descriptions](#2-create-an-analyzer) in `analyzer.json`, then re-create the analyzer.

## Possible Issues

Below are common issues you may encounter during migration.

### Creating an Analyzer

- **400 Bad Request**:  
  Validate the following:  
  - The endpoint URL is correct. Example:  
    `https://yourEndpoint/contentunderstanding/analyzers/yourAnalyzerID?api-version=2025-11-01`  
  - Your converted CU dataset respects the field naming constraints. If needed, manually correct the `analyzer.json` fields:  
    - Field names must start with a letter or underscore  
    - Field name length must be between 1 and 64 characters  
    - Only letters, numbers, and underscores are allowed  
  - Your Analyzer ID meets these requirements:  
    - Length must be between 1 and 64 characters  
    - Contains only letters, numbers, dots, underscores, and hyphens

- **401 Unauthorized**:  
  Authentication failure. Verify that your API Key and/or Subscription ID are correct and that you have access to the specified endpoint.

- **409 Conflict**:  
  An analyzer already exists with this ID. Use a different analyzer ID, or delete the existing one first.

### Calling Analyze

- **400 Bad Request**:  
  Verify that your endpoint and document SAS URL are correct:  
  `https://yourendpoint/contentunderstanding/analyzers/yourAnalyzerID:analyze?api-version=2025-11-01`

- **401 Unauthorized**:  
  Authentication failure. Verify your API Key and/or Subscription ID.

- **404 Not Found**:  
  The specified analyzer ID does not exist. Use the correct analyzer ID or create the analyzer first.

## Points to Note

1. **Python version**: Use Python 3.9 or higher.  
2. **Signature fields not supported**: Signature field types from previous DI versions are not yet supported in Content Understanding. These fields will be skipped during migration.  
3. **Review analyzer and field descriptions**: The DI format does not include descriptions, so the converted `analyzer.json` will have a generic placeholder analyzer description and empty field descriptions. Adding meaningful descriptions significantly improves extraction accuracy. See [Step 2: Create an Analyzer](#2-create-an-analyzer) for details.  
4. **Training data retention**: The content of your training documents is retained in the CU model's metadata under storage. For more details, see the [Content Understanding Transparency Note](https://learn.microsoft.com/en-us/legal/cognitive-services/content-understanding/transparency-note?toc=%2Fazure%2Fai-services%2Fcontent-understanding%2Ftoc.json&bc=%2Fazure%2Fai-services%2Fcontent-understanding%2Fbreadcrumb%2Ftoc.json).  
5. **API version**: All conversions target the Content Understanding GA (2025-11-01) API version.