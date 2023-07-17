""" Traverse all directories and 
    delete folders if all files are symlink.
"""

from pathlib import Path


def traverse_directory(directory):
    for item in directory.glob("*"):
        if item.is_dir():
            contain_files = any(item.iterdir())

            if contain_files is False:
                item.rmdir()
                print(f"Remove directory {item}")

            traverse_directory(item)

        elif item.is_symlink():
            item.unlink()
            print(f"Removing symbolic link: {item}")


if __name__ == "__main__":
    basepath = Path("sample_directory")
    traverse_directory(basepath)
