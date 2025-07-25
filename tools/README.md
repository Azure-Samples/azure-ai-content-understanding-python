# test_notebooks.py

This script is designed for **testing and validating** that all Jupyter notebooks in the `notebooks/` directory (or a specified directory) execute successfully from start to finish. It is especially useful for pre-merge checks and for contributors to verify that their changes do not break any notebook workflows.

## Features
- **Automatic Discovery:** Recursively scans a directory for `.ipynb` files (excluding hidden files).
- **Selective Skipping:** Supports a skip list to exclude specific notebooks from execution (e.g., those requiring manual input or special setup).
- **Execution Reporting:** Prints a summary of successful and failed notebooks, including error messages for failures.
- **Command Line Usage:** Can run all notebooks in a directory or a specified list of notebook files.

## Usage

### Run All Notebooks in a Directory

```bash
python3 tools/test_notebooks.py
```
This will scan the `notebooks/` directory by default, skipping any notebooks listed in the `skip_list` variable.

### Run Specific Notebooks

```bash
python3 tools/test_notebooks.py notebooks/example1.ipynb notebooks/example2.ipynb
```
This will execute only the specified notebooks.

## Setting Up Environment Variables
Some notebooks require access to Azure Storage or other resources. You may need to set environment variables in the [.env](../notebooks/.env) file before running the tests. For example, to test notebooks that use training data or reference documents, follow these steps:

1. **Prepare Azure Storage:**
   - Create an Azure Storage Account and a Blob Container (can follow the guide to [create an Azure Storage Account](https://aka.ms/create-a-storage-account)).
   - Use Azure Storage Explorer to generate a Shared Access Signature (SAS) URL with `Read`, `Write`, and `List` permissions for the container.
2. **Set Environment Variables:**
   - Add the following variables to the [.env](../notebooks/.env) file in your project root:

     ```env
     TRAINING_DATA_SAS_URL=<Blob container SAS URL>
     TRAINING_DATA_PATH=<Designated folder path under the blob container>
     REFERENCE_DOC_SAS_URL=<Blob container SAS URL>
     REFERENCE_DOC_PATH=<Designated folder path under the blob container>
     ```
   - These variables will be used by notebooks that require access to training/reference data.
   - You can refer to [Set env for training data and reference doc](../docs/set_env_for_training_data_and_reference_doc.md) for setting up these variables.

## Skip List
You can modify the `skip_list` variable in the script to add or remove notebooks that should be skipped during execution. The skip list can contain full paths or substrings.

## Dependencies
- Python 3
- `nbformat`
- `nbconvert`

Install dependencies with:
```bash
pip3 install nbformat nbconvert
```

## Exit Codes
- Returns `0` if all notebooks succeed.
- Returns `1` if any notebook fails or if no notebooks are found.

## Notes
- Notebooks that require manual input, special setup, or specific environment variables could be added to the skip list or set up the requirements accordingly.
