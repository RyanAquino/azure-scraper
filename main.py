import json
import time
from urllib.parse import urlparse

from selenium import webdriver

import config
from action_utils import (
    click_button_by_id,
    click_button_by_xpath,
    find_element_by_xpath,
    find_elements_by_xpath,
    get_input_value,
    send_keys_by_name,
)
from driver_utils import chrome_settings_init
from logger import logging
from results_processor import post_process_results
from scrape_utils import (
    scrape_attachments,
    scrape_basic_fields,
    scrape_development,
    scrape_discussions,
    scrape_history,
    scrape_related_work,
)


def login(driver, url, email, password):
    scheme, domain, path = urlparse(url)[0:3]
    # Navigate to the site and login
    if domain != "dev.azure.com":
        driver.get(f"{scheme}://{email}:{password}@{domain}{path}")
        driver.get(url)
        return

    driver.get(url)
    send_keys_by_name(driver, "loginfmt", email)
    click_button_by_id(driver, "idSIButton9")
    send_keys_by_name(driver, "passwd", password)
    click_button_by_id(driver, "idSIButton9")
    click_button_by_id(driver, "idSIButton9")


def scrape_child_work_items(driver):
    dialog_xpath = "//div[@role='dialog'][last()]"
    title_xpath = f"{dialog_xpath}//input[@aria-label='Title Field']"
    close_xpath = ".//button[contains(@class, 'ui-button')]"

    retry = 0
    title = None
    dialog_box = None

    while retry < config.MAX_RETRIES:
        title = get_input_value(driver, title_xpath)

        if title:
            print("Open dialog box for ", title)
            dialog_box = find_element_by_xpath(driver, dialog_xpath)
            break

        if retry == config.MAX_RETRIES:
            print("Error: Unable to find dialog box!!")
            return
        retry += 1
        print(f"Retrying finding of dialog box ... {retry}/{config.MAX_RETRIES}")

    work_item_data = scrape_basic_fields(dialog_box)
    work_item_data["Title"] = title.replace(" ", "_")
    work_item_data["discussions"] = scrape_discussions(driver)
    work_item_data["related_work"] = scrape_related_work(driver, dialog_box)
    work_item_data["development"] = scrape_development(driver)
    work_item_data["history"] = scrape_history(driver)
    work_item_data["attachments"] = scrape_attachments(driver)

    for key, value in work_item_data.items():
        print(key, ":", value)

    child_container = "//div[@class='la-group-title' and contains(text(), 'Child')]"
    child_xpath = f".{child_container}/following-sibling::div"
    child_work_items = find_elements_by_xpath(dialog_box, child_xpath)

    if child_work_items:
        children = []
        for work_item in child_work_items:
            click_button_by_xpath(work_item, ".//a")

            child_data = scrape_child_work_items(driver)
            children.append(child_data)

        work_item_data["children"] = children

    click_button_by_xpath(dialog_box, close_xpath)

    return work_item_data


def scraper(driver, url, email, password, file_path):
    logging.info(f"Navigate and login to {url}")
    login(driver, url, email, password)
    logging.info("Done")

    # Find each work item
    work_items = find_elements_by_xpath(driver, '//div[@aria-level="1"]')
    work_items_count = len(work_items)
    work_items_ctr = 0

    result_set = []
    while work_items_ctr < work_items_count:
        work_items = find_elements_by_xpath(driver, '//div[@aria-level="1"]')
        work_item = work_items[work_items_ctr]

        logging.info("Sleeping...")
        time.sleep(5)

        # Open Dialog Box
        click_button_by_xpath(work_item, ".//a")

        # Scrape Child Items
        work_item_data = scrape_child_work_items(driver)
        result_set.append(work_item_data)

        work_items_ctr += 1

    logging.info(f"Saving result to {file_path}")
    with open(file_path, "w", encoding="utf-8") as outfile:
        json.dump(result_set, outfile)


def main():
    save_file = "data/scrape_result.json"
    chrome_config, chrome_downloads = chrome_settings_init()

    with webdriver.Chrome(**chrome_config) as driver:
        scraper(
            driver,
            config.BASE_URL,
            config.EMAIL,
            config.PASSWORD,
            save_file,
        )

    post_process_results(save_file, chrome_downloads)


if __name__ == "__main__":
    main()
