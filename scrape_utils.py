import re
import time
import urllib.parse
from uuid import uuid4

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from config import Config

from action_utils import (
    expand_collapsed_by_xpath,
    find_element_by_xpath,
    find_elements_by_xpath,
    get_anchor_link,
    get_text,
)

config = Config()


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
    attachments_data = []

    for attachment in attachments[-int(attachment_count) :]:
        attachment_url = attachment.get_attribute("href")
        parsed_url = urllib.parse.urlparse(attachment_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        file_name = f"{uuid4()}_{query_params.get('fileName')[0]}"
        query_params["fileName"] = [file_name]
        updated_url = urllib.parse.urlunparse(
            parsed_url._replace(query=urllib.parse.urlencode(query_params, doseq=True))
        )
        attachments_data.append({"url": updated_url, "filename": file_name})
        driver.get(updated_url)

    # Navigate back to details
    details_tab_xpath = "//li[@aria-label='Details']"
    details_tab_button = find_elements_by_xpath(dialog_box, details_tab_xpath)
    details_tab_button[-1].click()

    return attachments_data


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


def scrape_related_work(driver, dialog_box):
    related_work_xpath = (
        "(.//div[@class='links-control-container']/div[@class='la-main-component'])"
        "[last()]/div[@class='la-list']/div"
    )
    related_work_items = find_elements_by_xpath(dialog_box, related_work_xpath)
    results = []

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
                updated_at = get_text(
                    related_work, "//p[contains(@class, 'ms-Tooltip-subtext')]"
                )
                retry_count += 1
                print(
                    f"Retrying hover on work related date ... {retry_count}/{config.MAX_RETRIES}"
                )
                time.sleep(3)

            updated_at = " ".join(updated_at.split(" ")[-4:])

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
            date = None
            retry_count = 0

            while date is None and retry_count < config.MAX_RETRIES:
                action.move_to_element(comment_timestamp).perform()
                date = get_text(
                    discussion, "//p[contains(@class, 'ms-Tooltip-subtext')]"
                )
                retry_count += 1
                print(
                    f"Retrying hover on discussion date ... {retry_count}/{config.MAX_RETRIES}"
                )
                time.sleep(3)

            result = {
                "User": get_text(discussion, ".//span[@class='user-display-name']"),
                "Content": content,
                "Date": " ".join(date.split(" ")[-4:]),
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


def scrape_description(element):
    formatted_text = ""
    html = element.get_attribute("innerHTML")
    parsed_div = html.replace("</div>", "\n").replace("<div>", "")
    parsed_div = parsed_div.replace("&nbsp;", " ")

    # Extract anchor tags using regex
    pattern = r'<a\s+href="([^"]+)">([^<]+)</a>'
    matches = re.findall(pattern, parsed_div)

    for href, text in matches:
        formatted_text = parsed_div.replace(
            f'<a href="{href}">{text}</a>', f"[{text}]({href})"
        )

    return formatted_text
