# Document Intelligence to Content Understanding Migration Tool (Python)

Welcome! We've created this tool to help convert your Document Intelligence (DI) datasets to Content Understanding (CU) **Preview.2** format seen in AI Foundry. The following DI versions are supported:
- DI 3.1/4.0 GA CustomNeural (seen in Document Intelligence Studio)
- DI 4.0 Preview CustomGen (seen in Document Extraction project)
To help you identify which version of Document Intelligence your dataset is in, please consult the sample documents provided under this folder to determine which format matches that of yours. 

Additionally, this will automatically create a CU Analyzer using your provided AI Service endpoint and provide the option to run Analyze on a given file. 

## Setup
To setup this tool, you will need to do the following steps:
1. Run the requirements.txt to install the needed dependencies via **pip install -r ./requirements.txt**
2. Rename the file **.sample_env** as **.env**
3. Replace the following values in your **.env** file as such:
   - **HOST:** Replace this with your Azure AI Service's Content Understanding endpoint. Be sure to remove the "/" at the end. 
       - Ex: "https://aainatest422.services.ai.azure.com"
   - **SUBSCRIPTION_KEY:** Replace this with your name or alias, is used to identify who called the API request
       - Ex: "vannanaaina"
   - **SOURCE_BLOB_ACCOUNT_URL:** Replace this with the URL to your blob storage account that contains your DI dataset
       - Ex: "https://srcStorageAccountName.blob.core.windows.net"
   - **SOURCE_BLOB_CONTAINER_NAME:** Replace this with the container within your blob storage account that contains your DI dataset
       - Ex: "srcContainerName"
   - **SOURCE_BLOB_FOLDER_PREFIX:** Replace this with the path to your DI dataset, within your specified container
       - Ex: "src/path/to/folder"   
   - **SOURCE_BLOB_STORAGE_SAS_TOKEN:** If you prefer to use a SAS Token to authenticate into your source blob storage, please enter ONLY the token here and WITHOUT the leading "?".
     If you prefer to use Azure AAD to authenticate, you can remove this value alltogether or leave it blank (i.e. "")
   - **TARGET_BLOB_ACCOUNT_URL:** Replace this with the URL to the blob storage account that you wish to store your converted CU dataset
       - Ex: "https://destStorageAccountName.blob.core.windows.net"
   - **TARGET_BLOB_CONTAINER_NAME:** Replace this with the container within your target blob storage account where you wish to store your converted CU dataset
       - Ex: "destContainerName"
   - **TARGET_BLOB_FOLDER_PREFIX:** Replace this with the path to your CU dataset, within your specified container.
     If you end this string with a "/", it will create a folder inside of the path specified and store the dataset there. 
       - Ex: "dest/path/to/folder"
   - **TARGET_BLOB_STORAGE_SAS_TOKEN:** Replace this with the SAS Token to authenticate into your target blob storage. This is REQUIRED, you CANNOT use Azure AAD to authenticate.
     A SAS Token is needed for creating an Analyzer.
   - **ANALYZE_PDF_URL:** Replace this with the SAS URL to a file you wish to analyze (i.e. pdf, jpg, jpeg, etc.). If you wish to not run Analyze, you can leave this as empty (i.e. "") 
       - Ex: "https://srcStorageAccountName.blob.core.windows.net/srcContainerName/src/path/to/folder/test.pdf?SASToken"
   - **ANALYZE_RESULT_OUTPUT_JSON:** Replace this with where you wish to store the analyze results. The default is "./sample_documents/analyze_result.json". 

## How to Run 
To run this tool, you will be using the command line to run the following commands. 

To convert a _DI 3.1/4.0 GA CustomNeural_ dataset, run this command:

**python ./di_to_cu_migration_tool.py --DI-version CustomNeural --analyzer-prefix myAnalyzer**

If you are using CustomNeural, please be sure to specify the analyzer prefix, as it is crucial for creating an analyzer. 

To convert a _DI 4.0 Preview CustomGen_, run this command: 

**python ./di_to_cu_migration_tool.py --DI-version CustomGen --analyzer-prefix myAnalyzer**

Specifying an analyzerPrefix isn't necessary for CustomGen, but is needed if you wish to create multiple analyzers from the same analyzer.json.

After this command finishes running, you should be able to
- see a converted CU dataset (with analyzer.json, labels.json, result.json, and the original files) in your specified target blob storage
- see a created Analyzer with the mentioned Analyzer ID
- see the results of the Analyze call in where you specified ANALYZE_RESULT_OUTPUT_JSON to be

## Things of Note
- You will need to be using a version of Python above 3.9
- Fields with FieldType "signature," which are supported in 2024-11-30 Custom Neural, are not supported in the latest version of Content Understanding (2025-05-01-preview), and thus will be ignored when creating the analyzer
- We will only be providing data conversion to CU Preview.2
