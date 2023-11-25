import os
import platform
import re
import string
from datetime import datetime

from dateutil.parser import parse
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

import config


def click_button_by_id(driver, element_id):
    element = WebDriverWait(driver, config.MAX_WAIT_TIME).until(
        EC.element_to_be_clickable((By.ID, element_id))
    )
    element.click()


def click_button_by_xpath(driver, xpath, retry=0, web_driver=None):
    while retry < config.MAX_RETRIES:
        try:
            element = WebDriverWait(driver, config.MAX_WAIT_TIME).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            return element.click()

        except TimeoutException:
            print(f"Retrying click button xpath: {xpath} {retry}/{config.MAX_RETRIES}")
        except ElementClickInterceptedException:
            element = WebDriverWait(driver, config.MAX_WAIT_TIME).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            return web_driver.execute_script("arguments[0].click();", element)
        retry += 1


def send_keys_by_name(driver, name, keys):
    element = WebDriverWait(driver, config.MAX_WAIT_TIME).until(
        EC.element_to_be_clickable((By.NAME, name))
    )
    element.send_keys(keys)


def find_elements_by_xpath(driver, xpath):
    try:
        e = WebDriverWait(driver, config.MAX_WAIT_TIME).until(
            EC.visibility_of_all_elements_located((By.XPATH, xpath))
        )
    except Exception:
        return None

    return e


def find_element_by_xpath(driver, xpath):
    try:
        e = WebDriverWait(driver, config.MAX_WAIT_TIME).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
    except Exception:
        return None

    return e


def get_input_value(driver, xpath):
    if element := find_element_by_xpath(driver, xpath):
        return element.get_attribute("value")


def get_anchor_link(driver, xpath):
    if element := find_element_by_xpath(driver, xpath):
        return element.get_attribute("href")


def get_text(driver, xpath):
    if element := find_element_by_xpath(driver, xpath):
        return element.text


def add_line_break(word, max_length):
    if len(word) > max_length:
        return (
            word[:max_length]
            + "\\\n           "
            + add_line_break(word[max_length:], max_length)
        )
    else:
        return word


def expand_collapsed_by_xpath(driver):
    dialog_box = "//div[@role='dialog'][last()]"
    history_items = "//div[@class='history-item-list']"
    collapsed_xpath = f"{dialog_box}{history_items}//div[@aria-expanded='false']"
    collapsed = find_elements_by_xpath(driver, collapsed_xpath)

    if collapsed:
        for collapse_item in collapsed:
            collapse_item.click()


def convert_date(
    date_string, date_format="%d %B %Y %H:%M:%S", new_format="%Y_%m_%dT%H_%M_%S"
):
    try:
        date_obj = datetime.strptime(date_string, date_format)
    except ValueError:
        date_obj = parse(date_string, fuzzy=True)

    return date_obj.strftime(new_format)


def create_symlink(source, target):
    if platform.system() == "Windows":
        command = f'mklink /J "{target}" "{source}"'
        os.system(command)
    else:
        os.symlink(source, target)


def get_roman_numeral(num):
    roman_numerals = {
        1: "i",
        4: "iv",
        5: "v",
        9: "ix",
        10: "x",
        40: "xl",
        50: "l",
        90: "xc",
        100: "c",
        400: "cd",
        500: "d",
        900: "cm",
        1000: "m",
    }
    result = ""
    for value, symbol in sorted(roman_numerals.items(), reverse=True):
        while num >= value:
            result += symbol
            num -= value
    return result


def convert_links(soup):
    for link in soup.find_all("a"):
        markdown_link = f"[{link.text}]({link.get('href')})"
        link.replace_with(markdown_link)
    return soup


def convert_to_markdown(soup):
    for div in soup.find_all("div"):
        div.insert_after("\n")

    for ul in soup.find_all("ul"):
        markdown_ul = ""
        for li in ul.find_all("li"):
            li = convert_links(li)
            indentation_level = len(li.find_parents("ul")) - 1
            indentation = "  " * indentation_level
            markdown_ul += f"{indentation}* {li.text}\n"

        ul.replace_with(markdown_ul)

    prev_indentation_level = None
    last_occurrence_index = -1
    last_occurrence_indentation = False

    # Convert ordered lists
    for ol in soup.find_all("ol"):
        markdown_ol = ""
        index = 0
        letters = 0
        roman_numerals = 0

        for li in ol.find_all("li"):
            li = convert_links(li)
            indentation_level = len(li.find_parents("ol")) - 1
            indentation = "  " * indentation_level

            if indentation_level != prev_indentation_level:
                if prev_indentation_level == 1:
                    last_occurrence_index = len(markdown_ol) - 1
                    last_occurrence_indentation = True
                prev_indentation_level = indentation_level

            if indentation_level == 0:
                index += 1
                markdown_ol += f"{indentation}{index}. {li.text}\n"
            elif indentation_level == 1:
                label = string.ascii_lowercase[letters % 26]
                if letters >= 26:
                    label = string.ascii_lowercase[(letters // 26) - 1] + label
                letters += 1
                markdown_ol += f"{indentation}{label}. {li.text}\\\n"

            elif indentation_level == 2:
                if roman_numerals == 0:
                    markdown_ol.rstrip("\n")
                    markdown_ol += "\\\n"
                roman_numerals += 1
                markdown_ol += f"{indentation}{get_roman_numeral(index)}. {li.text}\\\n"
            else:
                pass

        if last_occurrence_indentation:
            markdown_ol = (
                markdown_ol[:last_occurrence_index].rstrip("\\\n")
                + markdown_ol[last_occurrence_index:]
            )

        ol.replace_with(markdown_ol)

    # Convert links
    convert_links(soup)

    return soup.get_text().rstrip()


def show_more(dialog_box, xpath):
    if show_more_button := find_element_by_xpath(dialog_box, xpath):
        show_more_button.click()
        show_more(dialog_box, xpath)

    return None


def validate_title(title: str):
    fixed_string = re.sub(r"[^a-zA-Z0-9]", "_", title)
    return fixed_string
