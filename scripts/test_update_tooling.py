import os


def create_symlinks():
    """
    Create symbolic links for testing the change_symlink function.
    """
    current_directory = os.getcwd()
    parent_directory = os.path.join(current_directory, "root")

    # Create the parent root directory
    os.makedirs(parent_directory)

    # Create directories
    os.makedirs(os.path.join(parent_directory, "dir1", "subdir"))

    # Create files
    open(os.path.join(parent_directory, "file1.txt"), "w").close()
    open(os.path.join(parent_directory, "dir1", "file2.txt"), "w").close()
    open(os.path.join(parent_directory, "dir1", "subdir", "file3.txt"), "w").close()

    # Create symbolic links
    os.symlink(
        os.path.join(parent_directory, "file1.txt"),
        os.path.join(parent_directory, "link1.txt"),
    )
    os.symlink(
        os.path.join(parent_directory, "dir1", "file2.txt"),
        os.path.join(parent_directory, "dir1", "link2.txt"),
    )
    os.symlink(
        os.path.join(parent_directory, "dir1", "subdir", "file3.txt"),
        os.path.join(parent_directory, "link3.txt"),
    )

    print(os.path.join(parent_directory, "link1.txt"))
    print(os.path.join(parent_directory, "dir1", "link2.txt"))
    print(os.path.join(parent_directory, "link3.txt"))


if __name__ == "__main__":
    create_symlinks()
