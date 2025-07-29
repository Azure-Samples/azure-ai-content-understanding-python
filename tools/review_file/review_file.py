import os
import json
import re
import requests
import sys
import time
from io import StringIO
from typing import Optional, List, Dict, Any

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from github import Github, PullRequest
from openai import AzureOpenAI
from unidiff.patch import PatchSet, Hunk, Line


# Load environment variables from .env file in the same directory as this script
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path)

# Required environment variables
AZURE_OPENAI_ENDPOINT: Optional[str] = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT: Optional[str] = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_OPENAI_API_VERSION: str = "2024-12-01-preview"
GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN")
REPO_NAME: Optional[str] = os.getenv("GITHUB_REPOSITORY")
BRANCH_NAME: Optional[str] = os.getenv("BRANCH_NAME")
TARGET_FILE: Optional[str] = os.getenv("INPUT_FILE_PATH")
USER_INSTRUCTIONS: str = os.getenv("USER_INSTRUCTIONS", "").strip()
ENABLE_REVIEW_CHANGES: bool = os.getenv("ENABLE_REVIEW_CHANGES", "true").lower() == "true"

if not all([
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_DEPLOYMENT,
    GITHUB_TOKEN,
    REPO_NAME,
    TARGET_FILE
]):
    print("❌ Missing required environment variables. Please check your .env file and environment setup.")
    sys.exit(1)

# Authenticate with Azure AD instead of API key
try:
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default"
    )
except Exception as e:
    print(f"❌ Azure authentication failed: {e}")
    sys.exit(1)

# Initialize Azure OpenAI client with AAD credential
try:
    client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        azure_ad_token_provider=token_provider,
        api_version=AZURE_OPENAI_API_VERSION
    )
except Exception as e:
    print(f"❌ Failed to initialize Azure OpenAI client: {e}")
    sys.exit(1)

# Initialize GitHub client
try:
    gh = Github(GITHUB_TOKEN)
    repo = gh.get_repo(REPO_NAME)
except Exception as e:
    print(f"❌ GitHub authentication or repository access failed: {e}")
    sys.exit(1)

def run_llm_review(
        file_path: str,
        file_content: str,
        user_instructions: str = "",
    ) -> tuple[str, str]:
    """
    Use LLM to review and improve the content of a file.
    Returns the revised content as a plain text string.
    """
    user_instructions_prompt = (
        f"**Additional important instructions:**\n"
        f"{user_instructions.strip()}\n\n"
    ) if user_instructions else ""

    prompt = (
        f"You are a technical documentation editor.\n\n"
        f"Below is the content of the file `{file_path}`:\n"
        f"```\n{file_content}\n```\n\n"
        f"Your tasks:\n"
        f"1. First, review the content thoroughly to grasp the context and intended purpose of the file.\n"
        f"2. Revise the content to improve clarity, grammar, formatting, and overall structure.\n"
        f"3. Focus specifically on documentation elements, such as the full content of README files, "
        f"code comments, and markdown sections in Python notebooks.\n"
        f"4. **IMPORTANT:** Do not modify any code logic or functionality, only improve the documentation elements.\n"
        f"5. Edit the text directly to enhance readability and technical accuracy.\n"
        f"6. Preserve the original meaning and intent of the content.\n"
        f"7. Ensure consistency in terminology, tone, and technical details across README files, code comments, and markdown sections.\n\n"
        f"{user_instructions_prompt}"
        f"Output:\n"
        f"Return the **entire revised content** as a plain text, without additional commentary or formatting.\n"
    )

    try:
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        print(f"❌ LLM review failed: {e}")
        sys.exit(1)

    llm_review_details = (
        f"- Total tokens: {getattr(response.usage, 'total_tokens', 'N/A')}\n"
        f"- Prompt tokens: {getattr(response.usage, 'prompt_tokens', 'N/A')}\n"
        f"- Completion tokens: {getattr(response.usage, 'completion_tokens', 'N/A')}\n"
        f"- Used deployment: {AZURE_OPENAI_DEPLOYMENT}\n"
        f"- API version: {AZURE_OPENAI_API_VERSION}"
    )
    print(f"🤖 LLM file review received, token usage:\n{llm_review_details}")

    return response.choices[0].message.content, llm_review_details

def run_llm_comment_on_patch(patch: str) -> tuple[str, Optional[int]]:
    """
    Use LLM to analyze a code patch and provide a concise comment
    on the rationale and impact of the changes.
    """
    prompt = (
        f"You are a technical documentation reviewer.\n"
        f"Below is a code section (unified diff format) from a pull request:\n\n"
        f"```\n{patch}\n```\n\n"
        f"These changes were made by a previous editor to improve the code or documentation.\n"
        f"Your task is to summarize each significant change using the following format:\n"
        f"- **categories**: [One or more of the following labels: "
        f"**Typo Fix**, **Grammar**, **Clarity**, **Consistency**, **Formatting**]\n"
        f"  - **change**: [Brief description of the modification]\n"
        f"  - **rationale**: [Explanation of why this change was made]\n"
        f"  - **impact**: [How this change improves the code or documentation]\n\n"
        f"Do not suggest any additional edits or improvements\n"
    )

    try:
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        print(f"❌ LLM patch comment failed: {e}")
        return ""

    total_token_usage = getattr(response.usage, 'total_tokens')
    print(
        f"🤖 LLM change comment received, total token usage: "
        f"{total_token_usage if total_token_usage is not None else 'N/A'}"
    )
    return response.choices[0].message.content, total_token_usage

def find_position_in_pr(pr: PullRequest.PullRequest, filename: str, line_number: int) -> Optional[int]:
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
                    # Parse the line number range, e.g., @@ -1,4 +1,5 @@
                    m = re.search(r'\+(\d+)', l)
                    if m:
                        current_line = int(m.group(1)) - 1
                elif l.startswith('+'):
                    if current_line is not None:
                        current_line += 1
                        if current_line == line_number:
                            return position
                elif not l.startswith('-'):
                    if current_line is not None:
                        current_line += 1
    return None  # Not found

def group_changed_sections(hunk: Hunk, max_context_gap: int = 2) -> List[List[Line]]:
    """
    Group lines in a hunk into combined change sections (context + additions/removals).
    Returns a list of sections, each section is a list of Line objects.
    """
    sections: List[List[Line]] = []
    current_section: List[Line] = []
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
                    # Too much gap, close section
                    if current_section:
                        sections.append(current_section)
                        current_section = []
                        in_change_block = False
                        context_counter = 0
            else:
                # no change block, skip or reset
                continue
        else:
            # Unknown type — flush current section
            if current_section:
                sections.append(current_section)
                current_section = []
                in_change_block = False
                context_counter = 0

    if current_section:
        sections.append(current_section)

    return sections

def review_changes_and_comment_by_section(pr: PullRequest.PullRequest) -> None:
    """
    Analyze PR diff, group changed sections, and comment on each section using LLM.
    """
    print("🔍 Parsing and grouping changed line sections...")

    try:
        diff_response = requests.get(
            pr.diff_url,
            headers={
                "Accept": "application/vnd.github.v3.diff",
                "Authorization": f"token {os.getenv('GITHUB_TOKEN')}"
            },
            timeout=30
        )
        diff_response.raise_for_status()
        diff_text = diff_response.text
    except Exception as e:
        print(f"❌ Failed to fetch PR diff: {e}")
        return

    patch_set = PatchSet(StringIO(diff_text))
    review_comments: List[Dict[str, Any]] = []
    review_token_usage: int = 0

    for patched_file in patch_set:
        filename = patched_file.path
        if patched_file.is_removed_file:
            continue

        for hunk in patched_file:
            changed_sections = group_changed_sections(hunk)

            for section in changed_sections:
                section_text = "".join(str(line) for line in section)
                comment, comment_token_usage = run_llm_comment_on_patch(section_text)
                review_token_usage += comment_token_usage if comment_token_usage else 0
                if comment.strip():
                    last_line = next((l for l in reversed(section) if l.is_added), None)
                    if not last_line:
                        print(
                            f"⚠️ Skipping section in `{filename}` — "
                            f"no added lines found:\n{section_text}"
                        )
                        continue
                    position = find_position_in_pr(pr, filename, last_line.target_line_no)
                    if position:
                        review_comments.append({
                            "path": filename,
                            "position": position,
                            "body": comment.strip()
                        })
                    else:
                        print(
                            f"⚠️ Unable to determine position for comment in `{filename}` "
                            f"at line {last_line.target_line_no}."
                        )

    if review_comments:
        print(f"📝 Submitting {len(review_comments)} section-level comments to {pr.html_url}")
        try:
            comment_message = (
                f"Automated LLM code review (section-based).\n\n"
                f"LLM usage details:\n"
                f"- Total tokens used: {review_token_usage}.\n"
                f"- Used deployment: {AZURE_OPENAI_DEPLOYMENT}\n"
                f"- API version: {AZURE_OPENAI_API_VERSION}"
            )
            pr.create_review(
                body=comment_message,
                event="COMMENT",
                comments=review_comments
            )
        except Exception as e:
            print(f"❌ Failed to submit review comments: {e}")
    else:
        print("✅ No meaningful comments to submit.")

def main() -> None:
    """
    Main entry point for the review script.
    """
    base_branch = BRANCH_NAME if BRANCH_NAME else repo.default_branch
    try:
        base_ref = repo.get_git_ref(f"heads/{base_branch}")
        base_sha = base_ref.object.sha
    except Exception as e:
        print(f"❌ Failed to get base branch reference: {e}")
        sys.exit(1)

    print(f"📥 Fetching `{TARGET_FILE}` from branch `{base_branch}`...")
    try:
        blob = repo.get_contents(TARGET_FILE, ref=base_branch)
        orig_content = blob.decoded_content.decode()
    except Exception as e:
        print(f"❌ Failed to fetch file `{TARGET_FILE}`: {e}")
        sys.exit(1)

    print("🤖 Running LLM review...")
    updated_content, llm_review_details = run_llm_review(TARGET_FILE, orig_content, USER_INSTRUCTIONS)

    new_branch = f"review-{base_branch}-{TARGET_FILE.replace('/', '-')}-{int(time.time())}"
    print(f"🌿 Creating new branch `{new_branch}`...")
    try:
        repo.create_git_ref(ref=f"refs/heads/{new_branch}", sha=base_sha)
    except Exception as e:
        print(f"❌ Failed to create new branch `{new_branch}`: {e}")
        sys.exit(1)

    print(f"✍️ Committing updated file to `{new_branch}`...")
    try:
        file = repo.get_contents(TARGET_FILE, ref=new_branch)
        repo.update_file(
            path=TARGET_FILE,
            message=f"docs: review {TARGET_FILE}",
            content=updated_content,
            sha=file.sha,
            branch=new_branch
        )
    except Exception as e:
        print(f"❌ Failed to commit updated file: {e}")
        sys.exit(1)

    print("📬 Creating Pull Request...")
    try:
        pr_message = (
            f"Automated review and documentation improvements for `{TARGET_FILE}` "
            f"on branch `{base_branch}`\n\n"
            f"LLM usage details:\n{llm_review_details}"
        )
        pr = repo.create_pull(
            title=f"Review `{base_branch}-{TARGET_FILE}`",
            body=pr_message,
            head=new_branch,
            base=base_branch
        )
    except Exception as e:
        print(f"❌ Failed to create pull request: {e}")
        sys.exit(1)

    print(f"✅ PR created: {pr.html_url}")

    if ENABLE_REVIEW_CHANGES:
        print("🧠 Running LLM diff review and commenting...")
        review_changes_and_comment_by_section(pr)

if __name__ == "__main__":
    main()
