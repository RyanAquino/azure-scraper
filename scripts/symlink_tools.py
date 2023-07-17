""" Traverse all directories and 
    delete folders if all files are symlink.
"""

from pathlib import Path


def traverse_directory(directory_path):
    for item_path in directory_path:
        yield item_path


def run_symlink_tool1(directory):
    for item in traverse_directory(directory):
        if item.is_dir():
            prev_file_count = len(list(item.glob("**/*")))
            for item_files in item.glob("**/*"):
                if item_files.is_symlink():
                    print(f"Unlink item {item}.")
                    item.unlink()
                else:
                    print(f"Skip!! item {item} is not a symlink.")
                    new_file_count = len(list(item.glob("**/*")))

            if prev_file_count == 0:
                print(f"Skip!! Directory {item} does not have any files.")
                continue
            elif new_file_count > 0:
                print(f"Skip!! Directory {item} contains non-symlink files.")
                continue

            elif new_file_count == 0:
                item.rmdir()
                print(f"Remove directory {item}.")


if __name__ == "__main__":
    base_path = Path("sample_directory")
    run_symlink_tool1(sorted(base_path.glob("**/*"), reverse=True))
