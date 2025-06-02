# Document Intelligence to Content Understanding Migration Tool (Python)

Welcome! We've created this tool to help convert your Document Intelligence (DI) datasets to Content Understanding (CU) **Preview.2** 2025-05-01-preview format, as seen in AI Foundry. The following DI versions are supported:
- Custom Document DI 3.1 GA (2023-07-31) to DI 4.0 GA (2024-11-30) (seen in Document Intelligence Studio) --> DI-version = neural
- Custom Document 4.0 Preview (2024-07-31-preview) (seen in Document Field Extraction projects) --> DI-version = generative

To help you identify which version of Document Intelligence your dataset is in, please consult the sample documents provided under this folder to determine which format matches that of yours. Additionally, you can also identify the version through your DI project's UX as well. For instance, DI 3.1/4.0 GA is a part of Document Intelligence Studio (i.e., https://documentintelligence.ai.azure.com/studio) and DI 4.0 Preview.2 is only a part of Azure AI Foundry (i.e., https://ai.azure.com/explore/aiservices/vision/document/extraction). 

For migration from these DI versions to Content Understanding Preview.2, this tool first needs to convert the DI dataset to a CU compatible format. Once converted, you have the option to create a Content Understanding Analyzer, which will be trained on the converted CU dataset. Additionally, you can further test this model to ensure its quality.

## Details About the Tools
To provide you with some further details, here is a more intricate breakdown of each of the 3 CLI tools and their capabilities:
* **di_to_cu_converter.py**:
     * This CLI tool conducts your first step of migration. The tool refers to your labelled Document Intelligence dataset and converts it into a CU format compatible dataset. Through this tool, we map the following files accordingly: fields.json to analyzer.json, DI labels.json to CU labels.json, and ocr.json to result.json.
     * Depending on the DI version you wish to migrate from, we use [cu_converter_neural.py](cu_converter_neural.py) and [cu_converter_generative.py](cu_converter_generative.py) accordingly to convert your fields.json and labels.json files.
     * For OCR conversion, the tool creates a sample CU analyzer to gather raw OCR results via an Analyze request for each original file in the DI dataset. Additionally, since the sample analyzer contains no fields, we get the results.json files without any fields as well. For more details, please refer to [get_ocr.py](get_ocr.py).
* **create_analyzer.py**:
     * Once the dataset is converted to CU format, this CLI tool creates a CU analyzer while referring to the converted dataset. 
* **call_analyze.py**:
     * This CLI tool can be used to ensure that the migration has successfully completed and to test the quality of the previously created analyzer.

## Setup
To set up this tool, you will need to do the following steps:
1. Run the requirements.txt file to install the needed dependencies via **pip install -r ./requirements.txt**
2. Rename the file **.sample_env** to **.env**
3. Replace the following values in the **.env** file:
   - **HOST:** Update this to your Azure AI service endpoint.
       - Ex: "https://sample-azure-ai-resource.services.ai.azure.com"
       - Avoid the "/" at the end.
         ![Alt text](assets/sample-azure-resource.png "Azure AI Service")
         ![Alt text](assets/endpoint.png "Azure AI Service Endpoints")
   - **SUBSCRIPTION_KEY:** Update this to your Azure AI Service's API Key or Subscription ID to identify and authenticate the API request.
       - You can locate your API KEY here: ![Alt text](assets/endpoint-with-keys.png "Azure AI Service Endpoints With Keys")
       - If you are using AAD, please refer to your Subscription ID:  ![Alt text](assets/subscription-id.png "Azure AI Service Subscription ID")
   - **API_VERSION:** This version ensures that you are converting the dataset to CU Preview.2. No changes are needed here.

## How to Locate Your Document Field Extraction Dataset for Migration
To migrate your Document Field extraction dataset from AI Foundry, please follow the steps below:
1. On the bottom left of your Document Field Extraction project page, please select "Management Center."
    ![Alt text](assets/management-center.png "Management Center")
2. Now on the Management Center page, please select "View All" from the Connected Resources section.
   ![Alt text](assets/connected-resources.png "Connected Resources")
3. Within these resources, look for the resource with type "Azure Blob Storage." This resource's target URL contains the location of your dataset's storage account (in yellow) and blob container (in blue).
   ![Alt text](assets/manage-connections.png "Manage Connections")
   Using these values, navigate to your blob container. Then, select the "labelingProjects" folder. From there, select the folder with the same name as the blob container. Here, you'll locate all the contents of your project in the "data" folder.

   For example, the sample Document Extraction project is stored at
   ![Alt text](assets/azure-portal.png "Azure Portal")

## How to Find Your Source and Target SAS URLs
To run migration, you will need to specify the source SAS URL (location of your Document Intelligence dataset) and target SAS URL (location for your Content Understanding dataset).

To locate the SAS URL for a file or folder for any container URL arguments, please follow these steps:

1. Navigate to your storage account in Azure Portal, and from the left pane, select "Storage Browser."
   ![Alt text](assets/storage-browser.png "Storage Browser")
2. Select the source/target blob container for either where your DI dataset is present or where your CU dataset will be. Click on the extended menu on the side and select "Generate SAS."
    ![Alt text](assets/generate-sas.png "Generate SAS")
3. Configure the permissions and expiry for your SAS URL accordingly.

   For the DI source dataset, please select these permissions: _**Read & List**_

   For the CU target dataset, please select these permissions: _**Read, Add, Create, & Write**_

   Once configured, please select "Generate SAS Token and URL" & copy the URL shown under "Blob SAS URL."

   ![Alt text](assets/generate-sas-pop-up.png "Generate SAS Pop-Up")

Notes:

- Since SAS URL does not point to a specific folder, to ensure the correct path for source and target, please specify the correct dataset folder as --source-blob-folder or --target-blob-folder.
- To get the SAS URL for a single file, navigate to the specific file and repeat the steps above, such as:
  ![Alt text](assets/individual-file-generate-sas.png "Generate SAS for Individual File")

## How to Run 
To run the 3 tools, please refer to the following commands. For better readability, they are split across lines. Please remove this extra spacing before execution.

_**NOTE:** Use "" when entering in a URL._

### 1. Converting Document Intelligence to Content Understanding Dataset 

If you are migrating a _DI 3.1/4.0 GA Custom Document_ dataset, please run this command:

    python ./di_to_cu_converter.py --DI-version neural --analyzer-prefix mySampleAnalyzer 
    --source-container-sas-url "https://sourceStorageAccount.blob.core.windows.net/sourceContainer?sourceSASToken" --source-blob-folder diDatasetFolderName 
    --target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" --target-blob-folder cuDatasetFolderName

For migration of DI 3.1/4.0 GA, specifying an analyzer prefix is crucial for creating a CU analyzer. Since there's no "doc_type" defined for any identification in the fields.json, the created analyzer will have an analyzer ID of the specified analyzer prefix.

If you are migrating a _DI 4.0 Preview Custom Document_ dataset, please run this command: 

    python ./di_to_cu_converter.py --DI-version generative --analyzer-prefix mySampleAnalyzer 
    --source-container-sas-url "https://sourceStorageAccount.blob.core.windows.net/sourceContainer?sourceSASToken" --source-blob-folder diDatasetFolderName 
    --target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" --target-blob-folder cuDatasetFolderName

For migration of DI 4.0 Preview, specifying an analyzer prefix is optional. However, if you wish to create multiple analyzers from the same analyzer.json, please add an analyzer prefix. If provided, the analyzer ID will become analyzer-prefix_doc-type. Otherwise, it will simply remain as the doc_type in the fields.json. 

_**NOTE:** You are only allowed to create one analyzer per analyzer ID._

### 2. Creating an Analyzer

To create an analyzer using the converted CU analyzer.json, please run this command:

    python ./create_analyzer.py 
    --analyzer-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer/cuDatasetFolderName/analyzer.json?targetSASToken" 
    --target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" 
    --target-blob-folder cuDatasetFolderName

The analyzer.json file is stored in the specified target blob container and folder. Please get the SAS URL for the analyzer.json file from there.

Additionally, please use the analyzer ID from this output when running the call_analyze.py tool. 

Ex:

![Alt text](assets/analyzer.png "Sample Analyzer Creation")

### 3. Running Analyze

To analyze a specific PDF or original file, please run this command:

    python ./call_analyze.py --analyzer-id mySampleAnalyzer 
    --pdf-sas-url "https://storageAccount.blob.core.windows.net/container/folder/sample.pdf?SASToken 
    --output-json "./desired-path-to-analyzer-results.json"

For the --analyzer-id argument, please refer to the analyzer ID created in the previous step.
Additionally, specifying --output-json isn't necessary. The default location for the output is "./sample_documents/analyzer_result.json."

## Possible Issues
These are some issues that you might run into when creating an analyzer or running analyze. 
### Creating an Analyzer
For any **400** error, please validate the following:
- You are using a valid endpoint. Example: _https://yourEndpoint/contentunderstanding/analyzers/yourAnalyzerID?api-version=2025-05-01-preview_
- Your converted CU dataset may not meet the latest naming constraints. Please ensure that all the fields in your analyzer.json file meet these requirements. If not, please make the changes manually.

  - Field name only starts with a letter or an underscore
  - Field name length is between 1 and 64 characters
  - Only uses letters, numbers, and underscores
- Your analyzer ID meets these naming requirements
  - ID is between 1 and 64 characters long
  - Only uses letters, numbers, dots, underscores, and hyphens

A **401** error implies a failure in authentication. Please ensure that your API key and/or subscription ID are correct and that you have access to the endpoint specified.

A **409** error implies that the analyzer ID has already been used to create an analyzer. Please try using another ID.
### Calling Analyze
- A **400** error implies a potentially incorrect endpoint or SAS URL. Ensure that your endpoint is valid _(https://yourendpoint/contentunderstanding/analyzers/yourAnalyzerID:analyze?api-version=2025-05-01-preview)_ and that you are using the correct SAS URL for the document under analysis.
- A **401** error implies a failure in authentication. Please ensure that your API key and/or subscription ID are correct and that you have access to the endpoint specified.
- A **404** error implies that no analyzer exists with the analyzer ID you have specified. Mitigate it by calling the correct ID or creating an analyzer with such an ID. 

## Points to Note:
1. Make sure to use Python version 3.9 or above.
2. Signature field types (such as in the previous versions of DI) are not supported in Content Understanding yet. Thus, during migration, these signature fields will be ignored when creating the analyzer.
3. When training a model with a CU dataset, the content of the documents will be retained in the CU model metadata, under CU service storage specifically. This is different from how it is in DI. 
4. All the data conversion will be for Content Understanding preview.2 version only. 
