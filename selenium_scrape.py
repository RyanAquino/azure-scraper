from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium import webdriver
from datetime import datetime
from pathlib import Path
from uuid import uuid4
import urllib.parse
import platform
import logging
import shutil
import config
import time
import json
import os

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
            EC.presence_of_all_elements_located((By.XPATH, xpath))
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


def get_anchor_link(driver, xpath):
    if element := find_element_by_xpath(driver, xpath):
        return element.get_attribute("href")


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
    attachment_count = "".join(
        [char for char in attachment_count.strip() if char.isdigit()]
    )
    a_href_xpath = ".//div[contains(@class, 'attachments-grid-file-name')]//a"
    attachments = find_elements_by_xpath(dialog_box, a_href_xpath)

    for attachment in attachments[-int(attachment_count) :]:
        attachment_url = attachment.get_attribute("href")
        parsed_url = urllib.parse.urlparse(attachment_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        query_params["fileName"] = [f"{uuid4()}_{query_params.get('fileName')[0]}"]
        updated_url = urllib.parse.urlunparse(
            parsed_url._replace(query=urllib.parse.urlencode(query_params, doseq=True))
        )
        logging.info(f"Downloading attachments from {updated_url}")
        driver.get(updated_url)

    # Navigate back to details
    details_tab_xpath = "//li[@aria-label='Details']"
    details_tab_button = find_elements_by_xpath(dialog_box, details_tab_xpath)
    details_tab_button[-1].click()


def expand_collapsed_by_xpath(dialog_box):
    collapsed_xpath = ".//div[@aria-expanded='false']"
    collapsed = find_elements_by_xpath(dialog_box, collapsed_xpath)

    if collapsed:
        for collapse_item in collapsed:
            collapse_item.click()


def scrape_history(dialog_box):
    results = []

    # Check if there are collapsed history items
    expand_collapsed_by_xpath(dialog_box)

    history_container_xpath = (
        "(//div[contains(@class, 'workitem-history-control-container')])[last()]"
    )

    history_items = find_elements_by_xpath(
        dialog_box,
        f"{history_container_xpath}//div[@class='history-item-summary-details']",
    )

    for history in history_items:
        history.click()

        details_panel_xpath = (
            f"{history_container_xpath}//div[@class='history-details-panel']"
        )

        result = {
            "User": get_text(
                dialog_box,
                f"{details_panel_xpath}//span[contains(@class, 'history-item-name-changed-by')]",
            ),
            "Date": get_text(
                dialog_box,
                f"{details_panel_xpath}//span[contains(@class, 'history-item-date')]",
            ),
            "Title": get_text(
                dialog_box,
                f"{details_panel_xpath}//div[contains(@class, 'history-item-summary-text')]",
            ),
            "Content": None,
            "Links": [],
            "Fields": [],
        }

        # Get all field changes
        if fields := find_elements_by_xpath(
            dialog_box, f"{details_panel_xpath}//div[@class='field-name']"
        ):
            for field in fields:
                field_name = get_text(field, ".//span")
                field_value = find_element_by_xpath(field, "./following-sibling::div")
                old_value = get_text(field_value, ".//span[@class='field-old-value']")
                new_value = get_text(field_value, ".//span[@class='field-new-value']")

                result["Fields"].append(
                    {"name": field_name, "old_value": old_value, "new_value": new_value}
                )

        if html_field := find_elements_by_xpath(
            dialog_box,
            f"{details_panel_xpath}//div[@class='html-field-name history-section']",
        ):
            for field in html_field:
                field_name = get_text(
                    field,
                    f"{details_panel_xpath}//div[@class='html-field-name history-section']",
                )
                field_value = find_element_by_xpath(
                    field, "//parent::div/following-sibling::div"
                )
                old_value = get_text(
                    field_value, "//span[@class='html-field-old-value']"
                )
                new_value = get_text(
                    field_value, "//span[@class='html-field-new-value']"
                )

                result["Fields"].append(
                    {"name": field_name, "old_value": old_value, "new_value": new_value}
                )

        # Get comments
        if comment := get_text(
            dialog_box,
            f"{details_panel_xpath}//div[contains(@class, 'history-item-comment')]",
        ):
            result["Content"] = comment

        # Get Links
        if links := find_elements_by_xpath(
            dialog_box, f"{details_panel_xpath}//div[@class='history-links']"
        ):
            for link in links:
                result["Links"].append(
                    {
                        "Type": get_text(
                            link, ".//span[contains(@class, 'link-display-name')]//span"
                        ),
                        "Link to item file": get_anchor_link(
                            link, ".//span[contains(@class, 'link-text')]//a"
                        ),
                        "Title": get_text(
                            link, ".//span[contains(@class, 'link-text')]//span"
                        ),
                    }
                )

        results.append(result)

    return results


def scrape_related_work(action, dialog_box):
    related_work_xpath = (
        "(.//div[@class='links-control-container']/div[@class='la-main-component'])"
        "[last()]/div[@class='la-list']/div"
    )
    related_work_items = find_elements_by_xpath(dialog_box, related_work_xpath)
    results = []

    for related_work_item in related_work_items:
        related_work_type_xpath = "div[@class='la-group-title']"
        related_work_type = find_element_by_xpath(
            related_work_item, related_work_type_xpath
        )

        related_work_type = related_work_type.text
        related_work_type = related_work_type.split(" ")[0]
        result = {"type": related_work_type, "related_work_items": []}

        related_works_xpath = "div[@class='la-item']"
        related_works = find_elements_by_xpath(related_work_item, related_works_xpath)

        updated_at_hover_xpath = (
            "div/div/div[@class='la-additional-data']/div[1]/div/span"
        )

        for related_work in related_works:
            related_work_link = find_element_by_xpath(related_work, "div/div/div//a")

            updated_at_hover = find_element_by_xpath(
                related_work, updated_at_hover_xpath
            )
            action.move_to_element(updated_at_hover).perform()
            updated_at = get_text(related_work, "//p[contains(@class, 'subText-74')]")
            updated_at = " ".join(updated_at.split(" ")[-5:])

            related_work_url = related_work_link.get_attribute("href").split("/")[-1]
            related_work_title = related_work_link.text
            result["related_work_items"].append(
                {
                    "link": f"{related_work_url}_{related_work_title}",
                    "updated_at": updated_at,
                }
            )

        results.append(result)

    return results


def scrape_discussion_attachments(driver, attachment):
    parsed_url = urllib.parse.urlparse(attachment.get_attribute("src"))
    query_params = urllib.parse.parse_qs(parsed_url.query)
    query_params["fileName"] = [f"{uuid4()}_{query_params.get('fileName')[0]}"]

    if "download" not in query_params:
        query_params["download"] = "True"

    updated_url = urllib.parse.urlunparse(
        parsed_url._replace(query=urllib.parse.urlencode(query_params, doseq=True))
    )
    driver.get(updated_url)

    return {"url": updated_url, "filename": query_params["fileName"][0]}


def scrape_discussions(driver, action):
    results = []

    dialog_xpath = "//div[@role='dialog'][last()]"

    discussions_xpath = (
        f"{dialog_xpath}//div[contains(@class, 'initialized work-item-discussion-control')]"
        "//div[contains(@class, 'wit-comment-item')]"
    )
    discussions = find_elements_by_xpath(driver, discussions_xpath)

    if discussions:
        for discussion in discussions:
            content_xpath = ".//div[@class='comment-content']"
            content = get_text(discussion, content_xpath)

            content_attachment_xpath = f"{content_xpath}//img"
            attachments = find_elements_by_xpath(discussion, content_attachment_xpath)
            comment_timestamp = find_element_by_xpath(
                discussion, ".//a[@class='comment-timestamp']"
            )
            action.move_to_element(comment_timestamp).perform()
            date = get_text(discussion, "//p[contains(@class, 'subText-74')]")

            result = {
                "User": get_text(discussion, ".//span[@class='user-display-name']"),
                "Content": content,
                "Date": date,
                "attachments": [
                    scrape_discussion_attachments(driver, attachment)
                    for attachment in (attachments or [])
                ],
            }
            results.append(result)
    return results


def scrape_changesets(driver):
    results = []

    files_changed = find_elements_by_xpath(driver, "//tr[@role='treeitem']")

    for file in files_changed:
        file.click()

        header_xpath = "//span[@role='heading']"

        result = {
            "File Name": get_text(driver, header_xpath),
            "Path": get_text(
                driver, f"{header_xpath}/parent::span/following-sibling::span"
            ),
            "content": get_text(
                driver,
                "(//div[contains(@class,'lines-content')])[last()]",
            ),
        }

        results.append(result)
    return results


def scrape_development(driver):
    results = []

    development_links = find_elements_by_xpath(
        driver,
        f"//div[@role='dialog'][last()]//span[@aria-label='Development section.']/ancestor::div[@class='grid-group']//a",
    )

    original_window = driver.current_window_handle

    if development_links:
        for development_link in development_links:
            development_link.click()

            WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))

            driver.switch_to.window(driver.window_handles[-1])
            result = {
                "ID": driver.current_url.split("/")[-1],
                "Title": driver.title,
                "change_sets": scrape_changesets(driver),
            }
            results.append(result)

            driver.close()
            driver.switch_to.window(original_window)
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
    work_item_data = {}
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
        "description": get_text(dialog_box, description),
        "related_work": scrape_related_work(action, dialog_box),
        "discussions": scrape_discussions(driver, action),
    }

    scrape_attachments(driver, dialog_box)

    details_xpath = ".//li[@aria-label='Details']"
    history_xpath = ".//li[@aria-label='History']"

    # Navigate to history tab
    click_button_by_xpath(dialog_box, history_xpath)

    work_item_data["history"] = scrape_history(dialog_box)

    # Navigate back to details tab
    click_button_by_xpath(dialog_box, details_xpath)

    work_item_data["development"] = scrape_development(driver)
    child_work_items = find_elements_by_xpath(dialog_box, child_xpath)

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

        logging.info(f"Open dialog box for '{work_item_element_text}'")
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


def add_line_break(word, max_length):
    if len(word) > max_length:
        return (
            word[:max_length]
            + "\n           "
            + add_line_break(word[max_length:], max_length)
        )
    else:
        return word


def create_history_metadata(history, file):
    for item in history:
        file.write(f"* Date: {item['Date']}\n")
        file.write(f"   * User: {item['User']}\n")
        file.write(f"   * Title: {item['Title']}\n")

        if item["Content"]:
            file.write(f"   * Content: {add_line_break(item['Content'], 60)}\n")

        if item["Fields"]:
            file.write(f"   * Fields\n")
            fields = item["Fields"]

            for index in range(0, len(fields)):
                field = fields[index]

                file.write(f"       * {field['name']}\n")
                file.write(f"           * Old Value: {field['old_value']}\n")
                file.write(f"           * New Value: {field['new_value']}\n")

        if links := item.get("Links"):
            for link in links:
                file.write(f"   * Links\n")
                file.write(f"       * Type: {link['Type']}\n")
                file.write(f"       * Link to item file: {link['Link to item file']}\n")
                file.write(f"       * Title: {link['Title']}\n")


def create_directory_hierarchy(dicts, path=os.path.join(os.getcwd(), "data"), indent=0):
    attachments_path = os.path.join(path, "attachments")
    exclude_fields = ["children", "related_work", "discussions", "history"]

    for d in dicts:
        dir_name = f"{d['Task id']}_{d['Title']}"
        dir_path = os.path.join(path, dir_name)
        discussion_path = os.path.join(dir_path, "discussion")
        development_path = os.path.join(dir_path, "development")
        discussion_attachments_path = os.path.join(discussion_path, "attachments")

        print(" " * indent + dir_name)
        logging.info(f"Creating directory in {dir_path}")
        os.makedirs(dir_path, exist_ok=True)
        os.makedirs(discussion_path, exist_ok=True)
        shutil.rmtree(discussion_path)
        os.makedirs(discussion_attachments_path, exist_ok=True)
        os.makedirs(development_path, exist_ok=True)

        if "history" in d and d["history"]:
            with open(os.path.join(dir_path, "history.md"), "w") as file:
                create_history_metadata(d.pop("history"), file)

        if "discussions" in d and d["discussions"]:
            for discussion in d.pop("discussions"):
                discussion_date = datetime.strptime(
                    discussion["Date"], "%A, %B %d, %Y %H:%M:%S %p"
                )

                file_name = (
                    f"{discussion_date.strftime('%Y_%m_%d')}_{discussion['User']}.md"
                )
                with open(os.path.join(discussion_path, file_name), "a+") as file:
                    file.write(
                        f"* Title: <{discussion['User']} commented {discussion_date.strftime('%B %d, %Y %H:%m:%S %p')}>\n"
                    )
                    file.write(
                        f"* Content: {add_line_break(discussion['Content'], 90)}\n"
                    )

                if discussion["attachments"]:
                    for attachment in discussion["attachments"]:
                        source = os.path.join(attachments_path, attachment["filename"])
                        destination = os.path.join(
                            discussion_attachments_path, attachment["filename"]
                        )

                        if os.path.exists(source):
                            shutil.move(source, destination)

        with open(os.path.join(dir_path, "description.md"), "w") as file:
            if d["description"]:
                file.write(d.pop("description"))

        with open(os.path.join(dir_path, "metadata.md"), "w") as file:
            for key, value in d.items():
                if key not in exclude_fields:
                    file.write(f"* {key}: {value}\n")

        with open(os.path.join(dir_path, "origin.md"), "w") as file:
            file.write(config.BASE_URL + config.WORK_ITEM_ENDPOINT + d["Task id"])

        for development in d.pop("development"):
            with open(
                os.path.join(development_path, f"changeset_{development['ID']}.md"), "w"
            ) as file:
                if change_sets := development["change_sets"]:
                    for change_set in change_sets:
                        file.write(f"* 'File Name': {change_set['File Name']}\n")
                        file.write(f"* 'Path': {change_set['Path']}\n")
                        file.write(f"* 'Content': {change_set['content']}\n")

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
                    "links to item file": [],
                }

                for work_items in related_work.get("related_work_items", []):
                    work_item_folder_name = work_items.get("link")
                    work_item_updated_at = work_items.get("updated_at")

                    work_item_path = [
                        i
                        for i in Path(Path.cwd() / "data")
                        .resolve()
                        .rglob(work_item_folder_name)
                    ]

                    if not work_item_path:
                        logging.error(work_items)
                        continue

                    work_item_path = work_item_path[0]
                    related_work_data["links to item file"].append(
                        {"link": work_item_path, "updated_at": work_item_updated_at}
                    )

                file.write(f"* Type: {related_work_type}\n")

                for links in related_work_data.get("links to item file"):
                    file.write(f"    * Link to item file: `{links.get('link')}`\n")
                    file.write(f"    * Last update: {links.get('updated_at')}\n\n")

        if "children" in item:
            create_related_work_contents(item["children"], dir_path)


def chrome_settings_init():
    download_directory = Path(f"{os.getcwd()}/data/attachments")

    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--incognito")
    chrome_options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": str(download_directory),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
        },
    )

    chrome_options.add_experimental_option("detach", True)
    chrome_settings = {"options": chrome_options}

    if config.BINARY_PATH_LOCATION:
        chrome_options.binary_location = config.BINARY_PATH_LOCATION
    else:
        chrome_settings["service"] = get_driver_by_os()

    return chrome_settings, download_directory


if __name__ == "__main__":
    save_file = "data/scrape_result.json"

    chrome_config, chrome_downloads = chrome_settings_init()

    # Clean attachments directory
    if os.path.isdir(chrome_downloads):
        shutil.rmtree(chrome_downloads)
        os.makedirs(chrome_downloads)

    with webdriver.Chrome(**chrome_config) as wd:
        scraper(
            wd,
            config.BASE_URL + config.BACKLOG_ENDPOINT,
            config.EMAIL,
            config.PASSWORD,
            save_file,
        )

    with open(save_file) as f:
        scrape_result = json.load(f)
        create_directory_hierarchy(scrape_result)
        create_related_work_contents(scrape_result)
