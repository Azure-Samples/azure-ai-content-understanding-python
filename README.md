# Azure AI Content Understanding Samples (Python)

Welcome! Content Understanding is a solution that analyzes and comprehends various media content, such as **documents, images, audio, and video**, transforming it into structured, organized, and searchable data.

- The samples in this repository default to the latest preview API version: **(2025-05-01-preview)**.
- This repo will provide more samples for new functionalities in Preview.2 **(2025-05-01-preview)** soon.
- As of 2025/05, 2025-05-01-preview is only available in the regions documented in [Content Understanding region and language support](https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/overview).

## Getting started
Add a sentence that the sample can be run from GitHub Codespaces, or run from your local environment. Recommend the user to start from Codespace for a frustration-free experience.

### GitHub Codespaces
You can run this repo virtually by using GitHub Codespaces, which will open a web-based VS Code in your browser.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://github.com/codespaces/new?skip_quickstart=true&machine=basicLinux32gb&repo=899687170&ref=main&geo=UsEast&devcontainer_path=.devcontainer%2Fdevcontainer.json)

1. Create a new CodeSpace <br />
![Create CodeSpace](/docs/create-codespace/1-Create%20Codespace.png)
2. Select Kernel <br />
![Select Kernel](/docs/create-codespace/2-Select%20Kernel.png)
3. Select Python Environment <br />
![Select Python Environment](/docs/create-codespace/3-Select%20Python%20Environment.png)
4. Test <br />
![Test](/docs/create-codespace/4-Test.png)

### Local environment
1. Make sure the following tools are installed:

    * [Azure Developer CLI (azd)](https://aka.ms/install-azd)
    * [Python 3.11+](https://www.python.org/downloads/)
    * [Git LFS](https://git-lfs.com/)

2. Make a new directory called `azure-ai-content-understanding-python` and clone this template into it using the `azd` CLI:
    ```
    azd init -t azure-ai-content-understanding-python
    ```
    You can also use git to clone the repository if you prefer.
    ```
    git clone https://github.com/Azure-Samples/azure-ai-content-understanding-python.git
    cd azure-ai-content-understanding-python
    ```
    - **Important:** If you use `git clone`, make sure to install Git LFS and run `git lfs pull` to download sample files in the `data` directory:

      ```shell
      git lfs install
      git lfs pull
      ```

## Configure Azure AI service resource
### (Option 1) Use `azd` commands to auto create temporal resources to run sample
1. Make sure you have permission to grant roles under subscription
1. Login Azure
    ```shell
    azd auth login
    ```
1. Setting up environment, following prompts to choose location
    ```shell
    azd up
    ```


### (Option 2) Manually create resources and set environment variables
1. Create [Azure AI Services resource](docs/create_azure_ai_service.md)
2. Go to `Access Control (IAM)` in resource, grant yourself role `Cognitive Services User`
    - It's necessary even you are the owner of the resource
3. Copy `notebooks/.env.sample` to `notebooks/.env`
4. Fill **AZURE_AI_ENDPOINT** with the endpoint from your Azure portal Azure AI Services instance.
5. Login Azure
   ```shell
   azd auth login
   ```
### (Option3) Set Dev container Environment
#### 1. Install tools that support dev containers
- **Visual Studio Code**  
  Download and install [Visual Studio Code](https://code.visualstudio.com/).

- **Dev Containers Extension**  
  In the VS Code extension marketplace, install the extension named "Dev Containers".  
  (The extension was previously called "Remote - Containers", but has since been renamed and integrated into Dev Containers.)

- **Docker**  
  Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (available for Windows, macOS, and Linux).  
  Docker is used to manage and run the container environment.  
  - Start Docker and ensure it is running in the background.

#### 2. Open the project and start the Dev Container

- Open the project folder with VS Code.
- Press `F1` or `Ctrl+Shift+P`, type and select:
   ```
   Dev Containers: Reopen in Container
   ```
   Or click the green icon in the lower left corner of VS Code and select "Reopen in Container".
- VS Code will automatically detect the `.devcontainer` folder, build the development container, and install the necessary dependencies.
- ![How to set dev container environment](./docs/dev-container-setup.gif "dev container setup")

## Open a Jupyter notebook and follow the step-by-step guidance

Navigate to the `notebooks` directory and select the sample notebook you are interested in. Since Codespaces is pre-configured with the necessary environment, you can directly execute each step in the notebook.

## More Samples using Azure Content Understanding
[Azure Search with Content Understanding](https://github.com/Azure-Samples/azure-ai-search-with-content-understanding-python)

[Azure Content Understanding with OpenAI](https://github.com/Azure-Samples/azure-ai-content-understanding-with-azure-openai-python)

## Features

Azure AI Content Understanding is a new Generative AI-based [Azure AI service](https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/overview), designed to process/ingest content of any type (documents, images, audio, and video) into a user-defined output format. Content Understanding offers a streamlined process to reason over large amounts of unstructured data, accelerating time-to-value by generating an output that can be integrated into automation and analytical workflows.

## Samples

| File | Description |
| --- | --- |
| [content_extraction.ipynb](notebooks/content_extraction.ipynb) | In this sample we will show content understanding API can help you get semantic information from your file. For example OCR with table in document, audio transcription, and face analysis in video. |
| [field_extraction.ipynb](notebooks/field_extraction.ipynb) | In this sample we will show how to create an analyzer to extract fields in your file. For example invoice amount in the document, how many people in an image, names mentioned in an audio, or summary of a video. You can customize the fields by creating your own analyzer template.  |
| [conversational_field_extraction.ipynb](notebooks/conversational_field_extraction.ipynb) | This sample shows you how to evaluate conversational audio data that has previously been transcribed with Content Understanding or Azure AI Speech in in an efficient way to optimize processing quality. This also allows you to re-analyze data in a cost-efficient way. This sample is based on the [field_extraction.ipynb](notebooks/field_extraction.ipynb) sample. |
| [analyzer_training.ipynb](notebooks/analyzer_training.ipynb) | If you want to futher boost the performance for field extraction, we can do training when you provide few labeled samples to the API. Note: This feature is available to document scenario now. |
| [management.ipynb](notebooks/management.ipynb) | This sample will demo how to create a minimal analyzer, list all the analyzers in your resource, and delete the analyzer you don't need. |
| [build_person_directory.ipynb](notebooks/build_person_directory.ipynb) | This sample will demo how to enroll people’s faces from images and build a Person Directory. | |

## Notes

* **Trademarks** - This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft trademarks or logos is subject to and must follow [Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general). Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship. Any use of third-party trademarks or logos is subject to those third-party’s policies.

* **Data Collection** - The software may collect information about you and your use of the software and send it to Microsoft. Microsoft may use this information to provide services and improve our products and services. You may turn off the telemetry as described in the repository. There are also some features in the software that may enable you and Microsoft to collect data from users of your applications. If you use these features, you must comply with applicable law, including providing appropriate notices to users of your applications together with a copy of Microsoft’s privacy statement. Our privacy statement is located at https://go.microsoft.com/fwlink/?LinkID=824704. You can learn more about data collection and use in the help documentation and our privacy statement. Your use of the software operates as your consent to these practices.
