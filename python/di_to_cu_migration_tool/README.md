# Document Intelligence to Content Understanding Migration Tool (Python)

Welcome! We've created this tool to help convert your Document Intelligence (DI) datasets to Content Understanding (CU) **Preview.2** format, as seen in AI Foundry. The following DI versions are supported:
- DI 3.1/4.0 GA CustomNeural (seen in Document Intelligence Studio)
- DI 4.0 Preview CustomGen (seen in Document Extraction project)

To help you identify which version of Document Intelligence your dataset is in, please consult the sample documents provided under this folder to determine which format matches that of yours. 

Additionally, we have separate CLI tools to create a CU Analyzer using your provided AI Service endpoint and run Analyze on a given file using your analyzer.

## Details About the Tools
To give you some additional details, here is a more intricate breakdown of each of the 3 CLI tools and their capabilities:
* **di_to_cu_converter.py**:
     * This CLI tool handles the conversion of the dataset itself. In other words, it takes your DI dataset and converts it into a CU dataset. What this means is that your fields.json gets converted into analyzer.json, your DI labels.json gets converted into CU labels.json, and your ocr.json gets replaced with result.json.
     * To handle the conversion for fields.json and labels.json, we use the cu_converter_customGen.py and cu_converter_customNeural.py python classes. The class used depends on the DI version you have specified. This is why choosing the correct DI version is incredibly important.
     * To get the result.json, we take your DI dataset's original files and create a sample analyzer without any fields, allowing us to attain the raw OCR results for each original file via an Analyze request. The logic for this implementation is located in get_ocr.py.
* **create_analyzer.py**:
     * This CLI tool handles building an analyzer by calling the Content Understanding REST API. 
     * With di_to_cu_converter.py, this tool gives us a complete CU dataset. However, to build a model itself, the create_analyzer.py class is needed.
     * Additionally, the model will come "trained" as the entire converted CU dataset will be referenced when building the analyzer. 
* **call_analyze.py**:
     * This CLI tool handles analyzing a given PDF file by utilizing the previously created analyzer.
     * This is a great way to "test" the model by utilizing the Content Understanding REST API. 

## Setup
To setup this tool, you will need to do the following steps:
1. Run the requirements.txt file to install the needed dependencies via **pip install -r ./requirements.txt**
3. Rename the file **.sample_env** as **.env**
4. Replace the following values in your **.env** file as such:
   - **HOST:** Replace this with your Azure AI Service's AI Foundry endpoint. Be sure to remove the "/" at the end. 
       - Ex: "https://sample-azure-ai-resource.services.ai.azure.com"
         ![Alt text](https://github.com/Azure-Samples/azure-ai-content-understanding-python/blob/62b9642072bdddc7c1ff1541fb4b0319ce87c856/python/di_to_cu_migration_tool/assets/sample-azure-resource.png "Azure AI Service")
         ![Alt text](https://github.com/Azure-Samples/azure-ai-content-understanding-python/blob/e7eb604655b28fd8854a345729bf908376ae4bee/python/di_to_cu_migration_tool/assets/endpoint.png "Azure AI Service Enpoints")
   - **SUBSCRIPTION_KEY:** Replace this with your Azure AI Service's API Key or Subscription ID. This is used to identify and authenticate the API request.
       - If you have an API Key, it will show up here: ![Alt text](https://github.com/Azure-Samples/azure-ai-content-understanding-python/blob/6a0381c3ffc11f48eda3386f69673ddb11d12eab/python/di_to_cu_migration_tool/assets/endpoint-with-keys.png "Azure AI Service Enpoints With Keys")
       - If your service uses AAD, please instead fill this value with your Subscription ID:  ![Alt text](https://github.com/Azure-Samples/azure-ai-content-understanding-python/blob/62b9642072bdddc7c1ff1541fb4b0319ce87c856/python/di_to_cu_migration_tool/assets/subscription-id.png "Azure AI Service Subscription ID")
   - **API_VERSION:** Please leave this value as is. This ensures that you are converting to a CU Preview.2 dataset. 

## How to Find Your CustomGen DI Dataset in Azure Portal
If you are trying to migrate Document Extraction dataset from AI Foundry (customGen), please also refer to the following steps:
1. Navigate to the Management Center of your Document Extraction project. It should be on your bottom left. 
    ![Alt text](https://github.com/Azure-Samples/azure-ai-content-understanding-python/blob/b57d76e64bb0d10537bcbabfb184e42481265234/python/di_to_cu_migration_tool/assets/management-center.png "Management Center")
2. When you get to the Management Center, you should see a section for Connected Resources. Please select "View All".
   ![Alt text](https://github.com/Azure-Samples/azure-ai-content-understanding-python/blob/b57d76e64bb0d10537bcbabfb184e42481265234/python/di_to_cu_migration_tool/assets/connected-resources.png "Connected Resources")
3. This page shows you all the Azure resources and their locations. The "Target" refers to the URL for each Resource. None of these resources are the location of your DI dataset, but instead will lead us to it. We want to pay particular intention to the resources that are of type Blob Storage. The target of these Blob Storages will be the same, apart from the suffix of "-blobstore" on one of the resources.
   ![Alt text](https://github.com/Azure-Samples/azure-ai-content-understanding-python/blob/b57d76e64bb0d10537bcbabfb184e42481265234/python/di_to_cu_migration_tool/assets/manage-connections.png "Manage Connections")
   Using the above image, the yellow highlight shows the storage account that your DI dataset is located in. Additionally, your DI dataset's blob container will be the blue highlight + "-di".
   Using these two values, please navigate to the above mentioned blob container. From there, you will notice a labelingProjects folder and inside a folder with the same name as the blue highlight. Inside this will be a data folder, which will contain the contents of your Document Extraction project. Please refer to this as your source.
   For the example Document Extraction project, this will be where the Document Extraction project is stored: 
   ![Alt text](https://github.com/Azure-Samples/azure-ai-content-understanding-python/blob/b57d76e64bb0d10537bcbabfb184e42481265234/python/di_to_cu_migration_tool/assets/azure-portal.png "Azure Portal")

## How to Find Your Source and Target SAS URLs
To run the following tools, you will need to specify your source and target SAS URLs, along with their folder prefix.
To clarify, your source refers to the location of your DI dataset and your target refers to the location you wish to store your CU dataset at.

To find any SAS URL:

1. Navigate to the storage account in Azure Portal and click on "Storage Browser" on the left-hand side
   ![Alt text](https://github.com/Azure-Samples/azure-ai-content-understanding-python/blob/b57d76e64bb0d10537bcbabfb184e42481265234/python/di_to_cu_migration_tool/assets/storage-browser.png "Storage Browser")
2. From here, use the "Blob Containers" to select the container where your dataset either is located (for DI) or should be saved to (for CU). Click on the 3 dots to the side, and select "Generate SAS"
    ![Alt text](https://github.com/Azure-Samples/azure-ai-content-understanding-python/blob/b57d76e64bb0d10537bcbabfb184e42481265234/python/di_to_cu_migration_tool/assets/generate-sas.png "Generate SAS")
3. Then, you will be shown a side window where you can configure your permissions and expiry of the SAS URL.

   For the DI dataset, which is your source, please select the following permissions from the drop-down: _**Read & List**_

   For the CU dataset, which is your target, please select the following permissions from the drop-down: _**Read, Add, Create, & Write**_

   Once configured, please select "Generate SAS Token and URL" & copy the URL shown in "Blob SAS URL"

   ![Alt text](https://github.com/Azure-Samples/azure-ai-content-understanding-python/blob/b57d76e64bb0d10537bcbabfb184e42481265234/python/di_to_cu_migration_tool/assets/generate-sas-pop-up.png "Generate SAS Pop-Up")

   This URL is what you will use when you have to specify any of the container url arguments

To get the SAS URL of a certain file, as you will need for running create_analyzer.py or call_analyze.py, follow the same steps as above. The only difference is you will need to navigate to the specific file to then click on the 3 dots and later, "Generate SAS."
![Alt text](https://github.com/Azure-Samples/azure-ai-content-understanding-python/blob/b57d76e64bb0d10537bcbabfb184e42481265234/python/di_to_cu_migration_tool/assets/individual-file-generate-sas.png "Generate SAS for Individual File")

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

    python ./create_analyzer.py --analyzer-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer/cuDatasetFolderName/analyzer.json?targetSASToken" 
    --target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" --target-blob-folder cuDatasetFolderName

Your analyzer.json will be stored in your target storage account's target container, specifically in the target blob folder that you have specified. Please get the SAS URL for the analyzer.json file from there.

In the output, you will see the analyzer ID of the created Analyzer, please remember this when using the call_analyze.py tool. 

Ex:

![Alt text](https://github.com/Azure-Samples/azure-ai-content-understanding-python/blob/b57d76e64bb0d10537bcbabfb184e42481265234/python/di_to_cu_migration_tool/assets/analyzer.png "Sample Analyzer Creation")

### 3. Calling Analyze

To Analyze a specific PDF or original file, please run this command:

    python ./call_analyze.py --analyzer-id mySampleAnalyzer --pdf-sas-url "https://storageAccount.blob.core.windows.net/container/folder/sample.pdf?SASToken 
    --output-json "./desired-path-to-analyzer-results.json"

For the --analyzer-id argument, please input the analyzer ID of the created Analyzer. 
Additionally, specifying the --output-json isn't neccesary. The default location is "./sample_documents/analyzer_result.json".

## Possible Issues
These are some issues that you might encounter when creating an analyzer or calling analyze. 
### Creating an Analyzer
If you get a **400** Error, please be sure to check these following items:
- Make sure that your endpoint is correct. It should be something like _https://yourEndpoint/contentunderstanding/analyzers/yourAnalyzerID?api-version=2025-05-01-preview_
- Make sure that all your fields in your analyzer.json meet these naming requirements
  
  - Starts only with a letter or an underscore
  - Is in between 1 to 64 characters long
  - Only uses letters, numbers, and underscores
- Make sure that your analyzer ID specified meets these naming requirements
  - Is in between 1 to 64 characters long
  - Only uses letters, numbers, dots, underscores, and hyphens

If you get a **401** error, make sure that your API key or subscription ID is correct and that you have access to the endpoint you've specified. This is an authentication error. 

If you get a **409** error while creating your analyzer, that means that you have already created an analyzer with that analyzer ID. Please try using another ID.
### Calling Analyze
If you get a **400** Error, please be sure to check the following items:
- Make sure that your endpoint is correct. It should be something like _https://yourEndpoint/contentunderstanding/analyzers/yourAnalyzerID:analyze?api-version=2025-05-01-preview_
- Make sure that you've specified the correct SAS URL for the document you are analyzing

If you get a **401** error, make sure that your API key or subscription ID is correct and that you have access to the endpoint you've specified. This is an authentication error. 

If you get a **404** Error while trying to call analyze, that means that there is no analyzer with the analyzer ID you have specified. Please create an analyzer with such an ID. 
## Things of Note
- You will need to be using a version of Python above 3.9
- Fields with FieldType "signature," which are supported in 2024-11-30 Custom Neural, are not supported in the latest version of Content Understanding (2025-05-01-preview), and thus will be ignored when creating the analyzer
- We will only be providing data conversion to CU Preview.2
