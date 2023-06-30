# delete folder if all files in the folder are type of symlinks

## todo
* folder should be deleted if all files within that folder are only type of symlink
* if there is any type of file other that symlink then no action should be taken
* if there is another folder with that folder then no action should be taken
* if nested folder contains only symlinks then that folder should be deleted and 
    * if parent folder contains no files or symlink only then that folder should be deleted too
* tool should be written in python
* please drop tool into scripts folder
