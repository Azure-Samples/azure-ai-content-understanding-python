#!/bin/bash

# Clear the contents of the .env file
> notebooks/.env

# Append new values to the .env file
echo "AZURE_AI_ENDPOINT=$(azd env get-value AZURE_AI_ENDPOINT)" >> notebooks/.env