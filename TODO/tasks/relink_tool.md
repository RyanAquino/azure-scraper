# change symlink path tool

## todo
* tool should replace each symlink within current folder recursively
* link should be selected by prefix path and replace path part matching selector by new specified one
    * example selector: /home/paul/Downloads/test/ replace with: /media/somepath/
    * symlink 
        * before: /home/paul/Downloads/test/src/somefile.md
        * after: /media/somepath/src/somefile.md
* tool should be written in python
* please drop tool into scripts folder

## info
* as far as I know symlink cannot be altered, most likely new has to be created and old deleted
