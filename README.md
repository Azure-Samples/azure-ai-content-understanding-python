# Azure AI Content Understanding Samples (Python)

Welcome! Content Understanding is a solution that analyzes and comprehends various media content—including **documents, images, audio, and video**—and transforms it into structured, organized, and searchable data.

- The samples in this repository default to the latest preview API version: **2025-05-01-preview**.
- We will provide more samples for new functionalities in Preview.2 **2025-05-01-preview** soon.
- As of May 2025, the **2025-05-01-preview** API version is available only in the regions listed in [Content Understanding region and language support](https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/language-region-support).
- To access sample code for version **2024-12-01-preview**, please check out the corresponding Git tag `2024-12-01-preview` or download it directly from the [release page](https://github.com/Azure-Samples/azure-ai-content-understanding-python/releases/tag/2024-12-01-preview).

👉 If you are looking for **.NET samples**, check out [this repo](https://github.com/Azure-Samples/azure-ai-content-understanding-dotnet/).

## Getting Started

You can run the samples in GitHub Codespaces or on your local machine. For a smoother, hassle-free experience, we recommend starting with Codespaces.

### GitHub Codespaces

Run this repository virtually by using GitHub Codespaces, which opens a web-based VS Code directly in your browser.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://github.com/codespaces/new?skip_quickstart=true&machine=basicLinux32gb&repo=899687170&ref=main&geo=UsEast&devcontainer_path=.devcontainer%2Fdevcontainer.json)

After clicking the link above, follow these steps to set up the Codespace:

1. Create a new Codespace by selecting the `main` branch, your preferred Codespace region, and the 2-core machine type, as shown in the screenshot below.  
   ![Create CodeSpace](/docs/create-codespace/1-Create%20Codespace.png)
2. Once the Codespace is ready, open the terminal and follow the instructions in the **Configure Azure AI service resource** section to set up a valid Content Understanding resource.

### Local Environment

1. Ensure the following tools are installed:

    * [Azure Developer CLI (azd)](https://aka.ms/install-azd)
    * [Python 3.11+](https://www.python.org/downloads/)
    * [Git LFS](https://git-lfs.com/)

2. Create a new directory named `azure-ai-content-understanding-python` and clone this template into it using the `azd` CLI:

    ```bash
    azd init -t azure-ai-content-understanding-python
    ```

    Alternatively, you can clone the repository using Git:

    ```bash
    git clone https://github.com/Azure-Samples/azure-ai-content-understanding-python.git
    cd azure-ai-content-understanding-python
    ```

    - **Important:** If you use `git clone`, you must install Git LFS and run `git lfs pull` to download sample files in the `data` directory:

      ```bash
      git lfs install
      git lfs pull
      ```

3. Set Up Dev Container Environment

   - Install the following tools that support development containers:

     - **Visual Studio Code**  
       Download and install [Visual Studio Code](https://code.visualstudio.com/).

     - **Dev Containers Extension**  
       Install the "Dev Containers" extension from the VS Code Marketplace.  
       *(Note: This extension was previously called "Remote - Containers" but has been renamed and integrated into Dev Containers.)*

     - **Docker**  
       Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) for Windows, macOS, or Linux. Docker manages and runs the container environment.  
       - Start Docker and ensure it is running in the background.

   - Open the project and start the Dev Container:

     - Open the project folder in VS Code.
     - Press `F1` or `Ctrl+Shift+P`, then type and select:  
       ```
       Dev Containers: Reopen in Container
       ```
       Alternatively, click the green icon in the lower-left corner of VS Code and select **Reopen in Container**.
     - VS Code will detect the `.devcontainer` folder, build the development container, and install the necessary dependencies.  
     - ![How to set dev container environment](./docs/dev-container-setup.gif "Dev Container Setup")

## Configure Azure AI Service Resource

### (Option 1) Use `azd` Commands to Automatically Create Temporary Resources and Run Samples

1. Ensure you have permission to grant roles within your subscription.
2. Log in to Azure:

    ```bash
    azd auth login
    ```

    If this command doesn’t work, try the device code login:

    ```bash
    azd auth login --use-device-code
    ```

3. Set up the environment by following the prompts to choose your location:

    ```bash
    azd up
    ```

### (Option 2) Manually Create Resources and Set Environment Variables

1. Create an [Azure AI Services resource](docs/create_azure_ai_service.md).
2. Go to the resource’s **Access Control (IAM)** and assign yourself the role **Cognitive Services User**.  
   - This is necessary even if you are the owner of the resource.
3. Copy the sample environment file:

    ```bash
    cp notebooks/.env.sample notebooks/.env
    ```

4. Open `notebooks/.env` and fill in `AZURE_AI_ENDPOINT` with the endpoint URL from your Azure AI Services resource.
5. Log in to Azure:

    ```bash
    azd auth login
    ```

### (Option 3) Use Endpoint and API Key (No `azd` Required)

> ⚠️ **Note:** Using a subscription key works, but using a token provider with Azure Active Directory (AAD) is safer and strongly recommended for production environments.

1. Create an [Azure AI Services resource](docs/create_azure_ai_service.md).
2. Copy the sample environment file:

    ```bash
    cp notebooks/.env.sample notebooks/.env
    ```

3. Edit `notebooks/.env` and set your credentials:

    ```env
    AZURE_AI_ENDPOINT=https://<your-resource-name>.services.ai.azure.com/
    AZURE_AI_API_KEY=<your-azure-ai-api-key>
    ```

    Replace `<your-resource-name>` and `<your-azure-ai-api-key>` with your actual values. These can be found in your AI Services resource under **Resource Management** > **Keys and Endpoint**.

## Open a Jupyter Notebook and Follow Step-by-Step Guidance

Navigate to the `notebooks` directory and open the sample notebook you want to explore. Since the Dev Container (either in Codespaces or your local environment) is pre-configured with the necessary dependencies, you can directly execute each step.

1. Open any notebook from the `notebooks/` directory. We recommend starting with `content_extraction.ipynb` to understand the basic concepts.  
   ![Select *.ipynb](/docs/create-codespace/2-Select%20file.ipynb.png)  
2. Select the Kernel  
   ![Select Kernel](/docs/create-codespace/3-Select%20Kernel.png)  
3. Select the Python Environment  
   ![Select Python Environment](/docs/create-codespace/4-Select%20Python%20Environment.png)  
4. Run the notebook cells  
   ![Run](/docs/create-codespace/5-Run.png)

## Features

Azure AI Content Understanding is a new Generative AI-based [Azure AI service](https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/overview) designed to process and ingest content of any type—documents, images, audio, and video—into a user-defined output format. Content Understanding provides a streamlined way to analyze large volumes of unstructured data, accelerating time-to-value by generating output that can be integrated into automation and analytical workflows.

## Samples

| File                                      | Description                                                                                                                                                                                                                                                                                          |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [content_extraction.ipynb](notebooks/content_extraction.ipynb)           | Demonstrates how the Content Understanding API can extract semantic information from your files—for example, OCR with tables in documents, audio transcription, and face analysis in videos.                                                                                                   |
| [field_extraction.ipynb](notebooks/field_extraction.ipynb)               | Shows how to create an analyzer to extract fields from your files—e.g., invoice amounts in documents, counting people in images, names mentioned in audio, or summarizing videos. Customize fields by creating your own analyzer template.                                                        |
| [field_extraction_pro_mode.ipynb](notebooks/field_extraction_pro_mode.ipynb) | Demonstrates **Pro mode** in Azure AI Content Understanding, enhancing analyzers with multiple inputs and optional reference data. Pro mode is designed for advanced use cases requiring multi-step reasoning and complex decision-making, such as identifying inconsistencies and drawing inferences. |
| [classifier.ipynb](notebooks/classifier.ipynb)                           | Demonstrates how to (1) create a classifier to categorize documents, (2) create a custom analyzer to extract specific fields, and (3) combine classifiers and analyzers to classify, optionally split, and analyze documents using a flexible processing pipeline.                                 |
| [conversational_field_extraction.ipynb](notebooks/conversational_field_extraction.ipynb) | Shows how to efficiently evaluate conversational audio data previously transcribed with Content Understanding or Azure AI Speech. Enables re-analysis of data cost-effectively. Based on the [field_extraction.ipynb](notebooks/field_extraction.ipynb) sample.                                   |
| [analyzer_training.ipynb](notebooks/analyzer_training.ipynb)             | Demonstrates how to improve field extraction performance by training the API with a few labeled samples. *(Note: This feature is currently available only for document scenarios.)*                                                                                                               |
| [management.ipynb](notebooks/management.ipynb)                           | Demonstrates creating a minimal analyzer, listing all analyzers in your resource, and deleting analyzers you no longer need.                                                                                                                                                                      |
| [build_person_directory.ipynb](notebooks/build_person_directory.ipynb)   | Shows how to enroll people’s faces from images and build a Person Directory.                                                                                                                                                                                                                        |

## More Samples Using Azure Content Understanding

- [Azure Search with Content Understanding](https://github.com/Azure-Samples/azure-ai-search-with-content-understanding-python)
- [Azure Content Understanding with OpenAI](https://github.com/Azure-Samples/azure-ai-content-understanding-with-azure-openai-python)

## Notes

* **Trademarks** - This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft trademarks or logos is subject to and must follow [Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general). Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship. Any use of third-party trademarks or logos is subject to those third-party’s policies.

* **Data Collection** - The software may collect information about you and your use of the software and send it to Microsoft. Microsoft may use this information to provide services and improve our products and services. You may turn off the telemetry as described in the repository. There are also some features in the software that may enable you and Microsoft to collect data from users of your applications. If you use these features, you must comply with applicable law, including providing appropriate notices to users of your applications together with a copy of Microsoft’s privacy statement. Our privacy statement is located at https://go.microsoft.com/fwlink/?LinkID=824704. You can learn more about data collection and use in the help documentation and our privacy statement. Your use of the software operates as your consent to these practices.
