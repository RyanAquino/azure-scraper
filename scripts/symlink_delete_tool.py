"""
Traverse all directories and
delete folders if all files are of type symlink.
"""
import argparse
import shutil
from pathlib import Path


def run(directory_path: Path):
    if not directory_path.is_dir():
        print(f"{directory_path} is not a valid directory.")
        return

    symbolic_links_count = 0
    non_symbolic_links_count = 0

    # Recursively process subdirectories first
    for item in directory_path.iterdir():
        if item.is_dir():
            run(item)

    # Check the current directory's contents
    for item in directory_path.iterdir():
        if item.is_symlink():
            symbolic_links_count += 1
        else:
            non_symbolic_links_count += 1

    if symbolic_links_count > 0 and non_symbolic_links_count == 0:
        print(f"Deleting directory: {directory_path}")
        shutil.rmtree(directory_path)


def main():
    parser = argparse.ArgumentParser(description="Retrieve the base absolute/relative path directory.")
    parser.add_argument("--base-directory", type=str, help="Base absolute/relative path directory", required=True)

    args = parser.parse_args()
    base_directory = args.base_directory

    if not Path(base_directory).is_dir():
        print("Directory not valid. Please run again")
        return

    return run(Path(base_directory))


if __name__ == "__main__":
    main()
