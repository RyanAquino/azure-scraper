from pathlib import Path

from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
import time
import config
import json
import logging
import os
import platform
import urllib.parse
from uuid import uuid4

logging.basicConfig(
    level=logging.INFO,
    filename="scrape.log",
    filemode="w",
    format="%(asctime)s %(levelname)s %(message)s",
)


def get_driver_by_os():
    ps = platform.system()

    if ps == "Windows":
        driver_path = "chromedriver.exe"
    elif ps == "Darwin":
        driver_path = "chromedriver_mac"

        if platform.processor() == "arm":
            driver_path = "chromedriver_mac_arm"
    else:
        driver_path = "chromedriver_linux"

    logging.info(f"Using driver {driver_path}.")

    return Service(executable_path=f"drivers/{driver_path}")


def click_button_by_id(driver, element_id):
    element = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, element_id))
    )
    element.click()


def click_button_by_xpath(driver, xpath):
    element = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, xpath))
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


def get_input_value(driver, xpath):
    if element := find_element_by_xpath(driver, xpath):
        return element.get_attribute("value")


def get_text(driver, xpath):
    if element := find_element_by_xpath(driver, xpath):
        return element.text


def scrape_attachments(driver, dialog_box):

    # Attachment count
    attachment_count_xpath = "(.//span[contains(@class, 'attachment-count')])[last()]"
    attachment_count = find_element_by_xpath(dialog_box, attachment_count_xpath)

    if not attachment_count or not attachment_count.text.strip():
        return None

    # Navigate to attachments page
    attachment_xpath = "//li[@aria-label='Attachments']"
    attachment_button = find_elements_by_xpath(dialog_box, attachment_xpath)
    attachment_button[-1].click()

    # Retrieve attachment links
    attachment_count = attachment_count.text
    attachment_count = "".join([char for char in attachment_count.strip() if char.isdigit()])
    a_href_xpath = ".//div[contains(@class, 'attachments-grid-file-name')]//a"
    attachments = find_elements_by_xpath(dialog_box, a_href_xpath)

    for attachment in attachments[-int(attachment_count):]:
        attachment_url = attachment.get_attribute("href")
        parsed_url = urllib.parse.urlparse(attachment_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        query_params['fileName'] = [f"{uuid4()}_{query_params.get('fileName')[0]}"]
        updated_url = urllib.parse.urlunparse(parsed_url._replace(query=urllib.parse.urlencode(query_params, doseq=True)))
        driver.get(updated_url)

    # Navigate back to details
    details_tab_xpath = "//li[@aria-label='Details']"
    details_tab_button = find_elements_by_xpath(dialog_box, details_tab_xpath)
    details_tab_button[-1].click()


def scrape_related_work(action, dialog_box):
    related_work_xpath = (
        "(.//div[@class='links-control-container']/div[@class='la-main-component'])[last()]/div[@class='la-list']/div"
    )
    related_work_items = find_elements_by_xpath(dialog_box, related_work_xpath)
    results = []

    for related_work_item in related_work_items:
        related_work_type_xpath = "div[@class='la-group-title']"
        related_work_type = find_element_by_xpath(related_work_item, related_work_type_xpath)

        related_work_type = related_work_type.text
        related_work_type = related_work_type.split(" ")[0]
        result = {"type": related_work_type, "related_work_items": []}

        related_works_xpath = "div[@class='la-item']"
        related_works = find_elements_by_xpath(related_work_item, related_works_xpath)

        updated_at_hover_xpath = "div/div/div[@class='la-additional-data']/div[1]/div/span"

        for related_work in related_works:
            related_work_link = find_element_by_xpath(related_work, "div/div/div//a")

            updated_at_hover = find_element_by_xpath(related_work, updated_at_hover_xpath)
            action.move_to_element(updated_at_hover).perform()

            updated_at = find_element_by_xpath(related_work, "//p[contains(@class, 'subText-74')]").text
            updated_at = " ".join(updated_at.split(" ")[-5:])

            related_work_url = related_work_link.get_attribute("href").split("/")[-1]
            related_work_title = related_work_link.text
            result["related_work_items"].append({
                "link": f"{related_work_url}_{related_work_title}",
                "updated_at": updated_at
            })

        results.append(result)

    return results


def scrape_child_work_items(driver, dialog_box):
    action = ActionChains(driver)
    child_xpath = (
        ".//div[child::div[contains(@class, 'la-group-title') "
        "and contains(text(), 'Child')]]//div[@class='la-item']"
    )
    work_item_control_xpath = (
        ".//div[contains(@class, 'work-item-control initialized')]"
    )
    work_id_xpath = f".//div[contains(@class, 'work-item-form-id initialized')]//span"
    title_xpath = f".//div[contains(@class, 'work-item-form-title initialized')]//input"
    username_xpath = (
        ".//div[contains(@class, 'work-item-form-assignedTo initialized')]//span[contains(@class, 'text-cursor')]"
    )
    state_xpath = f"{work_item_control_xpath}//*[@aria-label='State Field']"
    area_xpath = f"{work_item_control_xpath}//*[@aria-label='Area Path']"
    iteration_xpath = f"{work_item_control_xpath}//*[@aria-label='Iteration Path']"
    priority_xpath = f"{work_item_control_xpath}//*[@aria-label='Priority']"
    remaining_xpath = f"{work_item_control_xpath}//*[@aria-label='Remaining Work']"
    activity_xpath = f"{work_item_control_xpath}//*[@aria-label='Activity']"
    blocked_xpath = f"{work_item_control_xpath}//*[@aria-label='Blocked']"
    description = f"{work_item_control_xpath}//*[@aria-label='Description']"

    discussions_xpath = (
        ".//div[contains(@class, 'initialized work-item-discussion-control')]"
        "//div[contains(@class, 'wit-comment-item')]"
    )

    desc = find_element_by_xpath(dialog_box, description)

    work_item_data = {
        "Task id": find_element_by_xpath(dialog_box, work_id_xpath).text,
        "Title": get_input_value(dialog_box, title_xpath),
        "User Name": find_element_by_xpath(dialog_box, username_xpath).text,
        "State": get_input_value(dialog_box, state_xpath),
        "Area": get_input_value(dialog_box, area_xpath),
        "Iteration": get_input_value(dialog_box, iteration_xpath),
        "Priority": get_input_value(dialog_box, priority_xpath),
        "Remaining Work": get_input_value(dialog_box, remaining_xpath),
        "Activity": get_input_value(dialog_box, activity_xpath),
        "Blocked": get_input_value(dialog_box, blocked_xpath),
        "description": desc.text,
        "related_work": scrape_related_work(action, dialog_box)
    }
    scrape_attachments(driver, dialog_box)
    discussions = find_elements_by_xpath(dialog_box, discussions_xpath)

    if discussions:
        work_item_data["discussions"] = []

        for discussion in discussions:
            content = get_text(discussion, "//p")

            if content:
                work_item_data["discussions"].append(
                    {
                        "Title": get_text(
                            discussion, "//span[@class='user-display-name']"
                        ),
                        "Content": content,
                    }
                )

    details_xpath = ".//li[@aria-label='Details']"
    history_xpath = ".//li[@aria-label='History']"
    links_xpath = ".//li[@aria-label='Links']"
    attachments_xpath = ".//li[@aria-label='Attachments']"

    # Navigate to history tab
    click_button_by_xpath(dialog_box, history_xpath)

    # Check if there are collapsed history items
    collapsed_xpath = ".//div[@aria-expanded='false']"
    collapsed = find_elements_by_xpath(dialog_box, collapsed_xpath)

    if collapsed:
        for collapse_item in collapsed:
            collapse_item.click()

    history_item_xpath = ".//div[@class='history-item-summary']"
    history_items = find_elements_by_xpath(dialog_box, history_item_xpath)

    for history in history_items:
        summary_text_xpath = "//span[contains(@class,'history-item-summary-text')]"
        print(get_text(history, summary_text_xpath))

        history.click()

        # history_item_detail_xpath = ".//div[@class='history-item-detail']"
        # history_item_detail = find_elements_by_xpath(dialog_box, history_item_detail_xpath)
        #
        # field_name = ".//div[@class='field-name']//span"
        # fields = find_elements_by_xpath(history_item_detail, field_name)
        #
        # for field in fields:
        #     print(field.text)

    click_button_by_xpath(dialog_box, details_xpath)

    child_work_items = find_elements_by_xpath(dialog_box, child_xpath)

    if child_work_items:
        children = []
        for work_item in child_work_items:
            work_item_element = find_element_by_xpath(work_item, ".//a")
            child_id = work_item_element.get_attribute("href").split("/")[-1]

            # Reposition movement to clear space / description
            action.move_to_element(desc).perform()

            logging.info(f"Open dialog box for '{work_item_element.text}'")
            work_item_element.click()
            time.sleep(5)

            dialog_xpath = (
                f"//span[@aria-label='ID Field' and "
                f"contains(text(), '{child_id}')]//ancestor::div"
            )

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

        logging.info(f"Open dialog box for '{work_item_element_text}'")
        # Click
        work_item_element.click()
        dialog_xpath = "//div[contains(@tabindex, '-1') and contains(@role, 'dialog')]"
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


def create_directory_hierarchy(dicts, path="data", indent=0):
    attachments_path = os.path.join(f"{path}/attachments")
    exclude_fields = ["children", "related_work"]

    for d in dicts:
        dir_name = f"{d['Task id']}_{d['Title']}"
        dir_path = os.path.join(path, dir_name)

        print(" " * indent + dir_name)
        logging.info(f"Creating directory in {dir_path}")
        os.makedirs(dir_path, exist_ok=True)  # create directory if it doesn't exist
        os.makedirs(attachments_path, exist_ok=True)

        if "discussions" in d and d["discussions"]:
            with open(os.path.join(dir_path, "discussion.md"), "w") as file:
                for discussion in d.pop("discussions"):
                    file.write(discussion["Title"] + "\n")
                    file.write(discussion["Content"] + "\n")

        with open(os.path.join(dir_path, "description.md"), "w") as file:
            file.write(d.pop("description"))

        with open(os.path.join(dir_path, "metadata.md"), "w") as file:
            for key, value in d.items():
                if key not in exclude_fields:
                    file.write(f"* {key}: {value}\n")

        with open(os.path.join(dir_path, "origin.md"), "w") as file:
            file.write(config.BASE_URL + config.WORK_ITEM_ENDPOINT + d["Task id"])

        if "children" in d:
            create_directory_hierarchy(d["children"], dir_path, indent + 2)


def create_related_work_contents(scrape_results, path: Path = Path("data")):
    for item in scrape_results:
        task_id = item.get("Task id")
        task_title = item.get("Title")
        folder_name = f"{task_id}_{task_title}"
        dir_path = Path(path, folder_name)

        folder_path = [i for i in Path(Path.cwd() / path).resolve().rglob(folder_name)]

        with open(os.path.join(folder_path[0], "related_work.md"), "w") as file:
            for related_work in item.get("related_work"):
                related_work_type = related_work.get("type")
                related_work_data = {
                    "type": related_work_type,
                    "links to item file": []
                }

                for work_items in related_work.get("related_work_items", []):
                    work_item_folder_name = work_items.get("link")
                    work_item_updated_at = work_items.get("updated_at")

                    work_item_path = [i for i in Path(Path.cwd() / "data").resolve().rglob(work_item_folder_name)]

                    if not work_item_path:
                        logging.error(work_items)
                        continue

                    work_item_path = work_item_path[0]
                    related_work_data["links to item file"].append({
                        "link": work_item_path,
                        "updated_at": work_item_updated_at
                    })

                file.write(f"* Type: {related_work_type}\n")

                for links in related_work_data.get("links to item file"):
                    file.write(f"    * Link to item file: `{links.get('link')}`\n")
                    file.write(f"    * Last update: {links.get('updated_at')}\n\n")

        if "children" in item:
            create_related_work_contents(item["children"], dir_path)


if __name__ == "__main__":
    download_directory = f'{os.getcwd()}/data/attachments'

    chrome_options = ChromeOptions()
    chrome_options.binary_location = config.BINARY_PATH_LOCATION
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--incognito")
    chrome_options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": download_directory,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        },
    )

    chrome_options.add_experimental_option("detach", True)
    save_file = "data/scrape_result.json"
    chrome_driver = get_driver_by_os()

    with webdriver.Chrome(options=chrome_options) as wd:
        scraper(wd, config.BASE_URL + config.BACKLOG_ENDPOINT, config.EMAIL, config.PASSWORD, save_file)

    # Clean attachments directory
    if os.path.isdir(download_directory):
        os.removedirs(download_directory)

    with open(save_file) as f:
        scrape_result = json.load(f)
        create_directory_hierarchy(scrape_result)
        create_related_work_contents(scrape_result)
