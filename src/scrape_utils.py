import os
import re
import time
import urllib.parse
from pathlib import Path
from uuid import uuid4

from bs4 import BeautifulSoup
from dateutil.parser import ParserError
from selenium.common.exceptions import (
    StaleElementReferenceException,
    JavascriptException,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

import config
from action_utils import (
    click_button_by_xpath,
    convert_date,
    convert_to_markdown,
    expand_collapsed_by_xpath,
    find_element_by_xpath,
    find_elements_by_xpath,
    get_input_value,
    get_text,
    show_more,
    validate_title,
)


def scrape_basic_fields(dialog_box, request_session):
    labels = [
        "ID Field",
        "Assigned To Field",
        "State Field",
        "Area Path",
        "Iteration Path",
        "Priority",
        "Remaining Work",
        "Activity",
        "Blocked",
        "Effort",
        "Severity",
    ]

    basic_fields = {}

    html = dialog_box.get_attribute("innerHTML")
    soup = BeautifulSoup(html, "html.parser")
    description_element = None
    img_urls = []

    for element in soup.find_all(attrs={"aria-label": True}):
        attribute = element.get("aria-label")

        if attribute in labels:
            if attribute == "Assigned To Field":
                element = element.find("span", {"class": "text-cursor"})

            if element.name == "input":
                value = element.get("value")

                if "value" not in element:
                    input_xpath = f".//input[@aria-label='{attribute}']"
                    value = get_input_value(dialog_box, input_xpath)
            else:
                value = element.text if element.text else None

            basic_fields[attribute] = value

    if soup.find(attrs={"aria-label": "Repro Steps section."}):
        repro_steps_element = soup.find(attrs={"aria-label": "Repro Steps"})
        system_info_element = soup.find(attrs={"aria-label": "System Info"})
        acceptance_element = soup.find(attrs={"aria-label": "Acceptance Criteria"})

        if retro := convert_to_markdown(repro_steps_element):
            retro = f"* Repro Steps\n** {retro}\n"

        if system_info := convert_to_markdown(system_info_element):
            system_info = f"* System Info\n** {system_info}\n"

        if acceptance := convert_to_markdown(acceptance_element):
            acceptance = f"* Acceptance criteria \n** {acceptance}\n"

        basic_fields["Description"] = retro + system_info + acceptance
    elif soup.find(attrs={"aria-label": "Resolution section."}):
        description_element = soup.find(attrs={"aria-label": "Description"})
        resolution_element = soup.find(attrs={"aria-label": "Resolution"})
        description = f"* Description\n\t* {convert_to_markdown(description_element)}\n"
        resolution = f"* Repro Steps\n\t* {convert_to_markdown(resolution_element)}\n"

        basic_fields["Description"] = description + resolution

    else:
        description_element = soup.find(attrs={"aria-label": "Description"})
        description = convert_to_markdown(description_element)
        basic_fields["Description"] = description

    if description_element and description_element.img:
        attachments_path = Path(Path.cwd(), "data", "attachments")
        os.makedirs(attachments_path, exist_ok=True)
        img_atts = description_element.find_all("img")
        for att in img_atts:
            if img_src := att.get("src"):
                parsed_url = urllib.parse.urlparse(img_src)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                orig_file_name = query_params.get('FileName')[0]

                response = request_session.get(img_src)
                if response.status_code != 200:
                    continue

                file_name = f"{uuid4()}_{orig_file_name}"
                img_urls.append({"filename": file_name})

                with open(attachments_path / file_name, 'wb') as f:
                    f.write(response.content)

    return {
        "Task id": basic_fields["ID Field"],
        "User Name": basic_fields["Assigned To Field"],
        "State": basic_fields["State Field"],
        "Area": basic_fields["Area Path"],
        "Iteration": basic_fields["Iteration Path"],
        "Priority": basic_fields["Priority"],
        "Remaining Work": basic_fields.get("Remaining Work"),
        "Activity": basic_fields.get("Activity"),
        "Blocked": basic_fields.get("Blocked"),
        "Effort": basic_fields.get("Effort"),
        "Severity": basic_fields.get("Severity"),
        "description": basic_fields.get("Description"),
    }, img_urls


def scrape_attachments(driver):
    dialog_xpath = "//div[@role='dialog'][last()]"
    attachments_tab = f"{dialog_xpath}//li[@aria-label='Attachments']"
    details_tab = f"{dialog_xpath}//li[@aria-label='Details']"

    # Attachment count
    attachments_count = get_text(driver, f"{attachments_tab}/span[2]")

    if attachments_count is None:
        print("No attachments:", attachments_count)
        return

    # Navigate to attachments page
    click_button_by_xpath(driver, attachments_tab)

    # Retrieve attachment links
    try:
        attachments_data = []
        retry = 0
        grid_rows = []

        while retry < config.MAX_RETRIES:
            grid_rows = find_elements_by_xpath(
                driver,
                f"({dialog_xpath}//div[@class='grid-content-spacer'])[last()]/parent::div//div[@role='row']",
            )

            if grid_rows:
                break

            if retry == config.MAX_RETRIES:
                print("Error: Unable to find history items!!")
                return

            retry += 1
            print(
                f"Retrying to find attachment row items... {retry}/{config.MAX_RETRIES}"
            )

        retry = 0
        attachment_href = None

        for grid_row in grid_rows:
            while not attachment_href and retry < config.MAX_RETRIES:
                attachment_href = find_element_by_xpath(grid_row, ".//a")
                retry += 1
                print("Retrying attachment href...")

            if not attachment_href:
                continue

            date_attached = find_element_by_xpath(grid_row, "./div[3]")
            attachment_url = attachment_href.get_attribute("href")
            parsed_url = urllib.parse.urlparse(attachment_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)

            updated_at = convert_date(date_attached.text, date_format="%d/%m/%Y %H:%M")
            resource_id = parsed_url.path.split("/")[-1]

            file_name = query_params.get("fileName")[0]
            new_file_name = f"{updated_at}_{resource_id}_{file_name}"

            query_params["fileName"] = [new_file_name]
            updated_url = urllib.parse.urlunparse(
                parsed_url._replace(
                    query=urllib.parse.urlencode(query_params, doseq=True)
                )
            )
            attachments_data.append({"url": updated_url, "filename": new_file_name})

            driver.get(updated_url)

        # Navigate back to details
        click_button_by_xpath(driver, details_tab)

        return attachments_data
    except (StaleElementReferenceException, AttributeError):
        return scrape_attachments(driver)


def get_element_text(element):
    if element is not None:
        return element.text


def scrape_history(driver):
    results = []
    dialog_box_xpath = "//div[@role='dialog'][last()]"
    details_tab_xpath = f"{dialog_box_xpath}//li[@aria-label='Details']"
    history_xpath = f"{dialog_box_xpath}//li[@aria-label='History']"
    history_items_xpath = f"{dialog_box_xpath}//div[@class='history-item-summary' or contains(@class, 'history-item-selected')]"

    # Navigate to history tab
    click_button_by_xpath(driver, history_xpath)

    # Check if there are collapsed history items
    expand_collapsed_by_xpath(driver)

    retry = 0
    history_items = None

    while retry < config.MAX_RETRIES:
        history_items = find_elements_by_xpath(driver, history_items_xpath)

        if history_items:
            break

        if retry == config.MAX_RETRIES:
            print("Error: Unable to find history items!!")
            return

        retry += 1
        print(f"Retrying to find history items... {retry}/{config.MAX_RETRIES}")

    for history in history_items:
        history.click()

        details_xpath = f"{dialog_box_xpath}//div[@class='history-item-viewer']"
        details = find_element_by_xpath(driver, details_xpath)

        soup = BeautifulSoup(details.get_attribute("innerHTML"), "html.parser")
        username = soup.find("span", {"class": "history-item-name-changed-by"}).text
        date = soup.find("span", {"class": "history-item-date"}).text
        summary = soup.find("div", {"class": "history-item-summary-text"}).text

        result = {
            "User": username,
            "Date": date,
            "Title": summary,
            "Links": [],
            "Fields": [],
        }

        if history_fields := soup.find("div", class_="fields"):
            fields = history_fields.find_all("div", class_="field-name")

            for field in fields:
                field_name = field.span.text
                field_value = field.find_next_sibling("div", class_="field-values")

                new_value = field_value.find("span", class_="field-new-value")
                old_value = field_value.find("span", class_="field-old-value")
                result["Fields"].append(
                    {
                        "name": field_name,
                        "old_value": get_element_text(old_value),
                        "new_value": get_element_text(new_value),
                    }
                )
        if html_field := soup.find("div", class_="html-field"):
            field_name = html_field.find("div", {"class": "html-field-name"}).text
            old_value = html_field.find("div", class_="html-field-old-value-container")
            new_value = html_field.find("div", class_="html-field-new-value-container")

            result["Fields"].append(
                {
                    "name": field_name,
                    "old_value": get_element_text(old_value),
                    "new_value": get_element_text(new_value),
                }
            )

        if added_comment := soup.find("div", {"class": "history-item-comment"}):
            result["Fields"].append(
                {
                    "name": "Comments",
                    "old_value": None,
                    "new_value": added_comment.text,
                }
            )

        if editted_comments := soup.find(
            "div", {"class": "history-item-comment-edited"}
        ):
            old_comment = editted_comments.find("div", class_="old-comment")
            new_comment = editted_comments.find("div", class_="new-comment")

            result["Fields"].append(
                {
                    "name": "Comments",
                    "old_value": old_comment.text,
                    "new_value": new_comment.text,
                }
            )

        # Get Links
        if link := soup.find("div", class_="history-links"):
            display_name = link.find("span", class_="link-display-name").text
            link = link.find("span", class_="link-text")

            result["Links"].append(
                {
                    "Type": display_name,
                    "Link to item file": link.a.get("href") if link.a else None,
                    "Title": link.span.text.lstrip(": ") if link.span else None,
                }
            )

        results.append(result)

    # Navigate back to details tab
    click_button_by_xpath(driver, details_tab_xpath)

    return results


def scrape_related_work(driver, dialog_box):
    try:
        results = []
        details_xpath = ".//li[@aria-label='Details']"
        related_work_xpath = ".//li[@aria-label='Links']"

        # Navigate to related work tab
        related_work_tab = find_element_by_xpath(dialog_box, related_work_xpath)

        if not related_work_tab.text:
            return []

        related_work_tab.click()

        grid_canvas_container_xpath = ".//div[@class='grid-canvas']"
        grid_canvas_container = find_element_by_xpath(
            dialog_box, grid_canvas_container_xpath
        )
        driver.execute_script(
            "arguments[0].scrollTop = arguments[0].scrollHeight", grid_canvas_container
        )

        related_work_items_xpath = f"{grid_canvas_container_xpath}//div[contains(@class, 'grid-row grid-row-normal') and @aria-level]"
        related_work_items = find_elements_by_xpath(
            dialog_box, related_work_items_xpath
        )

        # Click last work item to load all
        related_work_items[-1].click()

        related_work_items = find_elements_by_xpath(
            dialog_box, related_work_items_xpath
        )
        related_work_items_elements = [
            related_work_item for related_work_item in related_work_items
        ]

        soup = BeautifulSoup(dialog_box.get_attribute("innerHTML"), "html.parser")
        soup = soup.find("div", {"class": "grid-canvas"})
        related_work_type = None
        related_work_data = {}
        valid_labels = [
            "Child",
            "Duplicate",
            "Duplicate Of",
            "Predecessor",
            "Related",
            "Successor",
            "Tested By",
            "Tests",
            "Parent",
        ]

        for index, element in enumerate(soup.find_all("div", {"aria-level": True})):
            is_label = element.get("aria-level") == "1"

            if not is_label and related_work_type:
                work_item = element.find("a")

                work_item_url = work_item.get("href")
                related_work_item_id = work_item_url.split("/")[-1]
                related_work_title = validate_title(work_item.get_text())

                updated_date = find_element_by_xpath(
                    related_work_items_elements[index],
                    ".//span[contains(text(), 'Updated')]",
                )

                if not updated_date:
                    continue

                driver.execute_script(
                    "arguments[0].dispatchEvent(new MouseEvent('mouseover', {'bubbles': true}));",
                    updated_date,
                )
                updated_at_element = find_element_by_xpath(
                    driver,
                    "(.//div[contains(text(), 'Updated by') and contains(@class, 'popup-content-container')])[last()]",
                )
                updated_at = updated_at_element.text

                related_work_data[related_work_type].append(
                    {
                        "filename_source": f"{related_work_item_id}_{related_work_title}",
                        "link_target": f"{related_work_item_id}_{related_work_title}_update_{convert_date(updated_at)}_{related_work_type}",
                        "updated_at": " ".join(updated_at.split(" ")[-4:]),
                        "url": work_item_url,
                    }
                )
                driver.execute_script(
                    "arguments[0].parentNode.removeChild(arguments[0]);",
                    updated_at_element,
                )
            else:
                related_work_type = element.find("span").get_text(strip=True)

                if related_work_type not in valid_labels:
                    related_work_type = None
                    continue

                related_work_type = re.search(r"^\w+", related_work_type).group()
                related_work_data[related_work_type] = []

        # Format
        for work_item_type, related_works in related_work_data.items():
            results.append(
                {"type": work_item_type, "related_work_items": related_works}
            )

        # Navigate back to details tab
        click_button_by_xpath(dialog_box, details_xpath)

        return results
    except JavascriptException:
        return scrape_related_work(driver, dialog_box)


def scrape_discussion_attachments(driver, attachment, discussion_date):
    parsed_url = urllib.parse.urlparse(attachment.get("src"))
    query_params = urllib.parse.parse_qs(parsed_url.query)
    resource_id = parsed_url.path.split("/")[-1]

    file_name = query_params.get("FileName")

    if not file_name:
        return {}

    file_name = file_name[0]
    new_file_name = f"{discussion_date}_{resource_id}_{file_name}"

    query_params["FileName"] = [new_file_name]

    if "download" not in query_params:
        query_params["download"] = "True"

    updated_url = urllib.parse.urlunparse(
        parsed_url._replace(query=urllib.parse.urlencode(query_params, doseq=True))
    )
    driver.get(updated_url)

    return {"url": updated_url, "filename": new_file_name}


def scrape_discussions(driver):
    try:
        results = []
        dialog_xpath = "//div[@role='dialog'][last()]"
        container_xpath = f"{dialog_xpath}//div[@class='comments-section']"
        javascript_command = "arguments[0].dispatchEvent(new MouseEvent('mouseover', {'bubbles': true}));"
        mouse_out_command = "arguments[0].parentNode.removeChild(arguments[0]);"

        contains_discussions = None
        retry = 0
        while contains_discussions is None and retry < 3:
            contains_discussions = find_element_by_xpath(
                driver, f"({container_xpath}//div[@class='comment-header-left'])[1]"
            )

            if contains_discussions:
                break

            retry += 1
            time.sleep(1)
            print("retrying discussion items...")

        discussion_container = find_element_by_xpath(driver, container_xpath)

        html = discussion_container.get_attribute("innerHTML")
        soup = BeautifulSoup(html, "html.parser")

        discussions = soup.find_all("div", class_="comment-item-right")

        if discussions:
            for index, discussion in enumerate(discussions):
                index += 1
                username = discussion.find("span", class_="user-display-name").text
                discussion_content = discussion.find("div", class_="comment-content")
                content = convert_to_markdown(discussion_content)
                attachments = discussion.find_all("img")

                comment_header_xpath = (
                    f"({container_xpath}//div[@class='comment-header-left'])[{index}]"
                )

                timestamp_xpath = (
                    f"({comment_header_xpath}//*[@class='comment-timestamp'])[1]"
                )
                comment_timestamp = find_element_by_xpath(driver, timestamp_xpath)

                date = None
                retry_count = 0
                while date is None and retry_count < config.MAX_RETRIES:
                    driver.execute_script(javascript_command, comment_timestamp)
                    date = get_text(
                        driver, "//p[contains(@class, 'ms-Tooltip-subtext')]"
                    )
                    date_element = find_element_by_xpath(
                        driver, "//p[contains(@class, 'ms-Tooltip-subtext')]"
                    )

                    if date_element:
                        try:
                            date = convert_date(date_element.text)
                        except ParserError:
                            raise
                        driver.execute_script(mouse_out_command, date_element)
                        break

                    retry_count += 1
                    print(
                        f"Retrying hover on discussion date ... {retry_count}/{config.MAX_RETRIES}"
                    )
                    driver.execute_script("arguments[0].click();", discussion_container)
                    time.sleep(3)

                result = {
                    "User": username,
                    "Content": content,
                    "Date": date,
                    "attachments": [],
                }

                for attachment in attachments or []:
                    attachment_data = scrape_discussion_attachments(
                        driver, attachment, date
                    )

                    if attachment_data:
                        result["attachments"].append(attachment_data)

                results.append(result)
        return results
    except (StaleElementReferenceException, AttributeError):
        return scrape_discussions(driver)


def scrape_changesets(driver):
    results = []

    files_changed = find_elements_by_xpath(driver, "//tr[@role='treeitem']")

    for file in files_changed:
        driver.execute_script("arguments[0].click();", file)

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
    try:
        results = []
        dialog_box = "//div[@role='dialog'][last()]"
        development_section = "//span[@aria-label='Development section.']/ancestor::div[@class='grid-group']"
        show_more(driver, f"{development_section}//div[@class='la-show-more']")
        development_items = find_elements_by_xpath(
            driver, f"{dialog_box}{development_section}//div[@class='la-item']"
        )

        original_window = driver.current_window_handle
        print("Development items", development_items)

        failed_texts = [
            ".//span[starts-with(text(), 'Integrated in build link can not be read.')]",
            ".//span[@class='la-text build-failed']",
            ".//div[starts-with(text(), 'Integrated in build')]",
        ]

        if development_items:
            for development_item in development_items:
                failed = [get_text(development_item, text) for text in failed_texts]

                if any(failed):
                    continue

                click_button_by_xpath(development_item, ".//a")

                WebDriverWait(driver, config.MAX_WAIT_TIME).until(
                    EC.number_of_windows_to_be(2)
                )

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
    except StaleElementReferenceException:
        return scrape_development(driver)


def log_html(page_source, log_file_path="source.log"):
    with open(log_file_path, "w", encoding="utf-8") as file:
        file.write(page_source)
