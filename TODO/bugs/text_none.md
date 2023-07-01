# error

## info
* please find log file in log/2023_07_01
Traceback (most recent call last):
  File "/home/paul/Downloads/test/main.py", line 183, in <module>
    main()
  File "/home/paul/Downloads/test/main.py", line 171, in main
    scraper(
  File "/home/paul/Downloads/test/main.py", line 153, in scraper
    work_item_data = scrape_child_work_items(driver, dialog_box)
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/paul/Downloads/test/main.py", line 73, in scrape_child_work_items
    "related_work": scrape_related_work(driver, dialog_box),
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/paul/Downloads/test/scrape_utils.py", line 195, in scrape_related_work
    related_work_type = related_work_type.text
                        ^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'NoneType' object has no attribute 'text'

