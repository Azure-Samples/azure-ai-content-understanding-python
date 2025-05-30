# Document Intelligence to Content Understanding Migration Tool (Python)

Welcome! We've created this tool to help convert your Document Intelligence (DI) datasets to Content Understanding (CU) **Preview.2** format, as seen in AI Foundry. The following DI versions are supported:
- DI 3.1/4.0 GA CustomNeural (seen in Document Intelligence Studio)
- DI 4.0 Preview CustomGen (seen in Document Field Extraction projects)

To help you identify which version of Document Intelligence your dataset is in, please consult the sample documents provided under this folder to determine which format matches that of yours. Additionally, you can also identify the version through your DI project's UX as well. For instance, DI CustomNeural is a part of Document Intelligence Studio (i.e. https://documentintelligence.ai.azure.com/studio) and DI CustomGen is only a part of Azure AI Foundry (i.e. https://ai.azure.com/explore/aiservices/vision/document/extraction). 

For migration from these DI versions to Content understanding Preview.2, this tool first needs to convert the DI dataset to a CU compatible format. Once converted, you have the option to create a Content Understanding Analyzer, which will be trained on the converted CU dataset. Additionally, you can further test this model to ensure its quality.

## Details About the Tools
To provide you with some further details, here is a more intricate breakdown of each of the 3 CLI tools and their capabilities:
* **di_to_cu_converter.py**:
     * This CLI tool conducts your first step of migration. The tool refers to your labelled Document Intelligence dataset and converts it into a CU format compatible dataset. Through this tool, we map the following files accordingly: fields.json to analyzer.json, DI labels.json to CU labels.json, and ocr.json to result.json.
     * Depending on the DI version you wish to migrate from, we use [cu_converter_customNeural.py](cu_converter_customNeural.py) and [cu_converter_customGen.py](cu_converter_customGen.py) accordingly to convert your fields.json and labels.json files.
     * For OCR conversion, the tool creates a sample CU analyzer to gather raw OCR results via an Analyze request for each original file in the DI dataset. Additionally, since the sample analyzer contains no fields, we get the results.json files without any fields as well. For more details, please refer to [get_ocr.py](get_ocr.py).
* **create_analyzer.py**:
     * Once the dataset is converted to CU format, this CLI tool creates a CU analyzer while referring to the converted dataset. 
* **call_analyze.py**:
     * This CLI tool can be used to ensure that the migration has successfully completed and to test the quality of the previously created analyzer.

## Setup
To setup this tool, you will need to do the following steps:
1. Run the requirements.txt file to install the needed dependencies via **pip install -r ./requirements.txt**
2. Rename the file **.sample_env** to **.env**
3. Replace the following values in the **.env** file:
   - **HOST:** Update this to your Azure AI service endpoint.
       - Ex: "https://sample-azure-ai-resource.services.ai.azure.com".
       - Avoid the "/" at the end.
         ![Alt text](assets/sample-azure-resource.png "Azure AI Service")
         ![Alt text](assets/endpoint.png "Azure AI Service Enpoints")
   - **SUBSCRIPTION_KEY:** Update this to your Azure AI Service's API Key or Subscription ID to identify and authenticate the API request.
       - You can locate your API KEY here: ![Alt text](assets/endpoint-with-keys.png "Azure AI Service Enpoints With Keys")
       - If you are using AAD, please refer to your Subscription ID:  ![Alt text](assets/subscription-id.png "Azure AI Service Subscription ID")
   - **API_VERSION:** This version ensures that you are converting the dataset to CU Preview.2. No changes are needed here.

## How to Find Your Document Field Extraction Dataset in Azure Portal
If you are trying to migrate Document Extraction dataset from AI Foundry (customGen), please also refer to the following steps:
1. Navigate to the Management Center of your Document Extraction project. It should be on your bottom left. 
    ![Alt text](assets/management-center.png "Management Center")
2. When you get to the Management Center, you should see a section for Connected Resources. Please select "View All".
   ![Alt text](assets/connected-resources.png "Connected Resources")
3. This page shows you all the Azure resources and their locations. The "Target" refers to the URL for each Resource. None of these resources are the location of your DI dataset, but instead will lead us to it. We want to pay particular intention to the resources that are of type Blob Storage. The target of these Blob Storages will be the same, apart from the suffix of "-blobstore" on one of the resources.
   ![Alt text](assets/manage-connections.png "Manage Connections")
   Using the above image, the yellow highlight shows the storage account that your DI dataset is located in. Additionally, your DI dataset's blob container will be the blue highlight + "-di".
   Using these two values, please navigate to the above mentioned blob container. From there, you will notice a labelingProjects folder and inside a folder with the same name as the blue highlight. Inside this will be a data folder, which will contain the contents of your Document Extraction project. Please refer to this as your source.
   For the example Document Extraction project, this will be where the Document Extraction project is stored: 
   ![Alt text](assets/azure-portal.png "Azure Portal")

## How to Find Your Source and Target SAS URLs
To run the following tools, you will need to specify your source and target SAS URLs, along with their folder prefix.
To clarify, your source refers to the location of your DI dataset and your target refers to the location you wish to store your CU dataset at.

To find any SAS URL:

1. Navigate to the storage account in Azure Portal and click on "Storage Browser" on the left-hand side
   ![Alt text](assets/storage-browser.png "Storage Browser")
2. From here, use the "Blob Containers" to select the container where your dataset either is located (for DI) or should be saved to (for CU). Click on the 3 dots to the side, and select "Generate SAS"
    ![Alt text](assets/generate-sas.png "Generate SAS")
3. Then, you will be shown a side window where you can configure your permissions and expiry of the SAS URL.

   For the DI dataset, which is your source, please select the following permissions from the drop-down: _**Read & List**_

   For the CU dataset, which is your target, please select the following permissions from the drop-down: _**Read, Add, Create, & Write**_

   Once configured, please select "Generate SAS Token and URL" & copy the URL shown in "Blob SAS URL"

   ![Alt text](assets/generate-sas-pop-up.png "Generate SAS Pop-Up")

   This URL is what you will use when you have to specify any of the container url arguments

To get the SAS URL of a certain file, as you will need for running create_analyzer.py or call_analyze.py, follow the same steps as above. The only difference is you will need to navigate to the specific file to then click on the 3 dots and later, "Generate SAS."
![Alt text](assets/individual-file-generate-sas.png "Generate SAS for Individual File")

And lastly, the SAS URL does not specify a specific folder. To ensure that we are reading from and writing to the specific folder you wish, please enter in the DI dataset blob folder or the intended CU dataset folder whenever --source-blob-folder or --target-blob-folder is needed. 

## How to Run 
To run the 3 tools, you will need to follow these commands. Since these commands are incredibly long, for easy viewing we've split them into multiple lines. Please remove the extra spaces before running. 

_**NOTE:** When entering a URL, please use "" as the examples show you._

### 1. Running DI to CU Dataset Conversion

To convert a _DI 3.1/4.0 GA CustomNeural_ dataset, please run this command:

    python ./di_to_cu_converter.py --DI-version CustomNeural --analyzer-prefix mySampleAnalyzer 
    --source-container-sas-url "https://sourceStorageAccount.blob.core.windows.net/sourceContainer?sourceSASToken" --source-blob-folder diDatasetFolderName 
    --target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" --target-blob-folder cuDatasetFolderName

If you are using CustomNeural, please be sure to specify the analyzer prefix, as it is crucial for creating an analyzer. This is because there is no "doc_type" or any identification provided in CustomNeural. The created analyzer will have an analyzer ID of the specified analyzer-prefix. 

To convert a _DI 4.0 Preview CustomGen_, run this command: 

    python ./di_to_cu_converter.py --DI-version CustomGen --analyzer-prefix mySampleAnalyzer 
    --source-container-sas-url "https://sourceStorageAccount.blob.core.windows.net/sourceContainer?sourceSASToken" --source-blob-folder diDatasetFolderName 
    --target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" --target-blob-folder cuDatasetFolderName

Specifying an analyzerPrefix isn't necessary for CustomGen, but is needed if you wish to create multiple analyzers from the same analyzer.json. This is because the analyzer ID used will be the "doc_type" value specified in the fields.json. However, if an analyzer prefix is provided, the analyzer ID will then become analyzer-prefix_doc-type. 

_**NOTE:** You are only allowed to create one analyzer per analyzer ID._

### 2. Creating An Analyzer

To create an analyzer using the converted CU analyzer.json, please run this command:

    python ./create_analyzer.py 
    --analyzer-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer/cuDatasetFolderName/analyzer.json?targetSASToken" 
    --target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" 
    --target-blob-folder cuDatasetFolderName

Your analyzer.json will be stored in your target storage account's target container, specifically in the target blob folder that you have specified. Please get the SAS URL for the analyzer.json file from there.

In the output, you will see the analyzer ID of the created Analyzer, please remember this when using the call_analyze.py tool. 

Ex:

![Alt text](assets/analyzer.png "Sample Analyzer Creation")

### 3. Calling Analyze

To Analyze a specific PDF or original file, please run this command:

    python ./call_analyze.py --analyzer-id mySampleAnalyzer 
    --pdf-sas-url "https://storageAccount.blob.core.windows.net/container/folder/sample.pdf?SASToken 
    --output-json "./desired-path-to-analyzer-results.json"

For the --analyzer-id argument, please input the analyzer ID of the created Analyzer. 
Additionally, specifying the --output-json isn't neccesary. The default location is "./sample_documents/analyzer_result.json".

## Possible Issues
These are some issues that you might encounter when creating an analyzer or calling analyze. 
### Creating an Analyzer
For any **400** Error, please validate the following:
- Make sure that your endpoint is correct. It should be something like _https://yourEndpoint/contentunderstanding/analyzers/yourAnalyzerID?api-version=2025-05-01-preview_
- Make sure that all your fields in your analyzer.json meet these naming requirements. Your converted dataset might not work because CU has more naming constraints, thus you might need to manually make these changes.
  
  - Starts only with a letter or an underscore
  - Is in between 1 to 64 characters long
  - Only uses letters, numbers, and underscores
- Make sure that your analyzer ID specified meets these naming requirements
  - Is in between 1 to 64 characters long
  - Only uses letters, numbers, dots, underscores, and hyphens

If you get a **401** error, make sure that your API key or subscription ID is correct and that you have access to the endpoint you've specified. This is an authentication error. 

If you get a **409** error while creating your analyzer, that means that you have already created an analyzer with that analyzer ID. Please try using another ID.
### Calling Analyze
- A **400** Error implies a potentially incorrect endpoint or SAS URL. Ensure that your endpoint is valid _(https://yourendpoint/contentunderstanding/analyzers/yourAnalyzerID:analyze?api-version=2025-05-01-preview)_ and that you are using the correct SAS URL for the document under analysis.
- A **401** Error implies a failure in authentication. Please ensure that your API key and/or subscription ID are correct and that you have access to the endpoint specified.
- A **404** Error implies that no analyzer exists with the analyzer ID you have specified. Mitigate it by calling the correct ID or creating an analyzer with such an ID. 

## Points to Note:
1. Make sure to use Python version 3.9 or above.
2. Signature fieldtypes (such as in custom extraction model version 4.0) are not supported in Content Understanding yet. Thus, during migration, these signature fields will be ignored when creating the analyzer.
3. When training a model with a CU dataset, the content of the documents will be retained in the CU model metadata under CU service storage, for reference. This is different from how it is in DI. 
4. All the data conversion will be for Content Understanding preview.2 version only. 
