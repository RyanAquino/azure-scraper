import json
import shutil
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains

import config
from action_utils import (
    click_button_by_xpath,
    find_element_by_xpath,
    find_elements_by_xpath,
    get_input_value,
    show_more,
)
from driver_utils import chrome_settings_init
from logger import logging
from main import get_work_item_ids, login, retrieve_result_set, save_json_file
from main import scrape_child_work_items as main_scrape_child_work_items
from results_processor import create_directory_hierarchy, create_related_work_contents


def scrape_basic_fields(dialog_box):
    basic_fields = {}

    try:
        html = dialog_box.get_attribute("innerHTML")
        soup = BeautifulSoup(html, "html.parser")

        for element in soup.find_all(attrs={"aria-label": True}):
            attribute = element.get("aria-label")

            if attribute == "ID Field":
                value = element.text if element.text else None
                basic_fields[attribute] = value
                return {"Task id": basic_fields.get("ID Field")}
    except AttributeError:
        return scrape_basic_fields(dialog_box)


def scrape_child_work_items(driver, result_ids, temp=False):
    dialog_xpath = "//div[@role='dialog'][last()]"
    title_xpath = f"{dialog_xpath}//input[@aria-label='Title Field']"
    close_xpath = ".//button[contains(@class, 'ui-button')]"

    retry = 0
    dialog_box = None

    while retry < config.MAX_RETRIES:
        title = get_input_value(driver, title_xpath)

        time.sleep(2)

        if title:
            print("Open dialog box for ", title)
            dialog_box = find_element_by_xpath(driver, dialog_xpath)

        if dialog_box:
            break

        if retry == config.MAX_RETRIES:
            print("Error: Unable to find dialog box!!")
            return
        retry += 1
        print(f"Retrying finding of dialog box ... {retry}/{config.MAX_RETRIES}")

    work_item_id = scrape_basic_fields(dialog_box)

    child_container = f"({dialog_xpath}//div[@class='la-group-title' and contains(text(), 'Child')])[1]"
    show_more(
        dialog_box,
        f"{child_container}/../following-sibling::div//div[@class='la-show-more']",
    )
    child_work_items = find_elements_by_xpath(
        dialog_box, f"{child_container}/following-sibling::div"
    )

    if child_work_items:
        logging.info(f"Child work items for {work_item_id.get('Task id')}")
        children = []
        for work_item in child_work_items:
            click_button_by_xpath(work_item, ".//a", web_driver=driver)

            actions = ActionChains(driver)
            actions.move_by_offset(0, 0)
            actions.perform()

            child_data, temp = scrape_child_work_items(driver, result_ids, temp)
            # check child data
            if child_data.get("Task id") not in result_ids:
                # click_button_by_xpath(dialog_box, close_xpath)
                temp = True
            children.append(child_data)

        work_item_id["children"] = children

    click_button_by_xpath(dialog_box, close_xpath)

    return work_item_id, temp


def missed_scraper(
    driver,
    url,
    email,
    password,
    default_result_set=None,
):
    logging.info(f"Navigate and login to {url}")
    login(driver, url, email, password)
    logging.info("Done")

    work_item_selector = '//div[@aria-level="1"]'
    work_items = find_elements_by_xpath(driver, work_item_selector)
    work_items_count = len(work_items)
    work_items_ctr = 0

    result_set = default_result_set if default_result_set else []
    result_ids = []
    get_work_item_ids(result_set, result_ids)
    missed_items = []

    while work_items_ctr < work_items_count:
        work_items = find_elements_by_xpath(driver, work_item_selector)
        work_item = work_items[work_items_ctr]

        logging.info("Sleeping...")
        time.sleep(5)

        # Open Dialog Box
        click_button_by_xpath(work_item, ".//a")

        # Scrape Child Items
        work_item_data, is_skip = scrape_child_work_items(driver, result_ids)
        parent_work_item_id = work_item_data.get("Task id")

        if is_skip:
            logging.info(f"Skipped ID: {parent_work_item_id}")
            missed_items.append({"id": parent_work_item_id, "ctr": work_items_ctr})

        work_items_ctr += 1

    return missed_items


def run_single(default_result_set, save_file, driver):
    with open(save_file, "r", encoding="utf-8") as file:
        scrape_result = json.load(file)

        work_item_data = main_scrape_child_work_items(driver)
        default_result_set = list(
            filter(
                lambda x: x.get("Task id") != work_item_data.get("Task id"),
                default_result_set,
            )
        )
        default_result_set.append(work_item_data)
        save_json_file(save_file, default_result_set)

        create_directory_hierarchy(scrape_result)
        create_related_work_contents(scrape_result)

        # Clean downloads directory after post process
        if chrome_downloads.exists() and chrome_downloads.is_dir():
            shutil.rmtree(chrome_downloads)

        return json.load(file)


if __name__ == "__main__":
    save_file_location = "data/scrape_result.json"
    init_result_set = retrieve_result_set(save_file_location)
    chrome_config, chrome_downloads = chrome_settings_init()

    with webdriver.Chrome(**chrome_config) as init_driver:
        missed_items = missed_scraper(
            init_driver, config.BASE_URL, config.EMAIL, config.PASSWORD, init_result_set
        )
        logging.info(f"Missed items: {missed_items}")
        # missed_items = [{"id": "1", "ctr": 0}, {"id": "50", "ctr": 8}]
        # login(init_driver, config.BASE_URL, config.EMAIL, config.PASSWORD)

        for item in missed_items:
            work_item_ctr = item.get("ctr")
            work_item_id = item.get("id")
            work_items = find_elements_by_xpath(
                init_driver, "//a[@class='work-item-title-link']"
            )
            work_item = work_items[work_item_ctr]
            work_item.click()
            init_result_set = run_single(init_result_set, save_file_location, init_driver)
