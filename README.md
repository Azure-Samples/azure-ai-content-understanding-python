# Azure AI Content Understanding Samples (Python)

Welcome! Content Understanding is a solution that analyzes and comprehends various media content—including **documents, images, audio, and video**—and transforms it into structured, organized, and searchable data.

Content Understanding is now a Generally Available (GA) service with the release of the `2025-11-01` API version. 

- The samples in this repository default to the latest GA API version: `2025-11-01`.
- We will provide more samples for new functionalities in the GA API versions soon. For details on the updates in the current GA release, see the [Content Understanding What's New Document page](https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/whats-new).
- As of November 2025, the `2025-11-01` API version is now available in a broader range of [regions](https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/language-region-support).
- To access sample code for version `2025-05-01-preview`, please check out the corresponding Git tag `2025-05-01-preview` or download it directly from the [release page](https://github.com/Azure-Samples/azure-ai-content-understanding-python/releases/tag/2025-05-01-preview).
- To access sample code for version `2024-12-01-preview`, please check out the corresponding Git tag `2024-12-01-preview` or download it directly from the [release page](https://github.com/Azure-Samples/azure-ai-content-understanding-python/releases/tag/2024-12-01-preview).

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

### Step 1: Create Azure AI Foundry Resource

First, create an Azure AI Foundry resource that will host both the Content Understanding service and the required model deployments.

1. Follow the steps in the [Azure Content Understanding documentation](https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/) to create an Azure AI Foundry resource
2. Get your Foundry resource's endpoint URL from Azure Portal:
   - Go to [Azure Portal](https://portal.azure.com/)
   - Navigate to your Azure AI Foundry resource
   - Go to **Resource Management** > **Keys and Endpoint**
   - Copy the **Endpoint** URL (typically `https://<your-resource-name>.services.ai.azure.com/`)

**⚠️ Important: Grant Required Permissions**

After creating your Azure AI Foundry resource, you must grant yourself the **Cognitive Services User** role to enable API calls for setting default GPT deployments:

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to your Azure AI Foundry resource
3. Go to **Access Control (IAM)** in the left menu
4. Click **Add** > **Add role assignment**
5. Select the **Cognitive Services User** role
6. Assign it to yourself (or the user/service principal that will run the samples)

> **Note:** This role assignment is required even if you are the owner of the resource. Without this role, you will not be able to call the Content Understanding API to configure model deployments for prebuilt analyzers.

### Step 2: Deploy Required Models

**⚠️ Important:** The prebuilt analyzers require model deployments. You must deploy these models before using prebuilt analyzers:
- `prebuilt-documentSearch`, `prebuilt-audioSearch`, `prebuilt-videoSearch` require **GPT-4.1-mini** and **text-embedding-3-large**
- Other prebuilt analyzers like `prebuilt-invoice`, `prebuilt-receipt` require **GPT-4.1** and **text-embedding-3-large**

1. **Deploy GPT-4.1:**
   - In Azure AI Foundry, go to **Deployments** > **Deploy model** > **Deploy base model**
   - Search for and select **gpt-4.1**
   - Complete the deployment with your preferred settings
   - Note the deployment name (by convention, use `gpt-4.1`)

2. **Deploy GPT-4.1-mini:**
   - In Azure AI Foundry, go to **Deployments** > **Deploy model** > **Deploy base model**
   - Search for and select **gpt-4.1-mini**
   - Complete the deployment with your preferred settings
   - Note the deployment name (by convention, use `gpt-4.1-mini`)

3. **Deploy text-embedding-3-large:**
   - In Azure AI Foundry, go to **Deployments** > **Deploy model** > **Deploy base model**
   - Search for and select **text-embedding-3-large**
   - Complete the deployment with your preferred settings
   - Note the deployment name (by convention, use `text-embedding-3-large`)

For more information on deploying models, see [Deploy models in Azure AI Foundry](https://learn.microsoft.com/en-us/azure/ai-studio/how-to/deploy-models-openai).

### Step 3: Configure Environment Variables

Choose one of the following options to configure your environment:

#### Set Environment Variables with Token Authentication (Recommended)

> **💡 Recommended:** This approach uses Azure Active Directory (AAD) token authentication, which is safer and strongly recommended for production environments. You do **not** need to set `AZURE_AI_API_KEY` in your `.env` file when using this method.

1. Copy the sample environment file:

    ```bash
    cp notebooks/.env.sample notebooks/.env
    ```

2. Open `notebooks/.env` and fill in the required values. Replace `<your-resource-name>` with your actual resource name. If you used different deployment names in Step 2, update the deployment variables accordingly:

    ```env
    AZURE_AI_ENDPOINT=https://<your-resource-name>.services.ai.azure.com/
    GPT_4_1_DEPLOYMENT=gpt-4.1
    GPT_4_1_MINI_DEPLOYMENT=gpt-4.1-mini
    TEXT_EMBEDDING_3_LARGE_DEPLOYMENT=text-embedding-3-large
    ```

3. Log in to Azure:

    ```bash
    azd auth login
    ```

#### Set Environment Variables with API Key (Alternative)


1. Copy the sample environment file:

    ```bash
    cp notebooks/.env.sample notebooks/.env
    ```

2. Edit `notebooks/.env` and set your credentials. 
- Replace `<your-resource-name>` and `<your-azure-ai-api-key>` with your actual values. These can be found in your AI Services resource under **Resource Management** > **Keys and Endpoint**. 
- If you used different deployment names in Step 2, update the deployment variables accordingly:

    ```env
    AZURE_AI_ENDPOINT=https://<your-resource-name>.services.ai.azure.com/
    AZURE_AI_API_KEY=<your-azure-ai-api-key>
    GPT_4_1_DEPLOYMENT=gpt-4.1
    GPT_4_1_MINI_DEPLOYMENT=gpt-4.1-mini
    TEXT_EMBEDDING_3_LARGE_DEPLOYMENT=text-embedding-3-large
    ```

> ⚠️ **Note:** If you skip the token authentication step above, you must set `AZURE_AI_API_KEY` in your `.env` file. Get your API key from Azure Portal by navigating to your Foundry resource > **Resource Management** > **Keys and Endpoint**.

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
| [content_extraction.ipynb](notebooks/content_extraction.ipynb)           | **Recommended starting point.** Demonstrates how the Content Understanding API can extract semantic information from your files—for example, OCR with tables in documents, audio transcription, and face analysis in videos.                                                                                                   |
| [field_extraction.ipynb](notebooks/field_extraction.ipynb)               | Shows how to create an analyzer to extract fields from your files—e.g., invoice amounts in documents, counting people in images, names mentioned in audio, or summarizing videos. Customize fields by creating your own analyzer template.                                                        |
| [classifier.ipynb](notebooks/classifier.ipynb)                           | Demonstrates how to (1) create a classifier to categorize documents, (2) create a custom analyzer to extract specific fields, and (3) combine classifiers and analyzers to classify, optionally split, and analyze documents using a flexible processing pipeline.                                 |
| [analyzer_training.ipynb](notebooks/analyzer_training.ipynb)             | Demonstrates how to improve field extraction performance by training the API with a few labeled samples. *(Note: This feature is currently available only for document scenarios.)*                                                                                                               |
| [management.ipynb](notebooks/management.ipynb)                           | Demonstrates creating a minimal analyzer, listing all analyzers in your resource, and deleting analyzers you no longer need.                                                                                                                                                                      |

## More Samples Using Azure Content Understanding

> **Note:** The following samples are currently targeting Preview.2 (API version `2025-05-01-preview`) and will be updated to the GA API version (`2025-11-01`) soon.

- [Azure Search with Content Understanding](https://github.com/Azure-Samples/azure-ai-search-with-content-understanding-python)
- [Azure Content Understanding with OpenAI](https://github.com/Azure-Samples/azure-ai-content-understanding-with-azure-openai-python)

## Notes

* **Trademarks** - This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft trademarks or logos is subject to and must follow [Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general). Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship. Any use of third-party trademarks or logos is subject to those third-party’s policies.

* **Data Collection** - The software may collect information about you and your use of the software and send it to Microsoft. Microsoft may use this information to provide services and improve our products and services. You may turn off the telemetry as described in the repository. There are also some features in the software that may enable you and Microsoft to collect data from users of your applications. If you use these features, you must comply with applicable law, including providing appropriate notices to users of your applications together with a copy of Microsoft’s privacy statement. Our privacy statement is located at https://go.microsoft.com/fwlink/?LinkID=824704. You can learn more about data collection and use in the help documentation and our privacy statement. Your use of the software operates as your consent to these practices.
