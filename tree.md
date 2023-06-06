# Folder tree and data structure

## Folder

* Epic name convention for all sub folder `(<id>_<title>)`
    > Replace white spaces with underscore " " to "_"
  > for each file and folder whenever tile contains white space.
  * Feature
      * Backlog
          * Task

## Data

* Work item: Epic/Feature/Backlog/Task `(<id>_<title>)`
    * metadata.md:
        * Task id: 2222
        * User name:
        * Title:
        * State:
        * Area:
        * Iteration:
        * Priority:
        * Remaining Work:
        * Activity:
        * Blocked:
    * description.md:
    * discussion (folder):
        * attachments (folder): (store any graphical content from discussion record here)
            * <yyyy_mm_dd>_<username>_<id>.<relevant file extension> 
        * <yyyy_mm_dd>_<username>.md:
            * Title: <Joe commented Jan 11, 2016>
            * Content:
    * definition_of_done.md (Definition of Done please ignore this filed):
    * development (folder): (each change set as file )
        * changeset_<ID>.md
            * File name:
            * Path:
            * Content:
    * related (folder)
       * `<id>_<title>_update_<yyyy_MM_ddThh_mm_ss>.md` (linked as symlink):
           * Type:
               * Link to item file:
               * Last update:
    * history (folder)
       * <yyyy_mm_dd>_<username>_<title>.md:
           * User
           * Title:
           * Content:
           * Links:
               * Type:
               * Link to item file:
               * Title:
    * attachments (store attached files in this folder):
    * origin.md (Origin URL link to work item)

