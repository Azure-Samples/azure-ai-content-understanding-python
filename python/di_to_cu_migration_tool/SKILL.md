---
name: sdk-di-to-cu-migration
description: "Migrate Document Intelligence (DI) custom extraction models to Content Understanding (CU) analyzers. Guides users through the 4-step pipeline: convert labeled data, review descriptions, create analyzer, and verify extraction. Supports DI 3.1/4.0 GA (neural) and DI 4.0 Preview (generative) model types."
---

# Document Intelligence to Content Understanding Migration

Migrate labeled datasets from Document Intelligence (DI) custom extraction models into the Content Understanding (CU) GA 2025-11-01 format using the Python CLI migration tool.

> **[COPILOT INTERACTION MODEL]:** This skill is designed to be interactive. At each step marked with **[ASK USER]**, pause execution and prompt the user for input or confirmation before proceeding. Do NOT silently skip these prompts.

## Tool Location

This skill and the migration tool scripts live together in:

```
azure-ai-content-understanding-python/python/di_to_cu_migration_tool/
```

## Overview

The migration is a **4-step pipeline**:

| Step | Script | Purpose |
|------|--------|---------|
| 1. **Convert** | `di_to_cu_converter.py` | Convert DI schema + labels → CU knowledge base (`analyzer.json` + labels + OCR) |
| 2. **Review** | (manual edit) | Add descriptions to `analyzer.json` to improve extraction accuracy |
| 3. **Create** | `create_analyzer.py` | Upload `analyzer.json` to create a CU analyzer |
| 4. **Verify** | `call_analyze.py` | Analyze a sample document with the new analyzer |

## Supported DI Model Types

| Source DI Version | `--di-model-type` Flag | Where Created |
|---|---|---|
| Custom Extraction Model DI 3.1 GA to DI 4.0 GA | `neural` | [Document Intelligence Studio](https://documentintelligence.ai.azure.com/studio) |
| Document Field Extraction Model 4.0 Preview | `generative` | [Microsoft Foundry](https://ai.azure.com/explore/aiservices/vision/document/extraction) |

## Prerequisites

> **[ASK USER] Before starting, verify:**
> 1. "Which DI model type are you migrating? `neural` (DI 3.1/4.0 GA Custom Neural from DI Studio) or `generative` (DI 4.0 Preview Document Field Extraction from Foundry)?"
> 2. "Do you have a Microsoft Foundry resource with Content Understanding enabled and model deployments configured (GPT-4.1 and text-embedding-3-large)?"
>    - If no, direct them to: https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/quickstart/use-rest-api?tabs=portal%2Cdocument
> 3. "Do you have Python >= 3.9 installed?"
> 4. "Do you have SAS URLs ready for your source DI dataset blob container (Read + List) and target CU dataset blob container (Read + Add + Create + Write)?"
>    - If no, explain how to generate SAS URLs in Azure Portal (Storage Browser → Blob Container → Generate SAS)

### Software Requirements

- Python >= 3.9
- pip (Python package manager)

### Azure Requirements

- Microsoft Foundry resource with Content Understanding enabled
- Model deployments: completion model (default: `gpt-4.1`) and embedding model (default: `text-embedding-3-large`)
- Source blob container with DI labeled dataset (SAS URL with Read + List)
- Target blob container for CU output (SAS URL with Read + Add + Create + Write)

## Setup

### Step 1: Navigate to the Migration Tool

```bash
cd ../azure-ai-content-understanding-python/python/di_to_cu_migration_tool
```

### Step 2: Create and Activate Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

```bash
cp .sample_env .env
```

Edit `.env` and set:

| Variable | Required | Description |
|----------|----------|-------------|
| `CONTENTUNDERSTANDING_ENDPOINT` | **Yes** | Microsoft Foundry endpoint (e.g., `https://your-resource.services.ai.azure.com`) |
| `CONTENTUNDERSTANDING_KEY` | No | API key. If not set, `DefaultAzureCredential` is used (recommended — ensure `az login` first) |

> **[ASK USER]** "What is your Microsoft Foundry endpoint URL?" and "Are you using API key or DefaultAzureCredential (az login) for authentication?"

## Step 1: Convert DI Dataset to CU Format

This step converts the DI labeled dataset into CU knowledge base format.

> **[ASK USER] Gather required information:**
> 1. "What is your DI model type?" → `neural` or `generative`
> 2. "What analyzer ID do you want to use?" (required for `neural`; optional for `generative` where it defaults to the `doc_type` from fields.json)
> 3. "What is your **source** blob container SAS URL?" (where your DI dataset lives)
> 4. "What is the blob folder prefix within the source container?" (e.g., `myDIProject/data`)
> 5. "What is your **target** blob container SAS URL?" (where CU output will be written)
> 6. "What is the blob folder prefix for the target?" (e.g., `myCUDataset`)
> 7. "Are your model deployment names the defaults (`gpt-4.1` and `text-embedding-3-large`), or do you have custom names?"

### CLI Flags Reference

| Flag | Required | Description |
|------|----------|-------------|
| `--di-model-type` | **Yes** | `neural` or `generative` |
| `--analyzer-id` | Neural: **Yes**, Generative: No | Analyzer ID for the CU analyzer. For generative, defaults to `doc_type` from fields.json |
| `--source-container-sas-url` | **Yes** | SAS URL for source blob container (Read + List) |
| `--source-blob-folder` | **Yes** | Blob prefix in source container |
| `--target-container-sas-url` | **Yes** | SAS URL for target blob container (Read + Add + Create + Write) |
| `--target-blob-folder` | **Yes** | Blob prefix in target container |
| `--completion-deployment` | No | Completion model deployment name (default: `gpt-4.1`) |
| `--embedding-deployment` | No | Embedding model deployment name (default: `text-embedding-3-large`) |

### Example: Convert a Neural Model Dataset

```bash
python di_to_cu_converter.py --di-model-type neural --analyzer-id mySampleAnalyzer \
  --source-container-sas-url "<SOURCE_SAS_URL>" \
  --source-blob-folder diDatasetPrefix \
  --target-container-sas-url "<TARGET_SAS_URL>" \
  --target-blob-folder cuDatasetPrefix
```

### Example: Convert a Generative Model Dataset

```bash
python di_to_cu_converter.py --di-model-type generative --analyzer-id mySampleAnalyzer \
  --source-container-sas-url "<SOURCE_SAS_URL>" \
  --source-blob-folder diDatasetPrefix \
  --target-container-sas-url "<TARGET_SAS_URL>" \
  --target-blob-folder cuDatasetPrefix
```

### Example: With Custom Model Deployment Names

Add `--completion-deployment` and `--embedding-deployment` if your deployments differ from the defaults:

```bash
python di_to_cu_converter.py --di-model-type neural --analyzer-id mySampleAnalyzer \
  --source-container-sas-url "<SOURCE_SAS_URL>" \
  --source-blob-folder diDatasetPrefix \
  --target-container-sas-url "<TARGET_SAS_URL>" \
  --target-blob-folder cuDatasetPrefix \
  --completion-deployment "my-gpt4-deployment" \
  --embedding-deployment "my-embedding-deployment"
```

**Important notes:**
- Always enclose SAS URLs in double quotes to prevent shell interpretation of special characters
- For `neural`: `--analyzer-id` is **required** (DI 3.1/4.0 GA fields.json has no `doc_type`)
- For `generative`: if `--analyzer-id` is provided, final ID = `analyzer-id_doc-type`; otherwise uses `doc_type` from fields.json
- Signature fields from DI are skipped (not supported in CU)
- Maximum 100 fields per analyzer

## Step 2: Review and Add Descriptions

> **[ASK USER]** "The conversion is complete. The `analyzer.json` is in your target blob container. You should now review and add descriptions to the analyzer and each field — this is the **most impactful step** for improving extraction accuracy. Would you like guidance on what to write?"

The DI format does not include descriptions. The converted `analyzer.json` will have **empty descriptions**. Adding meaningful descriptions significantly improves extraction accuracy.

### What to Update

**1. Analyzer description** — the `"description"` field inside `"fieldSchema"`:
```json
"fieldSchema": {
    "name": "myInvoiceAnalyzer",
    "description": "Extract key fields from supplier invoices, including invoice number, date, vendor name, line items, and total amount.",
    "fields": { ... }
}
```

**2. Field descriptions** — on each field inside `"fields"`:
```json
"fields": {
    "invoice_number": {
        "type": "string",
        "method": "extract",
        "description": "The unique invoice identifier, usually found in the top-right corner."
    }
}
```

## Step 3: Create the CU Analyzer

After reviewing descriptions, create the analyzer from `analyzer.json`.

> **[ASK USER]** Gather:
> 1. "What is the SAS URL for your `analyzer.json` file in blob storage?"
> 2. "What is your target container SAS URL?" (same as Step 1)
> 3. "What is your target blob folder?" (same as Step 1)

### CLI Flags Reference

| Flag | Required | Description |
|------|----------|-------------|
| `--analyzer-sas-url` | **Yes** | SAS URL pointing to the `analyzer.json` in blob storage |
| `--target-container-sas-url` | **Yes** | SAS URL for target blob container (same as Step 1) |
| `--target-blob-folder` | **Yes** | Blob prefix in target container (same as Step 1) |

### Example

```bash
python create_analyzer.py \
  --analyzer-sas-url "<ANALYZER_JSON_SAS_URL>" \
  --target-container-sas-url "<TARGET_SAS_URL>" \
  --target-blob-folder cuDatasetPrefix
```

The script prints the created analyzer ID on success. Use this ID in Step 4.

## Step 4: Verify with Analyze

Test the created analyzer by analyzing a sample document.

> **[ASK USER]** Gather:
> 1. "What is the analyzer ID from Step 3?"
> 2. "What is the SAS URL for a sample document (PDF, image, etc.) to test?"
> 3. "Where should the output JSON be saved?" (default: `./sample_documents/analyzer_result.json`)

### CLI Flags Reference

| Flag | Required | Description |
|------|----------|-------------|
| `--analyzer-id` | **Yes** | Analyzer ID created in Step 3 |
| `--document-sas-url` | **Yes** | SAS URL for a document to analyze |
| `--output-json` | No | Output path (default: `./sample_documents/analyzer_result.json`) |

### Example

```bash
python call_analyze.py --analyzer-id mySampleAnalyzer \
  --document-sas-url "<DOCUMENT_SAS_URL>" \
  --output-json "./results/analyzer_result.json"
```

Review the output to verify extracted fields match expectations. If accuracy is low, revisit Step 2 (improve descriptions), re-create the analyzer (Step 3), and re-verify (Step 4).

## Troubleshooting

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| **400 Bad Request** (create) | Invalid endpoint, field names, or analyzer ID | Check endpoint URL, field names (letters/numbers/underscores, 1-64 chars), analyzer ID format |
| **401 Unauthorized** | Bad API key or not logged in | Verify `CONTENTUNDERSTANDING_KEY` or run `az login` |
| **404 Not Found** (analyze) | Analyzer ID doesn't exist | Use correct ID from Step 3, or create it first |
| **Field count > 100** | Too many fields in DI dataset | Reduce fields before migration |

### Field Name Constraints

- Must start with a letter or underscore
- 1-64 characters
- Only letters, numbers, and underscores

### Analyzer ID Constraints

- 1-64 characters
- Letters, numbers, dots, underscores, and hyphens only
