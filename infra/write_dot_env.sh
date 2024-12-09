#!/bin/bash

# Clear the contents of the .env file
> notebooks/.env

# Append new values to the .env file
echo "AZURE_AI_ENDPOINT=$(azd env get-value AZURE_AI_ENDPOINT)" >> notebooks/.env
echo "AZURE_AI_API_KEY=$(azd env get-value AZURE_AI_API_KEY)" >> notebooks/.env