# Set env variables for labeled data
Folder [document_training](../data/document_training/) provide the manually labeled data as a quick sample. Before using these labeled files, you need an Azure Storage Account to store them. Let's follow below steps to prepare the data environment:

1. To create an Azure Storage Account, reference https://aka.ms/create-a-storage-account. If exists, skip this step.
2. Azure Storage Explorer is a tool which makes it easy to work with Azure Storage data. Install it and login with your credential, follow the [guide](https://aka.ms/download-and-install-Azure-Storage-Explorer).
3. Create a blob container or use an exist one from Azure Storage Explorer.  
   <img src="./create-blob-container.png" width="600" />  
4. Crate a folder in root of blob container. Note the name of the folder, and It could be used as parameter **TRAINING_DATA_PATH** when running the sample code.
   <img src="./create-blob-virtual-dir.png" width="800" />  
5. Upload all the labeling files from [document_training](./document_training/) to the folder.  
   <img src="./upload-labeling-files.png" width="800" />
6. After uploading all the labeling files. Right click on blob container and click the "Get Shared Access Signature..." in menu. Then choose the expect parameters or use default, and click the "Create" button.
   <img src="./get-access-signature.png" height="600" />  <img src="./choose-signature-options.png" height="600" />  
7. Here, we get the blob container url with SAS token. Note the url, and It could be used as parameter **TRAINING_DATA_SAS_URL** when running the sample code.  
   <img src="./copy-access-signature.png" width="600" />  

Now, we have completed the preparation of the data environment. Next, we could create an analyzer through code.

   
