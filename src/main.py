import json
import time
import traceback
from pathlib import Path
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

import config
from action_utils import (
    click_button_by_id,
    click_button_by_xpath,
    find_element_by_xpath,
    find_elements_by_xpath,
    get_input_value,
    send_keys_by_name,
    show_more,
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
    # Navigate to the site and login
    try:
        if config.ON_PREM:
            scheme, domain, path = urlparse(url)[0:3]
            driver.get(f"{scheme}://{email}:{password}@{domain}{path}")
            driver.get(url)
            return

        driver.get(url)
        send_keys_by_name(driver, "loginfmt", email)
        click_button_by_id(driver, "idSIButton9")
        send_keys_by_name(driver, "passwd", password)
        click_button_by_id(driver, "idSIButton9")
        click_button_by_id(driver, "idSIButton9")
    except TimeoutException:
        driver.get(url)
        send_keys_by_name(driver, "loginfmt", email)
        click_button_by_id(driver, "idSIButton9")
    except StaleElementReferenceException:
        login(driver, url, email, password)


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

    try:
        work_item_data, desc_att = scrape_basic_fields(dialog_box, driver)
        work_item_data["img_description"] = desc_att
        work_item_data["Title"] = title
        work_item_data["discussions"] = scrape_discussions(driver)
        work_item_data["related_work"] = scrape_related_work(driver, dialog_box)
        work_item_data["development"] = scrape_development(driver)
        work_item_data["history"] = scrape_history(driver)
        work_item_data["attachments"] = scrape_attachments(driver)
    except Exception:
        raise

    for key, value in work_item_data.items():
        print(key, ":", value)

    child_container = "//div[@class='la-group-title' and contains(text(), 'Child')]"
    child_xpath = f".{child_container}/following-sibling::div"
    show_more(
        dialog_box, "//div[@class='la-group-title']/../..//div[@class='la-show-more']"
    )
    child_work_items = find_elements_by_xpath(dialog_box, child_xpath)

    if child_work_items:
        children = []
        for work_item in child_work_items:
            click_button_by_xpath(work_item, ".//a", web_driver=driver)

            actions = ActionChains(driver)
            actions.move_by_offset(0, 0)
            actions.perform()

            child_data = scrape_child_work_items(driver)
            children.append(child_data)

        work_item_data["children"] = children

    click_button_by_xpath(dialog_box, close_xpath)

    return work_item_data


def get_work_item_ids(work_items, work_item_ids):
    for item in work_items:
        if child := item.get("children"):
            get_work_item_ids(child, work_item_ids)

        work_item_ids.append(item.get("Task id"))


def scraper(
    driver,
    url,
    email,
    password,
    file_path,
    default_result_set=None,
    default_start_index=0,
):
    logging.info(f"Navigate and login to {url}")
    login(driver, url, email, password)
    logging.info("Done")

    # Find each work item
    work_item_selector = (
        '//div[@class="grid-canvas ui-draggable"]//div[@aria-level="2"]'
        if config.UNPARENTED
        else '//div[@aria-level="1"]'
    )

    if config.UNPARENTED:
        element = find_element_by_xpath(
            driver, "//span[text()='Unparented']//following-sibling::div"
        )
        element.click()

    work_items = find_elements_by_xpath(driver, work_item_selector)
    board_view = find_element_by_xpath(driver, "//div[@class='grid-canvas ui-draggable']")
    work_items_count = len(work_items)
    work_items_ctr = default_start_index

    result_set = default_result_set if default_result_set else []
    result_ids = []
    get_work_item_ids(result_set, result_ids)
    item_height_size = work_items[0].size.get("height", 0) if work_items else 0

    while work_items_ctr < work_items_count:
        work_items = find_elements_by_xpath(driver, work_item_selector)

        # Add new work items after scroll
        # for item in work_items_temp:
        #     if item not in work_items:
        #         work_items.append(item)
        #         work_items_count += 1

        work_item = work_items[work_items_ctr]

        logging.info("Sleeping...")
        time.sleep(5)

        # Open Dialog Box
        click_button_by_xpath(work_item, ".//a")

        # Scrape Child Items
        try:
            work_item_data = scrape_child_work_items(driver)
        except Exception as e:
            traceback.print_exception(e)
            err_msg = str(e)
            work_item_id = (
                result_ids[work_items_ctr] if work_items_ctr in result_ids else None
            )
            logging.error(err_msg)
            logging.error(work_items_ctr)
            logging.error(work_item_id)
            print(f"Exception: {err_msg}")
            print(f"Work item ID: {work_item_id}")
            save_json_file(file_path, result_set)

            return work_items_ctr

        if work_item_data.get("Task id") not in result_ids:
            result_set.append(work_item_data)

        work_items_ctr += 1

        # Adjust for next work item
        # item_height_size += item_height_size
        # driver.execute_script(f"arguments[0].scrollTo(0, {item_height_size});", board_view)

    logging.info(f"Saving result to {file_path}")
    save_json_file(file_path, result_set)


def save_json_file(file_path, result_set):
    with open(file_path, "w", encoding="utf-8") as outfile:
        json.dump(result_set, outfile)


def retrieve_result_set(save_file):
    default_result_set = {}

    if Path(save_file).exists():
        try:
            with open(save_file, "r") as json_file:
                default_result_set = json.load(json_file)
        except json.decoder.JSONDecodeError:
            pass

    return default_result_set


def main(default_start_index):
    save_file = "data/scrape_result.json"
    default_result_set = retrieve_result_set(save_file)
    chrome_config, chrome_downloads = chrome_settings_init()

    with webdriver.Chrome(**chrome_config) as driver:
        last_error_ctr = scraper(
            driver,
            config.BASE_URL,
            config.EMAIL,
            config.PASSWORD,
            save_file,
            default_result_set,
            default_start_index,
        )

    if last_error_ctr or last_error_ctr == 0:
        err_msg = f"Error encountered. Please reprocess on index: {last_error_ctr}"
        logging.error(err_msg)
        print(err_msg)
    else:
        post_process_results(save_file, chrome_downloads)


if __name__ == "__main__":
    start_index = input("Start work item index: ")
    main(int(start_index))
