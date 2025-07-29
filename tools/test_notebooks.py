import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple, Optional, List

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor


SINGLE_NOTEBOOK_TIMEOUT = 1200
CONCURRENT_WORKERS = 4


def should_skip(notebook_path: str, skip_list: List[str]) -> bool:
    return any(skip in notebook_path for skip in skip_list)


def run_notebook(notebook_path: str, root: str) -> Tuple[bool, Optional[str]]:
    """Execute a single notebook and print outputs of each cell."""
    try:
        print(f"🔧 running: {notebook_path}")
        with open(notebook_path, encoding="utf-8") as f:
            nb = nbformat.read(f, as_version=4)

        ep = ExecutePreprocessor(timeout=SINGLE_NOTEBOOK_TIMEOUT, kernel_name="python3")
        ep.preprocess(nb, {"metadata": {"path": root}})

        # Print outputs of each cell
        for i, cell in enumerate(nb.cells):
            if cell.cell_type == 'code':
                print(f"\n📦 Cell {i + 1}:\n{cell.source.strip()}")
                for output in cell.get('outputs', []):
                    if output.output_type == 'stream':
                        print(output.text)
                    elif output.output_type == 'error':
                        print("❌ Error:")
                        print("\n".join(output.get('traceback', [])))
                    elif output.output_type == 'execute_result':
                        data = output.get('data', {})
                        if 'text/plain' in data:
                            print(data['text/plain'])
                    elif output.output_type == 'display_data':
                        data = output.get('data', {})
                        if 'text/plain' in data:
                            print(data['text/plain'])

        return True, None
    except Exception as e:
        return False, str(e)


def run_all_notebooks(
        path: str=".",
        skip_list: List[str]=None,
        max_workers: int=CONCURRENT_WORKERS,
    ) -> None:
    abs_path = os.path.abspath(path)
    print(f"🔍 Scanning for notebooks in: {abs_path}\n")

    skip_list = skip_list or []

    notebook_paths: List[str] = []
    for root, _, files in os.walk(abs_path):
        for file in files:
            if file.endswith(".ipynb") and not file.startswith("."):
                full_path = os.path.join(root, file)
                if should_skip(full_path, skip_list):
                    print(f"⏭️ Skipped: {full_path}")
                    continue
                notebook_paths.append(full_path)

    if not notebook_paths:
        print("❌ No notebooks were found. Check the folder path or repo contents.")
        sys.exit(1)

    print(f"▶️ Running {len(notebook_paths)} notebooks using {max_workers} workers...\n")

    success_notebooks: List[str] = []
    failed_notebooks: List[Tuple[str, str]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(run_notebook, path, os.path.dirname(path)): path
            for path in notebook_paths
        }

        for future in as_completed(futures):
            notebook_path = futures[future]
            try:
                success, error = future.result()
                if success:
                    print(f"✅ Success: {notebook_path}")
                    success_notebooks.append(notebook_path)
                else:
                    print(f"❌ Failed: {notebook_path}\nError: {error}\n")
                    failed_notebooks.append((notebook_path, error))
            except Exception as e:
                print(f"❌ Exception during execution of {notebook_path}\nError: {e}\n")
                failed_notebooks.append((notebook_path, str(e)))

    # 📋 Summary
    print("\n🧾 Notebook Execution Summary")
    print(f"✅ {len(success_notebooks)} succeeded")
    print(f"❌ {len(failed_notebooks)} failed\n")

    if failed_notebooks:
        print("🚨 Failed notebooks:")
        for nb, error in failed_notebooks:
            last_line = error.strip().splitlines()[-1] if error else "Unknown error"
            print(f" - {nb}\n   ↳ {last_line}")
        sys.exit(1)

    print("🏁 All notebooks completed successfully.")


if __name__ == "__main__":
    args: List[str] = sys.argv[1:]

    # NOTE: Define skip list (can use full paths or substrings)
    skip_list = [
        "build_person_directory.ipynb",  # Skip due to "new_face_image_path" needed to be added manually
    ]

    if not args:
        run_all_notebooks("notebooks", skip_list=skip_list)
    else:
        failed: List[Tuple[str, str]] = []
        for notebook_path in args:
            if should_skip(notebook_path, skip_list):
                print(f"⏭️ Skipped: {notebook_path}")
                continue

            if notebook_path.endswith(".ipynb") and os.path.isfile(notebook_path):
                print(f"▶️ Running: {notebook_path}")
                success, error = run_notebook(notebook_path, os.path.dirname(notebook_path))
                if success:
                    print(f"✅ Success: {notebook_path}\n")
                else:
                    print(f"❌ Failed: {notebook_path}\nError: {error}\n")
                    failed.append((notebook_path, error))
            else:
                print(f"⚠️ Not a valid notebook file: {notebook_path}")
                failed.append((notebook_path, "Invalid path or not a .ipynb file"))

        # Summary
        print("🧾 Execution Summary")
        print(f"✅ {len(args) - len(failed)} succeeded")
        print(f"❌ {len(failed)} failed")

        if failed:
            print("🚨 Failed notebooks:")
            for nb, error in failed:
                last_line = error.strip().splitlines()[-1] if error else "Unknown error"
                print(f" - {nb}\n   ↳ {last_line}")
            sys.exit(1)
        else:
            print("🏁 All selected notebooks completed successfully.")
