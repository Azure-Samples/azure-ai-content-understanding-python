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
   - **HOST:** Replace this with your Azure AI Service's Content Understanding endpoint. Be sure to remove the "/" at the end. 
       - Ex: "https://user422.services.ai.azure.com"
         <img width="965" alt="image" src="https://github.com/user-attachments/assets/8eb64823-a55e-4a30-a50e-db6921537126" />
         <img width="605" alt="image" src="https://github.com/user-attachments/assets/ffd92606-dee1-48bc-a37d-5f1fe34cb52c" />
   - **SUBSCRIPTION_KEY:** Replace this with your Azure AI Service's API Key or Subscription ID. This is used to identify and authenticate the API request.
       - If you have an API Key, it will show up here: <img width="641" alt="image" src="https://github.com/user-attachments/assets/73f878fa-775a-40b2-85b0-d2b7353fe068" />
       - If your service uses AAD, please instead fill this value with your Subscription ID: <img width="974" alt="image" src="https://github.com/user-attachments/assets/2b80e05b-c248-4df4-a387-5088e08df75b" />
   - **API_VERSION:** Please leave this value as is. This ensures that you are converting to a CU Preview.2 dataset. 

## How to Run 
To run the 3 tools, you will need to follow these commands.

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

**python ./call_analyze.py --analyzer-id analyzerID --pdf-sas-url "https://storageAccount.blob.core.windows.net/container/folder/sample.pdf?SASToken"**

For the --analyzer-id argument, please input the analyzer ID of the created Analyzer. 

After this command finishes running, you should be able to
- see a converted CU dataset (with analyzer.json, labels.json, result.json, and the original files) in your specified target blob storage
- see a created Analyzer with the mentioned Analyzer ID
- see the results of the Analyze call in where you specified ANALYZE_RESULT_OUTPUT_JSON to be

## Things of Note
- You will need to be using a version of Python above 3.9
- Fields with FieldType "signature," which are supported in 2024-11-30 Custom Neural, are not supported in the latest version of Content Understanding (2025-05-01-preview), and thus will be ignored when creating the analyzer
- We will only be providing data conversion to CU Preview.2
