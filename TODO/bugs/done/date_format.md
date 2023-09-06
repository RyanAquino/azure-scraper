# non generic time format error (probably hard coded)

## console log

Retrying hover on work related date ... 1/100
Traceback (most recent call last):
  File "/home/paul/Downloads/xxx/main.py", line 183, in <module>
    main()
  File "/home/paul/Downloads/xxx/main.py", line 171, in main
    scraper(
  File "/home/paul/Downloads/xxx/main.py", line 153, in scraper
    work_item_data = scrape_child_work_items(driver, dialog_box)
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/paul/Downloads/xxx/main.py", line 107, in scrape_child_work_items
    child_data = scrape_child_work_items(driver, child_dialog_box)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/paul/Downloads/xxx/main.py", line 73, in scrape_child_work_items
    "related_work": scrape_related_work(driver, dialog_box),
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/paul/Downloads/xxx/scrape_utils.py", line 244, in scrape_related_work
    "link_target": f"{related_work_item_id}_{related_work_title}_update_{convert_date(updated_at)}_{related_work_type}",
                                                                         ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/paul/Downloads/xxx/action_utils.py", line 95, in convert_date
    date_obj = datetime.strptime(date_string, date_format)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/paul/miniconda3/envs/tfs/lib/python3.11/_strptime.py", line 568, in _strptime_datetime
    tt, fraction, gmtoff_fraction = _strptime(data_string, format)
                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/paul/miniconda3/envs/tfs/lib/python3.11/_strptime.py", line 349, in _strptime
    raise ValueError("time data %r does not match format %r" %
ValueError: time data 'New' does not match format '%d %B %Y %H:%M:%S'

## scrape.log
2023-07-02 11:18:43,768 INFO Open dialog box for 'xxx'

