# Document Intelligence to Content Understanding Migration Tool (Python)

Welcome! We've created this tool to help convert your Document Intelligence (DI) datasets to Content Understanding (CU) **Preview.2** format seen in AI Foundry. The following DI versions are supported:
- DI 3.1/4.0 GA CustomNeural (seen in Document Intelligence Studio)
- DI 4.0 Preview CustomGen (seen in Document Extraction project)

To help you identify which version of Document Intelligence your dataset is in, please consult the sample documents provided under this folder to determine which format matches that of yours. 

Additionally, we have separate CLI tools to create a CU Analyzer using your provided AI Service endpoint and run Analyze on a given file with your previously created analyzer.

## Details About the Tools
To give you some more details, here is a more intricate breakdown of each of the 3 CLI tools and their capabilities:
* **di_to_cu_converter.py**:
     * This CLI tool handles the conversion of the dataset itself. In other words, it takes your DI dataset and converts it into a CU dataset. What this means is that your fields.json gets converted into analyzer.json, your DI labels.json gets converted into CU labels.json, and your ocr.json gets replaced with result.json.
     * To handle the conversion for fields.json and labels.json, we use the cu_converter_customGen.py and cu_converter_customNeural.py python classes. The class used depends on the DI version you have specified. This is why choosing the correct DI version is incredibly important.
     * To get the result.json, we take your DI dataset's original files and create a sample analyzer without any fields, allowing us to attain the raw OCR results for each original file via an Analyze request. The logic for this implementation is located in get_ocr.py
* **create_analyzer.py**:
     * This CLI tool handles building an analyzer by calling the Content Understanding REST API. 
     * With di_to_cu_converter.py, this tool gives us a complete CU dataset. However, to build a model itself, the create_analyzer.py class is needed.
     * Additionally, the model will come "trained" as the entire converted CU dataset will be referenced when building the analyzer. 
* **call_analyze.py**:
     * This CLI tool handles analyzing a given PDF file by utilizing the previously created analyzer.
     * This is a great way to "test" the model by utilizing the Content Understanding REST API. 

## Setup
To setup this tool, you will need to do the following steps:
1. Run the requirements.txt to install the needed dependencies via **pip install -r ./requirements.txt**
2. Rename the file **.sample_env** as **.env**
3. Replace the following values in your **.env** file as such:
   - **HOST:** Replace this with your Azure AI Service's AI Foundry endpoint. Be sure to remove the "/" at the end. 
       - Ex: "https://user422.services.ai.azure.com"
         <img width="965" alt="image" src="https://github.com/user-attachments/assets/8eb64823-a55e-4a30-a50e-db6921537126" />
         <img width="605" alt="image" src="https://github.com/user-attachments/assets/ffd92606-dee1-48bc-a37d-5f1fe34cb52c" />
   - **SUBSCRIPTION_KEY:** Replace this with your Azure AI Service's API Key or Subscription ID. This is used to identify and authenticate the API request.
       - If you have an API Key, it will show up here: <img width="641" alt="image" src="https://github.com/user-attachments/assets/73f878fa-775a-40b2-85b0-d2b7353fe068" />
       - If your service uses AAD, please instead fill this value with your Subscription ID: <img width="974" alt="image" src="https://github.com/user-attachments/assets/2b80e05b-c248-4df4-a387-5088e08df75b" />
   - **API_VERSION:** Please leave this value as is. This ensures that you are converting to a CU Preview.2 dataset. 

## How to Find Your Source and Target SAS URLs
To run the following tools, you will need to specify your source and target SAS URLs, along with their folder prefix.
To clarify, your source refers to the location of your DI dataset and your target refers to the location you wish to store your CU dataset at.

To find any SAS URL:

1. Navigate to the storage account in Azure Portal and click on "Storage Browser" on the left-hand side
   <img width="1153" alt="image" src="https://github.com/user-attachments/assets/36657d72-dcd0-4479-8154-5fca1bd9cf54" />
2. From here, use the "Blob Containers" to select the container where your dataset either is located (for DI) or should be saved to (for CU). Click on the 3 dots to the side, and select "Generate SAS"
    <img width="1004" alt="image" src="https://github.com/user-attachments/assets/4b296eb9-d28d-4c50-83e0-a547eb3dc9a4" />
3. Then, you will be shown a side window as such, where you can configure your permissions and expiry of the SAS URL.

   For the DI dataset, please select the following permissions from the drop-down: Read & List

   For the CU dataset, please select the following permissions from the drop-down: Read, Add, & Create

   Once configured, please select "Generate SAS Token and URL" & copy the URL shown in "Blob SAS URL"

   <img width="439" alt="image" src="https://github.com/user-attachments/assets/8f7a4e57-346c-4aea-b480-afdf657d9e5a" />

   This URL is what you will use when you have to specify any of the container url arguments

To get the SAS URL of a certain file, as you will need for running call_analyze.py, follow the same steps as above. The only difference is you will need to navigate to the specific file to then click on the 3 dots and later, "Generate SAS."
<img width="788" alt="image" src="https://github.com/user-attachments/assets/204ecf7c-6f89-4c9f-a7e2-09b7b0373157" />

And lastly, the SAS URL does not specify a specific folder. To ensure that we are reading from and writing to the specific folder you wish, please enter in the DI dataset blob folder or the intended CU dataset folder whenever a --source-blob-folder or --target-blob-folder is needed. 

## How to Run 
To run the 3 tools, you will need to follow these commands.

_**NOTE:** When entering a URL, please use "" as the examples show you._

### 1. Running DI to CU Dataset Conversion

To convert a _DI 3.1/4.0 GA CustomNeural_ dataset, please run this command:

**python ./di_to_cu_converter.py --DI-version CustomNeural --analyzer-prefix myAnalyzer --source-container-sas-url "https://sourceStorageAccount.blob.core.windows.net/sourceContainer?sourceSASToken" --source-blob-folder diDatasetFolderName --target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" --target-blob-folder cuDatasetFolderName**

If you are using CustomNeural, please be sure to specify the analyzer prefix, as it is crucial for creating an analyzer. 

To convert a _DI 4.0 Preview CustomGen_, run this command: 

**python ./di_to_cu_converter.py --DI-version CustomGen --analyzer-prefix myAnalyzer --source-container-sas-url "https://sourceStorageAccount.blob.core.windows.net/sourceContainer?sourceSASToken" --source-blob-folder diDatasetFolderName --target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" --target-blob-folder cuDatasetFolderName**

Specifying an analyzerPrefix isn't necessary for CustomGen, but is needed if you wish to create multiple analyzers from the same analyzer.json.

### 2. Creating An Analyzer

To create an analyzer using the converted CU analyzer.json, please run this command:

**python ./create_analyzer.py --analyzer-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer/cuDatasetFolderName/analyzer.json?targetSASToken" 
--target-container-sas-url "https://targetStorageAccount.blob.core.windows.net/targetContainer?targetSASToken" --target-blob-folder cuDatasetFolderName**

In the output, you will see the analyzer ID of the created Analyzer, please remember this when using the call_analyze.py tool.

Ex: <img width="274" alt="image" src="https://github.com/user-attachments/assets/7cb0a94c-781e-4538-b536-cdf8d413cbba" />

### 3. Calling Analyze

To Analyze a specific PDF or original file, please run this command:

**python ./call_analyze.py --analyzer-id analyzerID --pdf-sas-url "https://storageAccount.blob.core.windows.net/container/folder/sample.pdf?SASToken --output-json "./desired-path-to-analyzer-results.json"**

For the --analyzer-id argument, please input the analyzer ID of the created Analyzer. 
Additionally, specifying the --output-json isn't neccesary. The default location is "./sample_documents/analyzer_result.json".

## Things of Note
- You will need to be using a version of Python above 3.9
- Fields with FieldType "signature," which are supported in 2024-11-30 Custom Neural, are not supported in the latest version of Content Understanding (2025-05-01-preview), and thus will be ignored when creating the analyzer
- We will only be providing data conversion to CU Preview.2
