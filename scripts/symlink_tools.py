"""
Traverse all directories and
delete folders if all files are of type symlink.
"""
import shutil
from pathlib import Path


def main(directory_path: Path):
    if not directory_path.is_dir():
        print(f"{directory_path} is not a valid directory.")
        return

    symbolic_links_count = 0
    non_symbolic_links_count = 0

    # Recursively process subdirectories first
    for item in directory_path.iterdir():
        if item.is_dir():
            main(item)

    # Check the current directory's contents
    for item in directory_path.iterdir():
        if item.is_symlink():
            symbolic_links_count += 1
        else:
            non_symbolic_links_count += 1

    if symbolic_links_count > 0 and non_symbolic_links_count == 0:
        print(f"Deleting directory: {directory_path}")
        shutil.rmtree(directory_path)


if __name__ == "__main__":
    base_path = Path("sample_directory")
    main(base_path)
