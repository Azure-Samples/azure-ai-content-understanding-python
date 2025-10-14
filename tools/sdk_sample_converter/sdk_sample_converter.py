import argparse
import os
import re
from typing import Union
from pathlib import Path

from dotenv import load_dotenv

from utils.aoai_utils import AzureOpenAIAssistant, FileCategories
from utils.github_utils import GitHubRepoHelper, parse_github_url

EXT_MAP = {
    "python": ".py",           # Python scripts
    "csharp": ".cs",           # C# source files
    "java": ".java",           # Java source files
    "javascript": ".js",       # JavaScript files
    "typescript": ".ts",       # TypeScript files
    "c": ".c",                 # C source files
    "cpp": ".cpp",             # C++ source files
    "go": ".go",               # Go language files
    "ruby": ".rb",             # Ruby scripts
    "php": ".php",             # PHP scripts
    "swift": ".swift",         # Swift files
    "kotlin": ".kt",           # Kotlin source files
    "rust": ".rs",             # Rust source files
    "scala": ".scala",         # Scala source files
    "perl": ".pl",             # Perl scripts
    "shell": ".sh",            # Shell scripts
    "r": ".r",                 # R scripts
    "dart": ".dart",           # Dart files
    "haskell": ".hs",          # Haskell source files
    "lua": ".lua",             # Lua scripts
}


### Convert file name ###
def detect_language(filename: str) -> str:
    """Detect language from file extension."""
    ext = os.path.splitext(filename)[1].lower()
    for lang, lang_ext in EXT_MAP.items():
        if ext == lang_ext:
            return lang
    return None


def split_name(name: str, lang: str):
    """Split filename into lowercase words."""
    if lang in ("java", "csharp", "kotlin", "swift", "scala", "rust"):
        return [w.lower() for w in re.findall(r"[A-Z]?[a-z0-9]+", name)]
    elif lang in ("javascript", "typescript", "go"):
        return [w.lower() for w in re.findall(r"[A-Z]?[a-z0-9]+", name)]
    elif lang == "python":
        return name.split("_")
    elif lang == "shell":
        return name.split("-")
    else:
        parts = re.findall(r"[A-Z]?[a-z0-9]+", name)
        return [p.lower() for p in parts] if parts else [name.lower()]


def join_name(words, lang: str):
    """Join words into target filename style."""
    if lang == "python":
        return "_".join(words)
    elif lang in ("java", "csharp", "kotlin", "swift", "scala", "rust"):
        return "".join(w.capitalize() for w in words)  # PascalCase
    elif lang in ("javascript", "typescript", "go"):
        return words[0] + "".join(w.capitalize() for w in words[1:])  # camelCase
    elif lang == "shell":
        return "-".join(words)
    else:
        return "_".join(words)


def convert_filename(filename: str, target_lang: str) -> str:
    """Convert a filename by detecting source language and applying target style."""
    source_lang = detect_language(filename)
    if not source_lang:
        print(f"⚠️ Unknown extension for {filename}, keeping original name.")
        return filename

    name, _ = os.path.splitext(filename)
    words = split_name(name, source_lang)
    new_name = join_name(words, target_lang)

    ext = EXT_MAP[target_lang]
    if not ext.startswith("."):
        ext = "." + ext

    return new_name + ext


### Convert and write samples ###
def collect_sdk_context_from_local(sdk_path: Path) -> dict[str, str]:
    """
    Collects the content of all SDK source files from a local folder.

    Args:
        sdk_path (Path): Path to the SDK source directory.

    Returns:
        dict[str, str]: A dictionary mapping relative file paths to their decoded UTF-8 content.
        Example:
            {
                "sdk/module/__init__.py": "...",
                "sdk/module/example.py": "..."
            }
    """
    file_dict = {}
    for root, _, files in os.walk(sdk_path):
        for f in files:
            if f.endswith(tuple(EXT_MAP.values())):
                file_path = Path(root) / f
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                        file_dict[str(file_path.relative_to(sdk_path))] = file.read()
                except Exception as e:
                    print(f"⚠️ Warning: Could not read {file_path}: {e}")
    return file_dict


def get_sample_file_paths(
        folder_path: str, 
        gh_helper: GitHubRepoHelper | None,
    ) -> list:
    """
    Get list of sample file paths from local directory or GitHub repo.

    Args:
        samples_source (str): Local path or GitHub tree URL for sample files.
        github_token (str | None): Optional GitHub token for private repos.
        is_local (bool): True if samples_source is a local path, False if it's a GitHub URL.

    Returns:
        list: List of file paths to sample files.
    """
    if gh_helper:
        return gh_helper.list_folder_file_paths(
            folder_path=folder_path,
            recursive=True,
        )
    else:
        file_paths = []
        for root, _, files in os.walk(folder_path):
            for f in files:
                file_paths.append(Path(root) / f)
        return file_paths


def read_file_content(file_path: Union[str, Path], gh_helper=None) -> str | None:
    """Read or fetch file content depending on GitHub source."""
    if gh_helper:
        content = gh_helper.fetch_file_content(file_path)
        if content is None:
            print(f"⚠️ Skipping {file_path}: Could not fetch content.")
        return content
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        print(f"⚠️ Skipping {file_path}: {e}")
        return None


def convert_and_write_sample(
        file_path: Union[str, Path],
        source_code: str,
        target_lang: str,
        sdk_files_dict: dict,
        assistant: AzureOpenAIAssistant,
        output_path: Path,
        is_doc: bool = False,
    ) -> str:
    """
    Converts and writes a single sample file to the output directory.
    """
    src_path = Path(file_path)
    src_lang = detect_language(src_path.name) or (src_path.suffix[1:] if src_path.suffix else "unknown")

    dest_filename = convert_filename(src_path.name, target_lang)
    dest_file = output_path / src_path.parent / dest_filename
    dest_file.parent.mkdir(parents=True, exist_ok=True)

    sdk_context = "\n\n".join(f"# File: {path}\n{content}" for path, content in sdk_files_dict.items() if content)

    print(f"🚀 Converting {file_path} → {dest_file}")
    try:
        if is_doc:
            converted = assistant.convert_doc(
                source_doc=source_code,
                source_lang=src_lang,
                target_lang=target_lang,
                sdk_context=sdk_context,
            )
        else:
            converted = assistant.convert_code(
                source_code=source_code,
                source_lang=src_lang,
                target_lang=target_lang,
                sdk_context=sdk_context,
            )
        dest_file.write_text(converted, encoding="utf-8")
        return converted
    except Exception as e:
        print(f"❌ Error converting {file_path}: {e}")
        return ""


def convert_and_write_samples(
        file_categories: FileCategories,
        target_lang: str,
        sdk_files_dict: dict,
        assistant: AzureOpenAIAssistant,
        output_path: Path,
        gh_helper=None,
    ) -> None:
    """
    Converts and writes multiple files to the output directory,
    handling different categories differently.
    """
    # --- 1️⃣ Helpers: Convert, save, and add into sdk_context ---
    for helper in file_categories.helpers:
        source_code = read_file_content(helper, gh_helper)
        if not source_code:
            continue
        converted_content = convert_and_write_sample(helper, source_code, target_lang, sdk_files_dict, assistant, output_path)
        # optionally add helper content to sdk_context
        sdk_files_dict.setdefault("helpers", {})[helper] = converted_content

    # --- 2️⃣ Samples: Convert and save ---
    for sample in file_categories.samples:
        source_code = read_file_content(sample, gh_helper)
        if not source_code:
            continue
        _ = convert_and_write_sample(sample, source_code, target_lang, sdk_files_dict, assistant, output_path)

    # --- 3️⃣ Docs: Update and save ---
    for doc in file_categories.docs:
        source_code = read_file_content(doc, gh_helper)
        if not source_code:
            continue
        _ = convert_and_write_sample(sample, source_code, target_lang, sdk_files_dict, assistant, output_path, is_doc=True)

    # --- 4️⃣ Other files: Just copy ---
    for other in file_categories.other_files:
        try:
            src_path = Path(other)
            dest_path = output_path / src_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(src_path.read_bytes())
            print(f"📁 Copied {other}")
        except Exception as e:
            print(f"⚠️ Could not copy {other}: {e}")


def convert_folder(
        sdk_source: str,
        samples_source: str,
        target_lang: str,
        output_path: Path,
        github_token: str | None = None,
    ):
    """
    Converts all SDK sample files in a folder or GitHub repo into another language.

    Args:
        sdk_source (str): Local path or GitHub tree URL for SDK source (e.g., https://github.com/<owner>/<repo>/tree/<commit>/<path>).
        samples_source (str): Local path or GitHub tree URL for sample files (e.g., https://github.com/<owner>/<repo>/tree/<commit>/<path>).
        target_lang (str): Target programming language.
        output_path (Path): Output folder for converted files.
        github_token (str | None): Optional GitHub token for private repos.
    """
    print("📘 Collecting SDK context...")

    if sdk_source.startswith("https://github.com/"):
        owner, repo, ref, folder_path = parse_github_url(sdk_source)
        gh_helper = GitHubRepoHelper(f"{owner}/{repo}", github_token, ref=ref)
        sdk_files_dict = gh_helper.fetch_folder_files(
            folder_path=folder_path,
            recursive=True,
            extensions=EXT_MAP.values(),
        )
    else:
        sdk_files_dict = collect_sdk_context_from_local(Path(sdk_source))

    print("✅ SDK context collection complete.\n")
    # Ensure output directory exists before saving sdk_context
    os.makedirs(output_path, exist_ok=True)
    # save sdk_context for debugging
    with open(output_path / "sdk_context.txt", "w", encoding="utf-8") as f:
        f.write("\n\n".join(f"# File: {path}\n{content}" for path, content in sdk_files_dict.items() if content))
    print(f"✅ SDK context saved to '{output_path}/sdk_context.txt'.\n")

    # Load environment variables from .env file in the same directory as this script
    dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_dotenv(dotenv_path)

    aoai_assistant = AzureOpenAIAssistant(
        aoai_end_point=os.getenv("AZURE_OPENAI_ENDPOINT"),
        aoai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        aoai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
    )

    if samples_source.startswith("https://github.com/"):
        owner, repo, ref, folder_path = parse_github_url(samples_source)
        gh_helper = GitHubRepoHelper(f"{owner}/{repo}", github_token, ref=ref)
    else:
        gh_helper = None
        folder_path = samples_source
        
    file_paths = get_sample_file_paths(folder_path, gh_helper)
    file_categories = aoai_assistant.classify_file_paths(file_paths, target_lang)
    print(f"{file_categories.total_len()} of {len(file_paths)} files was categorized.")
    convert_and_write_samples(file_categories, target_lang, sdk_files_dict, aoai_assistant, output_path, gh_helper)


def parse_args():
    parser = argparse.ArgumentParser(description="SDK Sample Converter using Azure OpenAI Assistant")
    parser.add_argument(
        "--sdk-source",
        required=True,
        help="Local path or GitHub tree URL for SDK source (e.g., https://github.com/<owner>/<repo>/tree/<commit>/<path>)",
    )
    parser.add_argument(
        "--samples-source",
        required=True,
        help="Local path or GitHub tree URL for sample files (e.g., https://github.com/<owner>/<repo>/tree/<commit>/<path>)",
    )
    parser.add_argument(
        "--target-lang",
        required=True,
        help="Target programming language (e.g., python, java, csharp)",
    )
    parser.add_argument(
        "--output",
        default="./converted_samples",
        help="Output folder for converted files",
    )
    parser.add_argument(
        "--github-token",
        default=os.getenv("GITHUB_TOKEN", ""),
        help="Optional GitHub token for accessing private repositories",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    convert_folder(
        args.sdk_source,
        args.samples_source,
        args.target_lang,
        Path(args.output),
        args.github_token,
    )
