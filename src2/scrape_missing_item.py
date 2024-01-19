import json
import shutil

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException

import config
from src2.action_utils import find_elements_by_xpath
from src2.driver_utils import chrome_settings_init
from src2.main import (
    get_work_item_ids,
    login,
    retrieve_result_set,
    save_json_file,
    scrape_child_work_items,
)
from src2.results_processor import (
    create_directory_hierarchy,
    create_related_work_contents,
)


def run_single(default_result_set, save_file, driver):
    work_item_data = scrape_child_work_items(driver)
    default_result_set.append(work_item_data)
    save_json_file(save_file, default_result_set)

    with open(save_file, "r", encoding="utf-8") as file:
        scrape_result = json.load(file)
        create_directory_hierarchy(scrape_result)
        create_related_work_contents(scrape_result)

        # Clean downloads directory after post process
        if chrome_downloads.exists() and chrome_downloads.is_dir():
            shutil.rmtree(chrome_downloads)


def main(driver, result_ids, result_set):
    work_items = find_elements_by_xpath(driver, "//a[@class='work-item-title-link']")

    for work_item in work_items:
        try:
            work_item_id = work_item.get_attribute("href").split("/")[-1]
        except StaleElementReferenceException:
            print("Retrying due to stale elements")
            return main(driver, result_ids, result_set)

        if work_item_id not in result_ids:
            work_item.click()
            run_single(result_set, save_file_location, driver)


if __name__ == "__main__":
    save_file_location = "data/scrape_result.json"
    init_result_set = retrieve_result_set(save_file_location)
    chrome_config, chrome_downloads = chrome_settings_init()

    init_result_ids = []
    get_work_item_ids(init_result_set, init_result_ids)

    with webdriver.Chrome(**chrome_config) as init_driver:
        login(init_driver, config.BASE_URL, config.EMAIL, config.PASSWORD)
        main(init_driver, init_result_ids, init_result_set)
