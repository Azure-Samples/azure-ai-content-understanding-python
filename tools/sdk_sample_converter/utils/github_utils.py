import re

from github import Github


class GitHubRepoHelper:
    def __init__(self, repo_name: str, token: str = None, ref: str = None):
        self.g = Github(token) if token else Github()
        self.repo = self.g.get_repo(repo_name)
        self.ref = ref

    def list_folder_file_paths(
        self,
        folder_path: str,
        recursive: bool = True,
        extensions: list[str] | None = None,
    ) -> list[str]:
        """
        Lists all file paths from a specific folder (and optionally its subfolders)
        in the GitHub repository, with optional extension filtering.

        Args:
            folder_path (str):
                Path to the folder inside the repository to list files from.
                Example: "sdk/contentunderstanding/azure-ai-contentunderstanding".
            recursive (bool, optional):
                Whether to recursively list files from all subdirectories.
                Defaults to True.
            extensions (list[str], optional):
                List of file extensions to include in the listing (e.g., [".py", ".js", ".ts"]).
                If None, all file types are included.

        Returns:
            list[str]:
                A list of relative file paths that match the given criteria.
                Example: ["sdk/module/__init__.py", "sdk/module/example.py"]
        """
        file_paths = []

        def _collect_paths(path):
            contents = self.repo.get_contents(path, ref=self.ref) if self.ref else self.repo.get_contents(path)
            for item in contents:
                if item.type == "file":
                    if extensions and not any(item.name.endswith(ext) for ext in extensions):
                        continue
                    file_paths.append(item.path)
                elif item.type == "dir" and recursive:
                    _collect_paths(item.path)

        _collect_paths(folder_path)
        return file_paths

    def fetch_folder_files(
        self,
        folder_path: str,
        recursive: bool = True,
        extensions: list[str] | None = None,
    ) -> dict[str, str]:
        """
        Fetches all files from a specific folder (and optionally its subfolders)
        in the GitHub repository and returns a mapping of file paths to file content.

        Args:
            folder_path (str):
                Path to the folder inside the repository to fetch files from.
                Example: "sdk/contentunderstanding/azure-ai-contentunderstanding".
            recursive (bool, optional):
                Whether to recursively fetch files from all subdirectories.
                Defaults to True.
            extensions (list[str], optional):
                List of file extensions to include (e.g., [".py", ".js", ".ts"]).
                If None, all file types are included.

        Returns:
            dict[str, str]:
                A dictionary mapping relative file paths to their decoded UTF-8 content.
                Example:
                    {
                        "sdk/module/__init__.py": "...",
                        "sdk/module/example.py": "..."
                    }
        """
        file_dict = {}

        def _collect_files(path):
            contents = self.repo.get_contents(path, ref=self.ref) if self.ref else self.repo.get_contents(path)
            for item in contents:
                if item.type == "file":
                    if extensions and not any(item.name.endswith(ext) for ext in extensions):
                        continue
                    try:
                        content = item.decoded_content.decode("utf-8", errors="ignore")
                        file_dict[item.path] = content
                    except Exception as e:
                        print(f"⚠️ Skipping {item.path}: {e}")
                elif item.type == "dir" and recursive:
                    _collect_files(item.path)

        _collect_files(folder_path)
        return file_dict

    def fetch_file_content(self, file_path: str) -> str | None:
        """
        Fetches the content of a single file from the GitHub repository.

        Args:
            file_path (str):
                Path to the file inside the repository to fetch.
                Example: "sdk/module/__init__.py".

        Returns:
            str | None:
                The decoded UTF-8 content of the file, or None if the file could not be fetched.
        """
        try:
            item = self.repo.get_contents(file_path, ref=self.ref) if self.ref else self.repo.get_contents(file_path)
            return item.decoded_content.decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"⚠️ Skipping {file_path}: {e}")
            return None

def parse_github_url(url: str):
    """
    Parses a GitHub tree URL and returns (owner, repo, ref, folder_path).
    Example: https://github.com/<owner>/<repo>/tree/<ref>/<folder_path>
    Returns: (owner, repo, ref, folder_path) 
    """
    m = re.match(r"https://github.com/([^/]+)/([^/]+)/tree/([^/]+)/(.*)", url)
    if not m:
        raise ValueError(f"Invalid GitHub tree URL: {url}")
    owner, repo, ref, folder_path = m.groups()
    return owner, repo, ref, folder_path
