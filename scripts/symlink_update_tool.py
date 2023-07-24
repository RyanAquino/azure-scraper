"""
SymlinkUpdater
==============

The SymlinkUpdater module provides a function to change symbolic links in a directory hierarchy
by replacing the prefix source link with a new prefix source. It allows for efficient batch updates of symbolic links
in a given directory and its subdirectories.
"""
import argparse
from pathlib import Path


def change_symlinks(root_dir: str, prefix_source: str, new_prefix_source: str):
    root_path = Path(root_dir)

    # Iterate over all files and directories recursively
    for path in root_path.rglob('*'):
        if path.is_symlink():
            target = path.resolve()

            # Check if the symlink's target starts with the prefix source
            if str(target).startswith(prefix_source):
                # Construct the new target path by replacing the prefix source with the new prefix source
                new_target = Path(str(target).replace(prefix_source, new_prefix_source))

                # Remove the old symlink
                path.unlink()

                # Create a new symlink with the updated target
                print(f"Path: {path}")
                print(f"Previous Target: {target}")
                print(f"New Target: {new_target}")
                path.symlink_to(new_target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process root directory and prefix inputs.")
    parser.add_argument("--root-dir", type=str, help="Root directory", required=True)
    parser.add_argument("--prefix-source", type=str, help="Prefix source link", required=True)
    parser.add_argument("--new-prefix-source", type=str, help="New prefix source", required=True)

    args = parser.parse_args()

    root_dir_input = args.root_dir
    prefix_source_input = args.prefix_source
    new_prefix_source_input = args.new_prefix_source

    change_symlinks(root_dir_input, prefix_source_input, new_prefix_source_input)
