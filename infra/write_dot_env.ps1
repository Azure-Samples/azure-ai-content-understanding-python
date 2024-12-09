# Clear the contents of the .env file
Set-Content -Path notebooks/.env -Value ""

# Append new values to the .env file
$azureAiEndpoint = azd env get-value AZURE_AI_ENDPOINT
$azureAiApiKey = azd env get-value AZURE_AI_API_KEY

Add-Content -Path notebooks/.env -Value "AZURE_AI_ENDPOINT=$azureAiEndpoint"
Add-Content -Path notebooks/.env -Value "AZURE_AI_API_KEY=$azureAiApiKey"