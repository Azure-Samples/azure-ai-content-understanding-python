# How to Create an Azure AI Service

This guide walks you through the latest configuration using **Azure AI Foundry**, including creating a Foundry Hub and Project, and deploying Azure AI Content Understanding.

## 1. Create a Foundry Hub
- Go to the [Azure Portal AI Foundry Resource](https://portal.azure.com/#create/Microsoft.CognitiveServicesAIFoundry).
- Select your Azure subscription.
- Choose or create a Resource Group.
- **Please select a supported region** from the table below:

   | Geography | Region         | Region Identifier   |
   | --------- | -------------- | ------------------- |
   | US        | West US        | westus              |
   | Europe    | Sweden Central | swedencentral       |
   | Australia | Australia East | australiaeast       |

- Enter a name for your Content Understanding resource.
- Select a pricing plan.  
    <img src="./create_srv_1.png" width="600" />
- Configure additional settings as needed, read and accept the terms, then click **Create**.  
    <img src="./create_srv_2.png" width="600" />
- Wait for Azure’s validation (look for a green **Validation Passed** banner).
- Click **Create** to start deployment. After a few seconds, you should see a message confirming, **Your deployment is complete**.

## 2. Get Keys and Endpoint
- Navigate to your deployed resource.
- In the left menu, select **Keys and Endpoint**.
- Please copy the following information carefully:
  - **Endpoint:** The format is  
    ```
    AZURE_AI_ENDPOINT = "https://<AzureAIContentUnderstandingResourceName>.services.ai.azure.com/"
    ```
  - **Primary Key:**  
    ```
    AZURE_AI_API_KEY = <your_primary_key>
    ```
  - **API Version:**  
    ```
    AZURE_AI_API_VERSION = "2025-05-01-preview"
    ```
    <img src="./create_srv_3.png" width="600" />

You are now ready to use these credentials to run the samples.

---

**Note:**  
- Always use the **Foundry Hub > Foundry Project** structure for Azure AI Content Understanding configuration.  
- Please ensure you select a supported region for Content Understanding during deployment.