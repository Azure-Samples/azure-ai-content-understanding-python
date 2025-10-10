import argparse
import os
import re
from pathlib import Path

from dotenv import load_dotenv

from utils.aoai_utils import AzureOpenAIAssistant
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
    """Detect the language based on file extension."""
    ext = os.path.splitext(filename)[1].lower()
    for lang, lang_ext in EXT_MAP.items():
        if ext == lang_ext:
            return lang
    return None


def split_name(name: str, lang: str):
    """Split a filename (without extension) into lowercase words."""
    if lang in ("java", "csharp", "kotlin", "swift", "scala", "rust"):
        return [w.lower() for w in re.findall(r"[A-Z][a-z0-9]*", name)]
    elif lang in ("javascript", "typescript", "go"):
        return [w.lower() for w in re.findall(r"[A-Z]?[a-z0-9]+", name)]
    elif lang == "python":
        return name.split("_")
    elif lang in ("shell",):
        return name.split("-")
    else:
        parts = re.findall(r"[A-Z]?[a-z0-9]+", name)
        return [p.lower() for p in parts] if parts else [name.lower()]


def join_name(words, lang: str):
    """Join words into the appropriate filename style for the target language."""
    if lang == "python":
        return "_".join(words)
    elif lang in ("java", "csharp", "kotlin", "swift", "scala", "rust"):
        return "".join(w.capitalize() for w in words)
    elif lang in ("javascript", "typescript", "go"):
        return words[0] + "".join(w.capitalize() for w in words[1:])
    elif lang in ("shell",):
        return "-".join(words)
    else:
        return "_".join(words)


def convert_filename(filename: str, target_lang: str) -> str:
    """Convert a filename by auto-detecting source language and applying target style."""
    source_lang = detect_language(filename)
    if not source_lang:
        raise ValueError(f"Could not detect language from extension for file: {filename}")

    name, _ = os.path.splitext(filename)
    words = split_name(name, source_lang)
    new_name = join_name(words, target_lang)
    return new_name + EXT_MAP[target_lang]


### Convert and write samples ###
def collect_sdk_context_from_local(sdk_path: Path) -> str:
    """
    Collects the content of all SDK source files from a local folder.

    Args:
        sdk_path (Path): Path to the SDK source directory.

    Returns:
        str: Combined text content of all relevant SDK files.
    """
    context = []
    for root, _, files in os.walk(sdk_path):
        for f in files:
            if f.endswith(tuple(EXT_MAP.values())):
                file_path = Path(root) / f
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                        context.append(f"\n### {file_path}\n{file.read()}")
                except Exception as e:
                    print(f"⚠️ Warning: Could not read {file_path}: {e}")
    return "\n".join(context)


def convert_and_write_sample(filename, source_code, target_lang, sdk_context, assistant, output_path):
    """
    Converts and writes a single sample file to the output directory.

    Args:
        filename (str): Source filename.
        source_code (str): Source code to convert.
        target_lang (str): Target programming language.
        sdk_context (str): SDK context for conversion.
        assistant (AzureOpenAIAssistant): OpenAI assistant.
        output_path (Path): Output directory.
    """
    src_lang = detect_language(filename)
    if not src_lang:
        src_lang = Path(filename).suffix[1:] if "." in filename else "unknown"

    dest_file = output_path / convert_filename(filename, target_lang)
    os.makedirs(dest_file.parent, exist_ok=True)

    print(f"🚀 Converting {filename} → {dest_file}")
    try:
        converted = assistant.convert_code(
            source_code=source_code,
            source_lang=src_lang,
            target_lang=target_lang,
            sdk_context=sdk_context,
        )
        with open(dest_file, "w", encoding="utf-8") as out:
            out.write(converted)
    except Exception as e:
        print(f"❌ Error converting {filename}: {e}")


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
        sdk_files = gh_helper.fetch_folder_files(
            folder_path=folder_path,
            recursive=True,
            extensions=EXT_MAP.values(),
        )
        sdk_context = "\n".join(f"\n### {fname}\n{content}" for fname, content in sdk_files.items())
    else:
        sdk_context = collect_sdk_context_from_local(Path(sdk_source))

    print("✅ SDK context collection complete.\n")
    # Ensure output directory exists before saving sdk_context
    os.makedirs(output_path, exist_ok=True)
    # save sdk_context for debugging
    with open(output_path / "sdk_context.txt", "w", encoding="utf-8") as f:
        f.write(sdk_context)
    print(f"✅ SDK context saved to '{output_path}/sdk_context.txt'.\n")

    # Load environment variables from .env file in the same directory as this script
    dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_dotenv(dotenv_path)

    assistant = AzureOpenAIAssistant(
        aoai_end_point=os.getenv("AZURE_OPENAI_ENDPOINT"),
        aoai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        aoai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
    )

    # Process each sample file one at a time (no accumulation)
    if samples_source.startswith("https://github.com/"):
        owner, repo, ref, folder_path = parse_github_url(samples_source)
        gh_helper = GitHubRepoHelper(f"{owner}/{repo}", github_token, ref=ref)
        file_paths = gh_helper.list_folder_file_paths(
            folder_path=folder_path,
            recursive=True,
            extensions=list(EXT_MAP.values()),
        )
        for file_path in file_paths:
            file_content = gh_helper.fetch_file_content(file_path)
            if file_content is None:
                print(f"⚠️ Skipping {file_path}: Could not fetch content.")
                continue
            file_name = os.path.basename(file_path)
            convert_and_write_sample(file_name, file_content, target_lang, sdk_context, assistant, output_path)
    else:
        for root, _, files in os.walk(samples_source):
            for f in files:
                src_file = Path(root) / f
                try:
                    with open(src_file, "r", encoding="utf-8", errors="ignore") as file:
                        source_code = file.read()
                    convert_and_write_sample(src_file.name, source_code, target_lang, sdk_context, assistant, output_path)
                except Exception as e:
                    print(f"⚠️ Skipping {src_file}: {e}")



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
