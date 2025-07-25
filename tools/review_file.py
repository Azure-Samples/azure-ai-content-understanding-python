import os
import json
import re
import requests
import sys
import time
from io import StringIO

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import find_dotenv, load_dotenv
from github import Github, GithubException
from openai import AzureOpenAI
from unidiff import PatchSet


# Load env vars
load_dotenv(find_dotenv())

# Required environment variables
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_OPENAI_API_VERSION = "2024-12-01-preview"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv("GITHUB_REPOSITORY")
TARGET_FILE = os.getenv("INPUT_FILE_PATH")
REVIEW_CHANGES = os.getenv("REVIEW_CHANGES", "false").lower() == "true"

if not all([
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_DEPLOYMENT,
    GITHUB_TOKEN,
    REPO_NAME,
    TARGET_FILE]):
    print("❌ Missing required environment variables.")
    sys.exit(1)

# Authenticate with Azure AD instead of API key
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://cognitiveservices.azure.com/.default"
)

# Initialize Azure OpenAI client with AAD credential
client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    azure_ad_token_provider=token_provider,
    api_version=AZURE_OPENAI_API_VERSION
)

# Initialize GitHub client
gh = Github(GITHUB_TOKEN)
repo = gh.get_repo(REPO_NAME)


def run_llm_review(path, content):
    prompt = (
        f"You are a technical documentation editor.\n\n"
        f"Below is the content of the file `{path}`:\n"
        f"```\n{content}\n```\n\n"
        f"Your task:\n"
        f"1. Review the content and make improvements to clarity, grammar, formatting, and structure.\n"
        f"2. Focus on the docuementation like the content on README.md and comments in code files."
        f"3. Revise the text directly where necessary to enhance readability and accuracy.\n"
        f"4. Ensure the revised version maintains the original intent and meaning.\n"
        f"5. Ensure the consistency of the technical details among README and code comments.\n\n"
        f"Output:\n"
        f"Return the **full revised content** as a plain text string.\n"
        f"Do not include any explanations, Markdown, or formatting (e.g., no triple backticks).\n"
        f"Only return the revised content."
    )

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[{"role": "user", "content": prompt}],
    )
    print(
        f"🤖 LLM file review received, token usage:\n"
        f"Total tokens: {response.usage.total_tokens} tokens\n"
        f"Prompt tokens: {response.usage.prompt_tokens} tokens\n"
        f"Completion tokens: {response.usage.completion_tokens} tokens\n"
        f"Used deployment: {AZURE_OPENAI_DEPLOYMENT}"
    )
    return response.choices[0].message.content

def run_llm_comment_on_patch(patch: str) -> str:
    prompt = (
        f"You are a technical documentation reviewer. "
        f"Here's a code section (unified diff format) from a pull request:\n\n"
        f"```\n{patch}\n```\n\n"
        f"These changes were made to improve the code or documentation by previous editor.\n"
        f"Your task is to analyze the changes and provide a concise comment "
        f"on the possible rationales of the modifications.\n"
        f"1. Identify the categories of the changes: typo, grammar, clarity, or consistency.\n"
        f"2. Provide the list of main changes and their rationales and impact on the documentation. "
        f"like a. change:..., b. rationale:..., c. impact:...\n"
        f"* Do not need to suggest any further changes or improvements.\n\n"
    )

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[{"role": "user", "content": prompt}],
    )

    print(f"🤖 LLM change comment received, total token usage: {response.usage.total_tokens}")
    return response.choices[0].message.content


def find_position_in_pr(pr, filename, line_number):
    """
    Returns the position in the diff for a given line number in a file.
    GitHub API requires 'position' in diff, not line number.
    """
    for f in pr.get_files():
        if f.filename == filename and f.patch:
            lines = f.patch.split('\n')
            position = 0
            current_line = None
            for l in lines:
                position += 1
                if l.startswith('@@'):
                    # Parse the line number range
                    # Example: @@ -1,4 +1,5 @@
                    m = re.search(r'\+(\d+)', l)
                    if m:
                        current_line = int(m.group(1)) - 1
                elif l.startswith('+'):
                    current_line += 1
                    if current_line == line_number:
                        return position
                elif not l.startswith('-'):
                    current_line += 1
    return None  # Not found


def group_changed_sections(hunk, max_context_gap=2):
    """
    Group lines in a hunk into combined change sections (context + additions/removals).
    """
    sections = []
    current_section = []
    context_counter = 0
    in_change_block = False

    for line in hunk:
        if line.is_removed or line.is_added:
            in_change_block = True
            current_section.append(line)
            context_counter = 0
        elif line.is_context:
            if in_change_block:
                # Allow a few context lines to help anchor changes
                if context_counter < max_context_gap:
                    current_section.append(line)
                    context_counter += 1
                else:
                    # too much gap, close section
                    if current_section:
                        sections.append(current_section)
                        current_section = []
                        in_change_block = False
                        context_counter = 0
            else:
                # no change block, skip or reset
                continue
        else:
            # Any unknown type — just flush current section
            if current_section:
                sections.append(current_section)
                current_section = []
                in_change_block = False
                context_counter = 0

    if current_section:
        sections.append(current_section)

    return sections


def review_changes_and_comment_by_section(pr):
    print("🔍 Parsing and grouping added line sections...")

    diff_text = requests.get(pr.diff_url, headers={
        "Accept": "application/vnd.github.v3.diff",
        "Authorization": f"token {os.getenv('GITHUB_TOKEN')}"
    }).text

    patch_set = PatchSet(StringIO(diff_text))
    review_comments = []

    for patched_file in patch_set:
        filename = patched_file.path
        if patched_file.is_removed_file:
            continue

        for hunk in patched_file:
            added_sections = group_changed_sections(hunk)

            for section in added_sections:
                section_text = "".join(str(line) for line in section)
                comment = run_llm_comment_on_patch(section_text)
                if comment.strip():
                    first_line = next((l for l in section if l.is_added), None)
                    if not first_line:
                        continue
                    position = find_position_in_pr(pr, filename, first_line.target_line_no)
                    if position:
                        review_comments.append({
                            "path": filename,
                            "position": position,
                            "body": comment.strip()
                        })

    if review_comments:
        print(f"📝 Submitting {len(review_comments)} section-level comments to {pr.html_url}")
        pr.create_review(
            body="Automated LLM code review (section-based).",
            event="COMMENT",
            comments=review_comments
        )
    else:
        print("✅ No meaningful comments to submit.")


def main():
    base_branch = repo.default_branch
    base_ref = repo.get_git_ref(f"heads/{base_branch}")
    base_sha = base_ref.object.sha

    print(f"📥 Fetching `{TARGET_FILE}` from branch `{base_branch}`...")
    blob = repo.get_contents(TARGET_FILE, ref=base_branch)
    orig = blob.decoded_content.decode()

    print("🤖 Running LLM review...")
    updated_content = run_llm_review(TARGET_FILE, orig)

    # NOTE: for testing
    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # new_file_path = os.path.join(script_dir, "new_file.txt")
    # with open(new_file_path, "r", encoding="utf-8") as f:
    #     updated_content = f.read()

    new_branch = f"review-{TARGET_FILE.replace('/', '-')}-{int(time.time())}"
    print(f"🌿 Creating new branch `{new_branch}`...")
    repo.create_git_ref(ref=f"refs/heads/{new_branch}", sha=base_sha)

    print(f"✍️ Committing updated file to `{new_branch}`...")
    file = repo.get_contents(TARGET_FILE, ref=new_branch)
    repo.update_file(
        path=TARGET_FILE,
        message=f"docs: review {TARGET_FILE}",
        content=updated_content,
        sha=file.sha,
        branch=new_branch
    )

    print("📬 Creating Pull Request...")
    pr = repo.create_pull(
        title=f"Review `{TARGET_FILE}`",
        body="Automated review and improvements.",
        head=new_branch,
        base=base_branch
    )

    print(f"✅ PR created: {pr.html_url}")

    # NOTE: testing purpose
    # pr = repo.get_pull(4)
    print("🧠 Running LLM diff review and commenting...")
    review_changes_and_comment_by_section(pr)

if __name__ == "__main__":
    main()
