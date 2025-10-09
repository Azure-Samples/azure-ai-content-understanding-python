# SDK Sample Converter

This tool converts SDK sample code files from one programming language to another using Azure OpenAI. It supports both local directories and GitHub repositories for source SDKs and sample files.

## Features

- Converts code samples between languages (Python, Java, C#, JavaScript, etc.)
- Uses Azure OpenAI for code translation
- Supports local folders and GitHub repositories (public/private)
- Saves converted samples to a specified output directory

## Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python sdk_sample_converter.py \
  --sdk-source <local_path_or_github_url> \
  --samples-source <local_path_or_github_url> \
  --target-lang <language> \
  --output <output_folder> \
  [--github-token <token>]
```

- `--sdk-source`: Path or GitHub URL to SDK source files
- `--samples-source`: Path or GitHub URL to sample files
- `--target-lang`: Target language (e.g., python, java, csharp)
- `--output`: Output folder for converted files (default: `./converted_samples`)
- `--github-token`: GitHub token for private repos (optional for public repositories, but recommended to bypass unauthenticated API rate limits)

## Environment Variables

Set these in a `.env` file or your environment:

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_API_KEY` (optional when use key)
- `AZURE_OPENAI_API_VERSION` (optional, default: `2024-12-01-preview`)
- `GITHUB_TOKEN` (optional)

## Example

```bash
python sdk_sample_converter.py \
  --sdk-source ./my_sdk \
  --samples-source ./samples \
  --target-lang python \
  --output ./converted_samples
```

# Design Workflow

1. **Locate the sample repository and folder**
    - Use the GitHub permalink or clone the repo locally.
    - Copy the permalink to use as the `--samples-source` argument.  
      ![copy_permalink](copy_permalink.png)
2. **Choose the target language** (`--target-lang`)
    - Decide which language you want to convert the samples to (e.g., Python, Java, C#).
3. **Find the SDK repository and code folder**
    - Use the GitHub permalink or local path for the SDK source code.
    - Copy the permalink to use as the `--sdk-source` argument.
4. **Run the converter script**
    - Execute the script with the appropriate arguments to convert sample files to the target language and save them locally.
5. **Integrate and test**
    - Copy the converted files to the designated repository (often the SDK repo).
    - Test the converted samples to ensure correctness and functionality.