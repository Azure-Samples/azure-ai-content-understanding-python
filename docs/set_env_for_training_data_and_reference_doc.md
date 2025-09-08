# Set Environment Variables for Training Data and Reference Documents in Pro Mode

The folders [document_training](../data/document_training/) and [field_extraction_pro_mode](../data/field_extraction_pro_mode) contain manually labeled data used for training data in Standard mode and reference documents in Pro mode as quick samples. Before using these knowledge source files, you need an Azure Storage blob container to store them. Please follow the steps below to prepare your data environment:

1. **Create an Azure Storage Account:**  
   If you don’t already have one, follow the guide to [create an Azure Storage Account](https://aka.ms/create-a-storage-account).  
   > If you already have an account, you can skip this step.

2. **Install Azure Storage Explorer:**  
   Azure Storage Explorer is a tool that simplifies working with Azure Storage data. Install it and log in with your credentials by following the [installation guide](https://aka.ms/download-and-install-Azure-Storage-Explorer).

3. **Create or Choose a Blob Container:**  
   Using Azure Storage Explorer, create a new blob container or use an existing one.  
   <img src="./create-blob-container.png" width="600" />

4. **Set SAS URL-related Environment Variables in the `.env` File:**  
   Depending on the sample you plan to run, configure the required environment variables in the [.env](../notebooks/.env) file. There are two options to set up environment variables that utilize the required Shared Access Signature (SAS) URL.

    - **Option A - Generate a SAS URL Manually via Azure Storage Explorer**  
        - Right-click on the blob container and select **Get Shared Access Signature...** from the menu.  
        - Select the permissions: **Read**, **Write**, and **List**.  
            - Note: **Write** permission is required for uploading, modifying, or appending blobs.  
        - Click the **Create** button.  
        <img src="./get-access-signature.png" height="600" /> <img src="./choose-signature-options.png" height="600" />  
        - **Copy the SAS URL:** After creating the SAS, click **Copy** to get the URL with the token. This URL will be used as the value for either **training_data_sas_url** or **REFERENCE_DOC_SAS_URL** when running the sample code.  
            <img src="./copy-access-signature.png" width="600" />
        
        - Set the following variables in the [.env](../notebooks/.env) file:  
            > **Note:** The value for **REFERENCE_DOC_SAS_URL** can be the same as **training_data_sas_url** to reuse the same blob container.
            - For [analyzer_training](../notebooks/analyzer_training.ipynb): Add the SAS URL as the value of **training_data_sas_url**.  
                ```env
                training_data_sas_url=<Blob container SAS URL>
                ```
            - For [field_extraction_pro_mode](../notebooks/field_extraction_pro_mode.ipynb): Add the SAS URL as the value of **REFERENCE_DOC_SAS_URL**.  
                ```env
                REFERENCE_DOC_SAS_URL=<Blob container SAS URL>
                ```

    - **Option B - Auto-generate the SAS URL via Code in Sample Notebooks**  
        - Instead of manually creating a SAS URL, you can specify the storage account and container information and let the code generate a temporary SAS URL at runtime.  
            > **Note:** **TRAINING_DATA_STORAGE_ACCOUNT_NAME** and **TRAINING_DATA_CONTAINER_NAME** can be the same as **REFERENCE_DOC_STORAGE_ACCOUNT_NAME** and **REFERENCE_DOC_CONTAINER_NAME** to reuse the same blob container.
            - For [analyzer_training](../notebooks/analyzer_training.ipynb): Add the storage account name as `TRAINING_DATA_STORAGE_ACCOUNT_NAME` and the container name under that storage account as `TRAINING_DATA_CONTAINER_NAME`.  
                ```env
                TRAINING_DATA_STORAGE_ACCOUNT_NAME=<your-storage-account-name>
                TRAINING_DATA_CONTAINER_NAME=<your-container-name>
                ```
            - For [field_extraction_pro_mode](../notebooks/field_extraction_pro_mode.ipynb): Add the storage account name as `REFERENCE_DOC_STORAGE_ACCOUNT_NAME` and the container name under that storage account as `REFERENCE_DOC_CONTAINER_NAME`.  
                ```env
                REFERENCE_DOC_STORAGE_ACCOUNT_NAME=<your-storage-account-name>
                REFERENCE_DOC_CONTAINER_NAME=<your-container-name>
                ```

5. **Set Folder Prefixes in the `.env` File:**  
   Depending on the sample you will run, set the required environment variables in the [.env](../notebooks/.env) file.

    - For [analyzer_training](../notebooks/analyzer_training.ipynb): Add a prefix for **training_data_path**. You can choose any folder name within the blob container. For example, use `training_files`.  
        ```env
        training_data_path=<Designated folder path under the blob container>
        ```
    - For [field_extraction_pro_mode](../notebooks/field_extraction_pro_mode.ipynb): Add a prefix for **REFERENCE_DOC_PATH**. You can choose any folder name within the blob container. For example, use `reference_docs`.  
        ```env
        REFERENCE_DOC_PATH=<Designated folder path under the blob container>
        ```

Once these steps are completed, your data environment is ready. You can proceed to create an analyzer through code.
