import logging
import re
import time
import urllib.parse
from uuid import uuid4

from bs4 import BeautifulSoup
from dateutil.parser import ParserError
from selenium.common.exceptions import StaleElementReferenceException, JavascriptException
from selenium.webdriver.common.action_chains import ActionChains
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

from driver_utils import session_re_authenticate


def scrape_basic_fields(dialog_box, driver, request_session, chrome_downloads, dialog_xpath):
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
    description_images = None
    summary_xpath = f"{dialog_xpath}//ul[@role='tablist']/li[2]"
    steps_xpath = f"{dialog_xpath}//ul[@role='tablist']/li[1]"

    try:
        html = dialog_box.get_attribute("innerHTML")
        soup = BeautifulSoup(html, "html.parser")
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

        if soup.find(attrs={"aria-label": "Collapse Repro Steps section."}):
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
            description_images = description_element.find_all("img")
            description = convert_to_markdown(description_element)
            resolution = (
                f"* Repro Steps\n\t* {convert_to_markdown(resolution_element)}\n"
            )

            basic_fields["Description"] = description + "\n" + resolution

        elif description_element := soup.find(attrs={"aria-label": "Description"}):
            description_images = description_element.find_all("img")
            description = convert_to_markdown(description_element)
            basic_fields["Description"] = description

        elif soup.find(attrs={"aria-label": "Steps"}):
            steps_content = soup.find("div", {"class": "test-steps-list"})
            steps_content = steps_content.find(
                "div", {"class": "grid-canvas", "role": "presentation"}
            )
            description = ""
            temp_steps = []

            for step in steps_content.select('div[class*="grid-row grid-row-normal"]')[:-1]:
                temp_steps += step.find_all("p")

                temp_steps.append(
                    BeautifulSoup("<p><br/></p>", features="html.parser").p
                )  # Adding for consistency

                temp_step_att = BeautifulSoup("<a></a>", features="html.parser").a

                if steps_att := step.find_all("a"):
                    combined_steps_att = ""

                    for step_att in steps_att:
                        combined_steps_att += f"{step_att.text.split(' ')[0]} "

                    temp_step_att = BeautifulSoup(
                        f"<div>{combined_steps_att}</div>", features="html.parser"
                    ).div

                temp_steps.append(temp_step_att)

            for idx in range(0, len(temp_steps), 4):
                description += f"{temp_steps[idx].text} \t {temp_steps[idx + 1].text} \t {temp_steps[idx + 2].text} \t {temp_steps[idx + 3].text}\n"

            if desc := find_element_by_xpath(driver, summary_xpath):
                driver.execute_script("arguments[0].click();", desc)
                html = dialog_box.get_attribute("innerHTML")
                soup = BeautifulSoup(html, "html.parser")
                description_element = soup.find(attrs={"aria-label": "Description"})

                description_images = description_element.find_all("img")
                description += convert_to_markdown(description_element)

            if steps_tab := find_element_by_xpath(driver, steps_xpath):
                driver.execute_script("arguments[0].click();", steps_tab)

            basic_fields["Description"] = description

        if description_images:
            for att in description_images:
                if img_src := att.get("src"):
                    parsed_url = urllib.parse.urlparse(img_src)
                    query_params = urllib.parse.parse_qs(parsed_url.query)
                    guid = query_params.pop("FileNameGuid", None)

                    key = "fileName"
                    orig_file_name = query_params.get(key)

                    if not orig_file_name:
                        key = "FileName"
                        orig_file_name = query_params.get(key)

                    if not orig_file_name:
                        continue

                    orig_file_name = orig_file_name[0]
                    file_name = f"{uuid4()}_{orig_file_name}"
                    query_params["fileName"] = [file_name]

                    query_params["download"] = "True"
                    query_params.pop("FileName", None)
                    path_url = parsed_url.path.split("/")[:-1]

                    payload = {
                        "query": urllib.parse.urlencode(query_params, doseq=True)
                    }

                    if guid:
                        path_url.append("attachments")
                        path_url.append(guid[0])
                        payload["path"] = "/".join(path_url)

                    updated_url = urllib.parse.urlunparse(
                        parsed_url._replace(
                            **payload
                        )
                    )
                    driver.get(updated_url)
                    img_urls.append({"filename": file_name})

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

    except AttributeError:
        return scrape_basic_fields(dialog_box, driver, request_session, chrome_downloads)


def scrape_attachments(request_session, driver, chrome_downloads):
    dialog_xpath = "//div[@role='dialog'][last()]"
    attachments_tab = f"{dialog_xpath}//ul[@role='tablist']/li[4]"
    details_tab = f"{dialog_xpath}//ul[@role='tablist']/li[1]"

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

        grid_rows_ctr = 0
        retry = 0

        print(f"Initial # of attachment found: {len(grid_rows)}")

        while grid_rows_ctr < len(grid_rows):
            grid_row = grid_rows[grid_rows_ctr]
            attachment_href = find_element_by_xpath(grid_row, ".//a")

            while not attachment_href and retry < config.MAX_RETRIES:
                print("Retrying attachment href...")
                grid_rows = find_elements_by_xpath(
                    driver,
                    f"({dialog_xpath}//div[@class='grid-content-spacer'])[last()]/parent::div//div[@role='row']",
                )
                print(f"# attachments re-found: {len(grid_rows)}")
                grid_row = grid_rows[grid_rows_ctr]
                attachment_href = find_element_by_xpath(grid_row, ".//a")
                retry += 1

            if not attachment_href:
                print(f"attachment not found")
                grid_rows_ctr += 1
                continue

            date_attached = find_element_by_xpath(grid_row, "./div[3]")
            attachment_url = attachment_href.get_attribute("href")
            parsed_url = urllib.parse.urlparse(attachment_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)

            updated_at = convert_date(date_attached.text, date_format="%d/%m/%Y %H:%M")
            key = "fileName"
            file_name = query_params.get(key)

            if not file_name:
                key = "FileName"
                file_name = query_params.get(key)

            if not file_name:
                print(f"File name not found on attachment: {attachment_url}")
                continue

            file_name = file_name[0]
            new_file_name = f"{updated_at}_{uuid4()}_{file_name}"

            query_params[key] = [new_file_name]
            updated_url = urllib.parse.urlunparse(
                parsed_url._replace(
                    query=urllib.parse.urlencode(query_params, doseq=True)
                )
            )
            attachments_data.append({"url": updated_url, "filename": new_file_name})

            print(f"Downloading attachment: {updated_url}")
            # request_download_image(
            #     request_session, updated_url, driver, chrome_downloads / new_file_name
            # )
            driver.get(updated_url)

            grid_rows_ctr += 1

        # Navigate back to details
        click_button_by_xpath(driver, details_tab)

        return attachments_data
    except (StaleElementReferenceException, AttributeError):
        return scrape_attachments(request_session, driver, chrome_downloads)


def get_element_text(element):
    if element is not None:
        return element.text


def scrape_history(driver, request_session, chrome_downloads):
    results = []
    dialog_box_xpath = "//div[@role='dialog'][last()]"
    details_tab_xpath = f"{dialog_box_xpath}//ul[@role='tablist']/li[1]"
    history_xpath = f"{dialog_box_xpath}//ul[@role='tablist']/li[2]"
    history_items_xpath = f"{dialog_box_xpath}//div[@class='history-item-summary' or contains(@class, 'history-item-selected')]"

    history_tab = find_element_by_xpath(driver, history_xpath)

    if history_tab and history_tab.accessible_name != "History":
        history_xpath = f"{dialog_box_xpath}//ul[@role='tablist']/li[4]"

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

    try:
        for history in history_items:
            driver.execute_script("arguments[0].click();", history)
            time.sleep(1)

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
                "Attachments": [],
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
                new_value = html_field.find("div", class_="html-field-new-value-container")
                new_value_text = new_value.find_all("span")[-1] if new_value else None
                old_value = html_field.find("div", class_="html-field-old-value-container")
                old_value_images = []

                if old_value:
                    old_image_urls = old_value.find_all("a")
                    old_value = old_value.find_all("span")[-1]

                    for image_url in old_image_urls:
                        image_url = image_url.get("href")
                        parsed_url = urllib.parse.urlparse(image_url)
                        query_params = urllib.parse.parse_qs(parsed_url.query)
                        guid = query_params.pop("FileNameGuid", None)
                        key = "fileName"
                        orig_file_name = query_params.get(key)

                        if not orig_file_name:
                            key = "FileName"
                            orig_file_name = query_params.get(key)

                        if not orig_file_name:
                            continue

                        orig_file_name = orig_file_name[0]

                        new_file_name = f"{uuid4()}_{orig_file_name}"
                        query_params["fileName"] = [new_file_name]
                        query_params["download"] = "True"
                        query_params.pop("FileName", None)
                        path_url = parsed_url.path.split("/")[:-1]

                        payload = {
                            "query": urllib.parse.urlencode(query_params, doseq=True)
                        }

                        if guid:
                            path_url.append("attachments")
                            path_url.append(guid[0])
                            payload["path"] = "/".join(path_url)

                        updated_url = urllib.parse.urlunparse(
                            parsed_url._replace(
                                **payload
                            )
                        )
                        driver.get(updated_url)

                        old_value_images.append({"File Name": new_file_name})

                new_value_images = []

                if new_value and (image_urls := new_value.find_all("a")):
                    for image_url in image_urls:
                        image_url = image_url.get("href")
                        parsed_url = urllib.parse.urlparse(image_url)
                        query_params = urllib.parse.parse_qs(parsed_url.query)
                        guid = query_params.pop("FileNameGuid", None)
                        key = "fileName"
                        orig_file_name = query_params.get(key)

                        if not orig_file_name:
                            key = "FileName"
                            orig_file_name = query_params.get(key)

                        if not orig_file_name:
                            continue

                        orig_file_name = orig_file_name[0]

                        new_file_name = f"{uuid4()}_{orig_file_name}"

                        query_params["fileName"] = [new_file_name]
                        query_params["download"] = "True"
                        query_params.pop("FileName", None)
                        path_url = parsed_url.path.split("/")[:-1]

                        payload = {
                            "query": urllib.parse.urlencode(query_params, doseq=True)
                        }

                        if guid:
                            path_url.append("attachments")
                            path_url.append(guid[0])
                            payload["path"] = "/".join(path_url)

                        updated_url = urllib.parse.urlunparse(
                            parsed_url._replace(
                                **payload
                            )
                        )
                        driver.get(updated_url)

                        new_value_images.append({"File Name": new_file_name})

                result["Fields"].append(
                    {
                        "name": field_name,
                        "old_value": get_element_text(old_value),
                        "old_attachments": old_value_images,
                        "new_value": get_element_text(new_value_text),
                        "new_attachments": new_value_images,
                    }
                )

            if added_comment := soup.find("div", {"class": "history-item-comment"}):
                img_discussion_attachments = []
                if image_urls := added_comment.find_all("a"):
                    for image_url in image_urls:
                        image_url = image_url.get("href")
                        parsed_url = urllib.parse.urlparse(image_url)
                        query_params = urllib.parse.parse_qs(parsed_url.query)
                        guid = query_params.pop("FileNameGuid", None)
                        key = "fileName"
                        orig_file_name = query_params.get(key)

                        if not orig_file_name:
                            key = "FileName"
                            orig_file_name = query_params.get(key)

                        if not orig_file_name:
                            continue

                        orig_file_name = orig_file_name[0]
                        new_file_name = f"{uuid4()}_{orig_file_name}"

                        query_params["fileName"] = [new_file_name]
                        query_params["download"] = "True"
                        query_params.pop("FileName", None)
                        path_url = parsed_url.path.split("/")[:-1]

                        payload = {
                            "query": urllib.parse.urlencode(query_params, doseq=True)
                        }

                        if guid:
                            path_url.append("attachments")
                            path_url.append(guid[0])
                            payload["path"] = "/".join(path_url)

                        updated_url = urllib.parse.urlunparse(
                            parsed_url._replace(
                                **payload
                            )
                        )
                        driver.get(updated_url)

                        img_discussion_attachments.append({"File Name": new_file_name})

                result["Fields"].append(
                    {
                        "name": "Comments",
                        "old_value": None,
                        "new_value": added_comment.text,
                        "new_attachments": img_discussion_attachments,
                    }
                )

            if editted_comments := soup.find(
                "div", {"class": "history-item-comment-edited"}
            ):
                old_comment = editted_comments.find("div", class_="old-comment")
                new_comment = editted_comments.find("div", class_="new-comment")

                new_comment_atts = []
                old_comment_atts = []

                if image_urls := old_comment.find_all("a"):
                    for image_url in image_urls:
                        image_url = image_url.get("href")
                        parsed_url = urllib.parse.urlparse(image_url)
                        query_params = urllib.parse.parse_qs(parsed_url.query)
                        guid = query_params.pop("FileNameGuid", None)
                        key = "fileName"
                        orig_file_name = query_params.get(key)

                        if not orig_file_name:
                            key = "FileName"
                            orig_file_name = query_params.get(key)

                        if not orig_file_name:
                            continue

                        orig_file_name = orig_file_name[0]
                        new_file_name = f"{uuid4()}_{orig_file_name}"

                        query_params["fileName"] = [new_file_name]
                        query_params["download"] = "True"
                        query_params.pop("FileName", None)
                        path_url = parsed_url.path.split("/")[:-1]

                        payload = {
                            "query": urllib.parse.urlencode(query_params, doseq=True)
                        }

                        if guid:
                            path_url.append("attachments")
                            path_url.append(guid[0])
                            payload["path"] = "/".join(path_url)

                        updated_url = urllib.parse.urlunparse(
                            parsed_url._replace(
                                **payload
                            )
                        )
                        driver.get(updated_url)

                        old_comment_atts.append({"File Name": new_file_name})

                if image_urls := new_comment.find_all("a"):
                    for image_url in image_urls:
                        image_url = image_url.get("href")
                        parsed_url = urllib.parse.urlparse(image_url)
                        query_params = urllib.parse.parse_qs(parsed_url.query)
                        guid = query_params.pop("FileNameGuid", None)
                        key = "fileName"
                        orig_file_name = query_params.get(key)

                        if not orig_file_name:
                            key = "FileName"
                            orig_file_name = query_params.get(key)

                        if not orig_file_name:
                            continue

                        orig_file_name = orig_file_name[0]
                        new_file_name = f"{uuid4()}_{orig_file_name}"

                        query_params["fileName"] = [new_file_name]
                        query_params["download"] = "True"
                        query_params.pop("FileName", None)
                        path_url = parsed_url.path.split("/")[:-1]

                        payload = {
                            "query": urllib.parse.urlencode(query_params, doseq=True)
                        }

                        if guid:
                            path_url.append("attachments")
                            path_url.append(guid[0])
                            payload["path"] = "/".join(path_url)

                        updated_url = urllib.parse.urlunparse(
                            parsed_url._replace(
                                **payload
                            )
                        )
                        driver.get(updated_url)

                        new_comment_atts.append({"File Name": new_file_name})

                result["Fields"].append(
                    {
                        "name": "Comments",
                        "old_value": old_comment.find(
                            "div", class_="history-item-comment"
                        ).text,
                        "new_value": new_comment.find(
                            "div", class_="history-item-comment"
                        ).text,
                        "old_attachments": old_comment_atts,
                        "new_attachments": new_comment_atts,
                    }
                )

            # Get Links
            if links := soup.find("div", class_="history-links"):
                links = links.find_all("div", class_="link")

                for link in links:
                    is_deleted = (
                        "Deleted" if "link-delete" in link.get("class") else "Added"
                    )
                    display_name = link.find("span", class_="link-display-name").text
                    link = link.find("span", class_="link-text")

                    try:
                        title = link.a.text.lstrip(": ")
                    except AttributeError:
                        title = link.text

                    try:
                        link_item_file = link.a.get("href")
                    except AttributeError:
                        link_item_file = link.text

                    result["Links"].append(
                        {
                            "Change Type": is_deleted,
                            "Type": display_name,
                            "Link to item file": link_item_file,
                            "Title": title,
                        }
                    )

            # Attachments
            if attachments := soup.find("div", class_="history-attachments"):
                attachments = attachments.find_all("div", class_="attachment")

                for attachment in attachments:
                    attachment_file_name = attachment.find(
                        "button", class_="attachment-text"
                    )
                    is_deleted = attachment.find("del")
                    attachment_change_type = "Deleted" if is_deleted else "Added"
                    result["Attachments"].append(
                        {
                            "Change Type": attachment_change_type,
                            "File Name": get_element_text(attachment_file_name),
                        }
                    )
            results.append(result)

        # Navigate back to details tab
        click_button_by_xpath(driver, details_tab_xpath)

        return results
    except StaleElementReferenceException:
        return scrape_history(driver, request_session, chrome_downloads)


def scrape_related_work(driver, dialog_box):
    try:
        results = []
        details_xpath = ".//ul[@role='tablist']/li[1]"
        related_work_xpath = ".//ul[@role='tablist']/li[3]"

        # Navigate to related work tab
        related_work_tab = find_element_by_xpath(dialog_box, related_work_xpath)

        retry = 0

        while not related_work_tab and retry < config.MAX_RETRIES:
            related_work_tab = find_element_by_xpath(dialog_box, related_work_xpath)
            print(f"Retrying related work tab... {retry}/{config.MAX_RETRIES}")
            time.sleep(1)
            retry += 1

        if not related_work_tab.text or "Links" not in related_work_tab.accessible_name:
            return []

        related_work_tab.click()

        time.sleep(3)

        grid_canvas_container_xpath = ".//div[@class='grid-canvas']"
        grid_canvas_container = find_element_by_xpath(
            dialog_box, grid_canvas_container_xpath
        )

        if grid_canvas_container:
            driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight", grid_canvas_container
            )

        related_work_items_xpath = f"{grid_canvas_container_xpath}//div[contains(@class, 'grid-row grid-row-normal') and @aria-level]"

        related_work_items = find_elements_by_xpath(dialog_box, related_work_items_xpath)

        # Click last work item to load all
        related_work_items[-1].click()

        related_work_items = find_elements_by_xpath(dialog_box, related_work_items_xpath)
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
                    "arguments[0].parentNode.removeChild(arguments[0]);", updated_at_element
                )
            else:
                related_work_type = element.find("span").get_text(strip=True)

                if related_work_type:
                    related_work_type = re.search(r"([^\(]+)", related_work_type)
                    related_work_type = related_work_type.group(1)
                    related_work_type = related_work_type.replace("\xa0", "")

                if related_work_type not in valid_labels:
                    related_work_type = None
                    continue

                related_work_type = re.search(r"^\w+", related_work_type).group()
                related_work_data[related_work_type] = []

        # Format
        for work_item_type, related_works in related_work_data.items():
            results.append({"type": work_item_type, "related_work_items": related_works})

        # Navigate back to details tab
        click_button_by_xpath(dialog_box, details_xpath)

        return results
    except JavascriptException:
        return scrape_related_work(driver, dialog_box)


def scrape_discussion_attachments(driver, attachment, discussion_date, request_session, chrome_downloads):
    parsed_url = urllib.parse.urlparse(attachment.get("src"))
    query_params = urllib.parse.parse_qs(parsed_url.query)
    guid = query_params.pop("FileNameGuid", None)
    key = "fileName"
    file_name = query_params.get(key)

    if not file_name:
        key = "FileName"
        file_name = query_params.get(key)

    if not file_name:
        return {}

    file_name = file_name[0]
    new_file_name = f"{discussion_date}_{uuid4()}_{file_name}"

    if "download" not in query_params:
        query_params["download"] = "True"

    query_params["fileName"] = [new_file_name]
    query_params.pop("FileName", None)
    path_url = parsed_url.path.split("/")[:-1]

    payload = {
        "query": urllib.parse.urlencode(query_params, doseq=True)
    }

    if guid:
        path_url.append("attachments")
        path_url.append(guid[0])
        payload["path"] = "/".join(path_url)

    updated_url = urllib.parse.urlunparse(
        parsed_url._replace(**payload)
    )
    driver.get(updated_url)

    return {"url": updated_url, "filename": new_file_name}


def scrape_discussions(driver, request_session, chrome_downloads):
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

        retry = 0
        while discussion_container is None and retry < 3:
            discussion_container = find_element_by_xpath(driver, container_xpath)

            if discussion_container:
                break

            retry += 1
            time.sleep(1)
            print("retrying discussion container...")

        html = discussion_container.get_attribute("innerHTML")
        soup = BeautifulSoup(html, "html.parser")

        discussions = soup.find_all("div", class_="comment-item-right")

        if discussions:
            for index, discussion in enumerate(discussions):
                index += 1
                username = discussion.find("span", class_="user-display-name").text
                discussion_content = discussion.find("div", class_="comment-content")
                attachments = discussion.find_all("img")
                content = convert_to_markdown(discussion_content)

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
                    actions = ActionChains(driver)
                    actions.move_to_element(comment_timestamp)
                    actions.perform()
                    time.sleep(3)

                result = {
                    "User": username,
                    "Content": content,
                    "Date": date,
                    "attachments": [],
                }

                for attachment in attachments or []:
                    attachment_data = scrape_discussion_attachments(
                        driver, attachment, date, request_session, chrome_downloads
                    )

                    if attachment_data:
                        result["attachments"].append(attachment_data)

                results.append(result)
        return results
    except (StaleElementReferenceException, AttributeError):
        return scrape_discussions(driver, request_session, chrome_downloads)


def scrape_changesets(driver):
    results = []

    files_changed = find_elements_by_xpath(driver, "//div[@role='treeitem']")

    if not files_changed:
        return results

    files_changed = files_changed[1:]

    for idx, file in enumerate(files_changed, start=2):
        driver.execute_script("arguments[0].click();", file)

        header_xpath = f"(//span[@class='file-name'])[{idx}]"

        result = {
            "File Name": get_text(driver, header_xpath),
            "Path": get_text(
                driver, "//span[@class='diff-summary-filepath']"
            )
        }

        results.append(result)
    return results


def scrape_development(driver, chrome_downloads, request_session):
    try:
        results = []
        dialog_box = "//div[@role='dialog'][last()]"
        development_section = "//span[@aria-label='Collapse Development section.']/ancestor::div[@class='grid-group']"
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
        return scrape_development(driver, chrome_downloads, request_session)


def log_html(page_source, log_file_path="source.log"):
    with open(log_file_path, "w", encoding="utf-8") as file:
        file.write(page_source)


def request_download_image(request_session, img_src, driver, file_path):
    response = request_session.get(img_src)

    if response.status_code == 203:
        session_re_authenticate(request_session, driver)
        response = request_session.get(img_src)

    if response.status_code != 200:
        logging.info(
            f"Error downloading image description: {response.status_code}: {str(response.content)}"
        )

    with open(file_path, "wb") as f:
        f.write(response.content)

    return response
