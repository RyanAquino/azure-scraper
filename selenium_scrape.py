from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
import time
import config
import json


def click_button_by_id(driver, id):
    element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, id)))
    element.click()


def click_button_by_xpath(driver, xpath):
    element = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, xpath))
    )
    element.click()


def click_button_by_tag(driver, tag):
    element = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.TAG_NAME, tag))
    )
    element.click()


def send_keys_by_name(driver, name, keys):
    element = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.NAME, name))
    )
    element.send_keys(keys)


def find_elements_by_xpath(driver, xpath):
    try:
        e = WebDriverWait(driver, 10).until(
            EC.visibility_of_all_elements_located((By.XPATH, xpath))
        )
    except Exception as e:
        return None

    return e


def find_element_by_xpath(driver, xpath):
    try:
        e = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
    except Exception as e:
        return None

    return e


def login(driver, email, password):
    send_keys_by_name(driver, "loginfmt", email)
    click_button_by_id(driver, "idSIButton9")
    send_keys_by_name(driver, "passwd", password)
    click_button_by_id(driver, "idSIButton9")
    click_button_by_id(driver, "idSIButton9")


def scrape_child_work_items(driver, dialog_box):
    child_xpath = (
        ".//div[child::div[contains(@class, 'la-group-title') "
        "and contains(text(), 'Child')]]//div[@class='la-item']"
    )
    work_id_xpath = ".//div[contains(@class, 'work-item-form-id initialized')]//span"
    title_xpath = ".//div[contains(@class, 'work-item-form-title initialized')]//input"

    work_item_data = {
        "ID": find_element_by_xpath(dialog_box, work_id_xpath).text,
        "title": find_element_by_xpath(dialog_box, title_xpath).get_attribute("value"),
    }

    child_work_items = find_elements_by_xpath(dialog_box, child_xpath)

    if child_work_items:
        children = []
        for work_item in child_work_items:
            work_item_element = find_element_by_xpath(work_item, ".//a")
            child_id = work_item_element.get_attribute("href").split("/")[-1]

            work_item_element.click()
            time.sleep(5)

            dialog_xpath = (
                f"//span[@aria-label='ID Field' and "
                f"contains(text(), '{child_id}')]//ancestor::div"
            )

            child_dialog_box = find_element_by_xpath(driver, dialog_xpath)
            child_data = scrape_child_work_items(driver, child_dialog_box)
            children.append(child_data)

            click_button_by_xpath(
                child_dialog_box, ".//button[contains(@class, 'ui-button')]"
            )
        work_item_data["children"] = children
    return work_item_data


def scraper(driver, url, email, password, file_path):
    # Navigate to the site and login
    driver.get(url)
    login(driver, email, password)

    # Find each work item
    work_items = find_elements_by_xpath(driver, '//div[@aria-level="1"]')

    result_set = []
    for work_item in work_items:
        time.sleep(5)

        work_item_element = find_element_by_xpath(work_item, ".//a")

        # Click
        work_item_element.click()
        dialog_xpath = "//div[contains(@tabindex, '-1') and contains(@role, 'dialog')]"
        dialog_box = find_element_by_xpath(work_item, dialog_xpath)

        # Scrape Child Items
        work_item_data = scrape_child_work_items(driver, dialog_box)
        result_set.append(work_item_data)

        # Close dialog box
        click_button_by_xpath(dialog_box, ".//button[contains(@class, 'ui-button')]")

    with open(file_path, "w") as outfile:
        json.dump(result_set, outfile)


if __name__ == "__main__":
    chrome_options = ChromeOptions()
    # chrome_options.add_argument("--headless=new")
    # chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option("detach", True)
    save_file = "Azure Directories/scrape_result.json"

    with webdriver.Chrome(options=chrome_options) as wd:
        scraper(wd, config.URL, config.EMAIL, config.PASSWORD, save_file)
