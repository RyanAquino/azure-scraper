""" Create sample nested directories with symlink
"""
from pathlib import Path
import platform
import os


def create_nested_directories(path, link, depth=5):
    if depth > 0:
        path = Path(path, f"directory_{depth}")
        path.mkdir(parents=True, exist_ok=True)

        empty_path = Path(path, f"empty_directory_{depth}")
        empty_path.mkdir(parents=True, exist_ok=True)

        file_path1 = Path(path, "symlink_file1")
        file_path2 = Path(path, "symlink_file2")
        file_path3 = Path(path, "symlink_file3")
        # os.symlink(file_path1, link)
        # os.symlink(file_path2, link)
        # os.symlink(file_path3, link)

        create_nested_directories(path, link, depth=depth - 1)


if __name__ == "__main__":
    base_path = Path("sample_directory")
    symlink = Path("link_here", "test")
    create_nested_directories(base_path, symlink)
