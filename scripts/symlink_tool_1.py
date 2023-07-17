""" Traverse all directories and 
    delete folders if all files are symlink.
"""

from pathlib import Path


def traverse_directory(directory_path):
    for item_path in directory_path:
        yield item_path


def unlink_all_symlinks(directory):
    for item in traverse_directory(directory):
        if item.is_symlink():
            print(f"Unlink item {item}.")
            item.unlink()
        else:
            print(f"Skip!! item {item} is not a symlink.")


def remove_empty_directories(directory):
    for item in traverse_directory(directory):
        if item.is_dir():
            contain_files = any(item.iterdir())

            if contain_files is False:
                print(item.rmdir())
                print(f"Remove directory {item}.")
            else:
                print(f"Skip!! directory {item} contains file.")


def main(path):
    directory = Path(path)
    unlink_all_symlinks(directory.glob("**/*"))
    remove_empty_directories(sorted(directory.glob("**/*"), reverse=True))


if __name__ == "__main__":
    basepath = "sample_directory"
    main(basepath)
