# related work item

## current
* links are stored in one file in form of absolute path

## should
* related work item should be stored in folder "related" for each work item separately as symlink (symbolic link)
```bash
# linux command sample for symlink creation
ln -s source_file symbolic_link
```
* for each symlik file there should be associated with the same name but .md extension file with metadata
* please find details about folder structure and naming convention in the tree.md file
* there are cross project linked related items, in that case create symlink 
    however there is no need to validate it since there is no access to another project
