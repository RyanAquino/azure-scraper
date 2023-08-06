import json
import time

from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains

import config
from action_utils import (
    click_button_by_id,
    click_button_by_xpath,
    find_element_by_xpath,
    find_elements_by_xpath,
    send_keys_by_name,
)
from driver_utils import chrome_settings_init
from logger import logging
from results_processor import post_process_results
from scrape_utils import (
    scrape_basic_fields,
    scrape_attachments,
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


def scrape_child_work_items(driver, dialog_box):
    action = ActionChains(driver)
    child_xpath = (
        ".//div[child::div[contains(@class, 'la-group-title') "
        "and contains(text(), 'Child')]]//div[@class='la-item']"
    )
    container = ".//div[contains(@class, 'work-item-control initialized')]"
    description_xpath = f"{container}//*[@aria-label='Description']"
    description = find_element_by_xpath(dialog_box, description_xpath)

    work_item_data = scrape_basic_fields(dialog_box)
    work_item_data["related_work"] = scrape_related_work(driver, dialog_box)
    work_item_data["discussions"] = scrape_discussions(driver)
    work_item_data["attachments"] = scrape_attachments(driver, dialog_box)
    work_item_data["history"] = scrape_history(dialog_box)
    work_item_data["development"] = scrape_development(driver)

    child_work_items = find_elements_by_xpath(dialog_box, child_xpath)

    print(work_item_data)

    if child_work_items:
        children = []
        for work_item in child_work_items:
            work_item_element = find_element_by_xpath(work_item, ".//a")

            # Reposition movement to clear space / description
            action.move_to_element(description).perform()

            logging.info(f"Open dialog box for '{work_item_element.text}'")
            work_item_element.click()
            dialog_xpath = "//div[@role='dialog'][last()]"
            child_dialog_box = find_element_by_xpath(driver, dialog_xpath)
            child_data = scrape_child_work_items(driver, child_dialog_box)
            children.append(child_data)

            logging.info(f"Close dialog box for '{work_item_element.text}'")
            click_button_by_xpath(
                child_dialog_box, ".//button[contains(@class, 'ui-button')]"
            )
        work_item_data["children"] = children

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

        work_item_element = find_element_by_xpath(work_item, ".//a")
        work_item_element_text = work_item_element.text

        # logging.info(f"Open dialog box for '{work_item_element_text}'")
        print(f"Open dialog box for '{work_item_element_text}'")
        # Click
        work_item_element.click()

        dialog_xpath = "(//div[@role='dialog'])[last()]"
        dialog_box = find_element_by_xpath(work_item, dialog_xpath)

        # Scrape Child Items
        work_item_data = scrape_child_work_items(driver, dialog_box)
        result_set.append(work_item_data)

        logging.info(f"Close dialog box for '{work_item_element_text}'")
        # Close dialog box
        click_button_by_xpath(dialog_box, ".//button[contains(@class, 'ui-button')]")
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
