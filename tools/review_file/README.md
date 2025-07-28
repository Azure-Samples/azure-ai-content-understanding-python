# review_file.py

## Automated Documentation & Code Review

The `review_file.py` script uses Azure OpenAI and GitHub APIs to automatically review and improve documentation or code files, then creates a pull request with suggested changes. It also analyzes diffs and leaves section-level comments on PRs.

### Usage

1. **Set Required Environment Variables**  
   you can copy `tools/.env.sample` to `tools/.env`
   Ensure the following environment variables are set in your [.env](../tools/.env) file under `/tools`:
   - `AZURE_OPENAI_ENDPOINT`
   - `AZURE_OPENAI_DEPLOYMENT`
   - `GITHUB_TOKEN`
   - `GITHUB_REPOSITORY`
   - `INPUT_FILE_PATH`
   - Optional:
      - `BRANCH_NAME` (default: default branch such as `main`)
      - `ENABLE_REVIEW_CHANGES` (default: `true`)

2. **Install Dependencies**  
   ```bash
   pip3 install azure-identity python-dotenv PyGithub openai unidiff requests
   ```

3. **Run the Script**  
   ```bash
   python3 tools/review_file.py
   ```
   This will:
   - Review the file specified by `INPUT_FILE_PATH` using LLM.
   - Create a new branch and commit the revised file.
   - Open a pull request with the changes.
   - Optionally, analyze the diff and comment on changed sections.

### Notes

- The script is intended for documentation files (e.g., `README.md`) and code comments.
- Ensure your Azure OpenAI and GitHub credentials are valid.
- Comments on PRs are generated using LLM for clarity and rationale.
