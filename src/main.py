import json
import time

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains

import config
from action_utils import (
    click_button_by_id,
    click_button_by_xpath,
    find_element_by_xpath,
    find_elements_by_xpath,
    get_input_value,
    send_keys_by_name,
    get_text,
)
from driver_utils import chrome_settings_init
from logger import logging
from results_processor import post_process_results
from scrape_utils import (
    scrape_attachments,
    scrape_description,
    scrape_development,
    scrape_discussions,
    scrape_history,
    scrape_related_work,
)


def login(driver, email, password):
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
    work_item_control_xpath = (
        ".//div[contains(@class, 'work-item-control initialized')]"
    )
    work_id_xpath = ".//div[contains(@class, 'work-item-form-id initialized')]//span"
    title_xpath = ".//div[contains(@class, 'work-item-form-title initialized')]//input"
    username_xpath = (
        ".//div[contains(@class, 'work-item-form-assignedTo initialized')]"
        "//span[contains(@class, 'text-cursor')]"
    )
    state_xpath = f"{work_item_control_xpath}//*[@aria-label='State Field']"
    area_xpath = f"{work_item_control_xpath}//*[@aria-label='Area Path']"
    iteration_xpath = f"{work_item_control_xpath}//*[@aria-label='Iteration Path']"
    priority_xpath = f"{work_item_control_xpath}//*[@aria-label='Priority']"
    remaining_xpath = f"{work_item_control_xpath}//*[@aria-label='Remaining Work']"
    activity_xpath = f"{work_item_control_xpath}//*[@aria-label='Activity']"
    blocked_xpath = f"{work_item_control_xpath}//*[@aria-label='Blocked']"
    description = f"{work_item_control_xpath}//*[@aria-label='Description']"

    desc = find_element_by_xpath(dialog_box, description)
    task_id = get_text(dialog_box, work_id_xpath)
    username = get_text(dialog_box, username_xpath)

    work_item_data = {
        "Task id": task_id,
        "Title": get_input_value(dialog_box, title_xpath).replace(" ", "_"),
        "User Name": username,
        "State": get_input_value(dialog_box, state_xpath),
        "Area": get_input_value(dialog_box, area_xpath),
        "Iteration": get_input_value(dialog_box, iteration_xpath),
        "Priority": get_input_value(dialog_box, priority_xpath),
        "Remaining Work": get_input_value(dialog_box, remaining_xpath),
        "Activity": get_input_value(dialog_box, activity_xpath),
        "Blocked": get_input_value(dialog_box, blocked_xpath),
        "related_work": scrape_related_work(driver, dialog_box),
        "discussions": scrape_discussions(driver),
        "attachments": scrape_attachments(driver, dialog_box),
        "description": scrape_description(desc),
    }

    details_xpath = ".//li[@aria-label='Details']"
    history_xpath = ".//li[@aria-label='History']"

    # Navigate to history tab
    click_button_by_xpath(dialog_box, history_xpath)

    work_item_data["history"] = scrape_history(dialog_box)

    # Navigate back to details tab
    click_button_by_xpath(dialog_box, details_xpath)

    work_item_data["development"] = scrape_development(driver)
    child_work_items = find_elements_by_xpath(dialog_box, child_xpath)

    print(work_item_data)

    if child_work_items:
        children = []
        for work_item in child_work_items:
            work_item_element = find_element_by_xpath(work_item, ".//a")

            # Reposition movement to clear space / description
            action.move_to_element(desc).perform()

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
    driver.maximize_window()

    logging.info(f"Navigate and login to {url}")
    # Navigate to the site and login
    driver.get(url)
    login(driver, email, password)
    logging.info(f"Done")

    # Find each work item
    work_items = find_elements_by_xpath(driver, '//div[@aria-level="1"]')
    work_items_count = len(work_items)
    work_items_ctr = 0

    result_set = []
    while work_items_ctr < work_items_count:
        work_items = find_elements_by_xpath(driver, '//div[@aria-level="1"]')
        work_item = work_items[work_items_ctr]

        logging.info(f"Sleeping...")
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
    with open(file_path, "w") as outfile:
        json.dump(result_set, outfile)


def main():
    save_file = "data/scrape_result.json"
    chrome_config, chrome_downloads = chrome_settings_init()

    with webdriver.Chrome(**chrome_config) as wd:
        scraper(
            wd,
            config.BASE_URL + config.BACKLOG_ENDPOINT,
            config.EMAIL,
            config.PASSWORD,
            save_file,
        )

    post_process_results(save_file, chrome_downloads)


if __name__ == "__main__":
    main()
