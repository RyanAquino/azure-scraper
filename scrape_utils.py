import logging
import time
import urllib.parse
from collections import deque

from bs4 import BeautifulSoup

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

import config
from action_utils import (
    convert_date,
    convert_to_markdown,
    expand_collapsed_by_xpath,
    find_element_by_xpath,
    find_elements_by_xpath,
    get_anchor_link,
    get_text,
    show_more,
    get_input_value,
)


def scrape_basic_fields(dialog_box):
    title_xpath = ".//div[contains(@class, 'work-item-form-title initialized')]//input"
    title = get_input_value(dialog_box, title_xpath)
    description_xpath = ".//div[contains(@class, 'work-item-control initialized')]//*[@aria-label='Description']"
    description = find_element_by_xpath(dialog_box, description_xpath)

    if title is None:
        return

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
    ]
    basic_fields = {}

    soup = BeautifulSoup(dialog_box.get_attribute("innerHTML"), "html.parser")
    description_soup = BeautifulSoup(
        description.get_attribute("innerHTML"), "html.parser"
    )

    for element in soup.select("[aria-label]"):
        attribute = element.get("aria-label")

        if attribute in labels:
            if attribute == "Assigned To Field":
                element = element.find("span", {"class": "text-cursor"})

            if element.name == "input":
                value = element.get("value")

                if "value" not in element:
                    value = get_input_value(
                        dialog_box, f"//input[@aria-label='{attribute}']"
                    )

            else:
                value = element.text if element.text else None

            basic_fields[attribute] = value

    return {
        "Task id": basic_fields["ID Field"],
        "Title": title.replace(" ", "_"),
        "User Name": basic_fields["Assigned To Field"],
        "State": basic_fields["State Field"],
        "Area": basic_fields["Area Path"],
        "Iteration": basic_fields["Iteration Path"],
        "Priority": basic_fields["Priority"],
        "Remaining Work": basic_fields.get("Remaining Work"),
        "Activity": basic_fields.get("Activity"),
        "Blocked": basic_fields.get("Blocked"),
        "description": convert_to_markdown(description_soup),
    }


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
    attachments_data = []

    attachment_rows = find_elements_by_xpath(
        dialog_box,
        "(.//div[@class='grid-content-spacer'])[last()]/parent::div//div[@role='row']",
    )

    a_href_xpath = ".//div[contains(@class, 'attachments-grid-file-name')]//a"
    date_attached_xpath = ".//div[3]"
    attachments = []

    for attachment in attachment_rows:
        attachment_href = find_element_by_xpath(attachment, a_href_xpath)
        attachment_url = attachment_href.get_attribute("href")
        date_attached = find_element_by_xpath(attachment, date_attached_xpath)

        parsed_url = urllib.parse.urlparse(attachment_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        updated_at = convert_date(date_attached.text, date_format="%d/%m/%Y %H:%M")
        resource_id = parsed_url.path.split("/")[-1]

        file_name = query_params.get("fileName")[0]
        new_file_name = f"{updated_at}_{resource_id}_{file_name}"

        query_params["fileName"] = [new_file_name]
        updated_url = urllib.parse.urlunparse(
            parsed_url._replace(query=urllib.parse.urlencode(query_params, doseq=True))
        )
        attachments_data.append({"url": updated_url, "filename": new_file_name})
        attachments.append(updated_url)

    deque(map(driver.get, attachments))

    # Navigate back to details
    details_tab_xpath = "//li[@aria-label='Details']"
    details_tab_button = find_elements_by_xpath(dialog_box, details_tab_xpath)
    details_tab_button[-1].click()

    return attachments_data


def get_element_text(element):
    if element is not None:
        return element.text


def scrape_history(driver):
    results = []
    dialog_box = "//div[@role='dialog'][last()]"

    # Check if there are collapsed history items
    expand_collapsed_by_xpath(driver)

    history_items = find_elements_by_xpath(
        driver,
        f"{dialog_box}//div[@class='history-item-summary']",
    )

    for history in history_items:
        history.click()

        details_xpath = f"{dialog_box}//div[@class='history-item-viewer']"
        details = find_element_by_xpath(driver, details_xpath)

        soup = BeautifulSoup(details.get_attribute("innerHTML"), "html.parser")
        username = soup.find("span", {"class": "history-item-name-changed-by"}).text
        date = soup.find("span", {"class": "history-item-date"}).text
        summary = soup.find("div", {"class": "history-item-summary-text"}).text

        print(username, date, summary)

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
            field_name = html_field.find("div", {"class": "html-field-name"})
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
                    "Link to item file": link.a.get("href"),
                    "Title": link.span.text,
                }
            )

    results.append(result)
    return results


def scrape_related_work(driver, dialog_box):
    results = []

    related_work_xpath = "(.//div[@class='links-control-container']/div[@class='la-main-component'])[last()]"
    show_more_xpath = "//div[@class='la-show-more']"
    show_more(dialog_box, f"{related_work_xpath}{show_more_xpath}")

    related_work_items = find_elements_by_xpath(
        dialog_box, f"{related_work_xpath}/div[@class='la-list']/div"
    )

    if not related_work_items:
        return results

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
            updated_at = None
            retry_count = 0

            while updated_at is None and retry_count < config.MAX_RETRIES:
                driver.execute_script(
                    "arguments[0].dispatchEvent(new MouseEvent('mouseover', {'bubbles': true}));",
                    updated_at_hover,
                )
                updated_at = get_text(driver, "//p[contains(text(), 'Updated by')]")
                retry_count += 1
                print(
                    f"Retrying hover on work related date ... {retry_count}/{config.MAX_RETRIES}"
                )
                time.sleep(3)

            logging.info(f"related work item '{updated_at}'")

            driver.execute_script(
                "arguments[0].dispatchEvent(new MouseEvent('mouseout', {'bubbles': true}));",
                updated_at_hover,
            )

            related_work_item_id = related_work_link.get_attribute("href").split("/")[
                -1
            ]
            related_work_title = related_work_link.text.replace(" ", "_")
            result["related_work_items"].append(
                {
                    "filename_source": f"{related_work_item_id}_{related_work_title}",
                    "link_target": f"{related_work_item_id}_{related_work_title}_update_{convert_date(updated_at)}_{related_work_type}",
                    "updated_at": " ".join(updated_at.split(" ")[-4:]),
                }
            )

        results.append(result)

    return results


def scrape_discussion_attachments(attachment, discussion_date):
    parsed_url = urllib.parse.urlparse(attachment.get("src"))
    query_params = urllib.parse.parse_qs(parsed_url.query)
    resource_id = parsed_url.path.split("/")[-1]

    file_name = query_params.get("fileName")[0]
    new_file_name = f"{convert_date(discussion_date)}_{resource_id}_{file_name}"

    query_params["fileName"] = [new_file_name]

    if "download" not in query_params:
        query_params["download"] = "True"

    updated_url = urllib.parse.urlunparse(
        parsed_url._replace(query=urllib.parse.urlencode(query_params, doseq=True))
    )

    return {"url": updated_url, "filename": query_params["fileName"][0]}


def scrape_discussions(driver):
    results = []
    dialog_xpath = "//div[@role='dialog'][last()]"
    container_xpath = f"{dialog_xpath}//div[@class='comments-section']"
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
                driver.execute_script(
                    "arguments[0].dispatchEvent(new MouseEvent('mouseover', {'bubbles': true}));",
                    comment_timestamp,
                )
                date = get_text(driver, "//p[contains(@class, 'ms-Tooltip-subtext')]")

                if date:
                    break

                retry_count += 1
                print(
                    f"Retrying hover on discussion date ... {retry_count}/{config.MAX_RETRIES}"
                )
                time.sleep(3)

            result = {
                "User": username,
                "Content": content,
                "Date": date,
                "attachments": [
                    scrape_discussion_attachments(attachment, date)
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


def log_html(page_source, log_file_path="source.log"):
    with open(log_file_path, "w", encoding="utf-8") as file:
        file.write(page_source)
