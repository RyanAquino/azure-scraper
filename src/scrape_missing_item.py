import json
import shutil

from src.driver_utils import chrome_settings_init
from src.main import (
    scrape_child_work_items,
    retrieve_result_set,
    login,
    get_work_item_ids,
    save_json_file,
)

from selenium import webdriver
import config
from src.results_processor import (
    create_directory_hierarchy,
    create_related_work_contents,
)


def main(url):
    save_file = "data/scrape_result.json"
    default_result_set = retrieve_result_set(save_file)
    chrome_config, chrome_downloads = chrome_settings_init()

    result_set = default_result_set if default_result_set else []
    result_ids = []
    get_work_item_ids(result_set, result_ids)

    with webdriver.Chrome(**chrome_config) as driver:
        login(driver, url, config.EMAIL, config.PASSWORD)
        work_item_data = scrape_child_work_items(driver)

    if work_item_data.get("Task id") not in result_ids:
        result_set.append(work_item_data)
        save_json_file(save_file, result_set)

        with open(save_file, "r", encoding="utf-8") as file:
            scrape_result = json.load(file)
            create_directory_hierarchy(scrape_result)
            create_related_work_contents(scrape_result)

            # Clean downloads directory after post process
            if chrome_downloads.exists() and chrome_downloads.is_dir():
                shutil.rmtree(chrome_downloads)


if __name__ == "__main__":
    url = input("URL: ")
    main(url)
