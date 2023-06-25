import os
import platform
from datetime import datetime


from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

import config


def click_button_by_id(driver, element_id):
    element = WebDriverWait(driver, config.MAX_WAIT_TIME).until(
        EC.element_to_be_clickable((By.ID, element_id))
    )
    element.click()


def click_button_by_xpath(driver, xpath):
    element = WebDriverWait(driver, config.MAX_WAIT_TIME).until(
        EC.element_to_be_clickable((By.XPATH, xpath))
    )
    element.click()


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
    except Exception as e:
        return None

    return e


def find_element_by_xpath(driver, xpath):
    try:
        e = WebDriverWait(driver, config.MAX_WAIT_TIME).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
    except Exception as e:
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
            + "\n           "
            + add_line_break(word[max_length:], max_length)
        )
    else:
        return word


def expand_collapsed_by_xpath(dialog_box):
    collapsed_xpath = ".//div[@aria-expanded='false']"
    collapsed = find_elements_by_xpath(dialog_box, collapsed_xpath)

    if collapsed:
        for collapse_item in collapsed:
            collapse_item.click()


def convert_date(
    date_string, date_format="%d %B %Y %H:%M:%S", new_format="%Y_%m_%dT%H_%M_%S"
):
    date_obj = datetime.strptime(date_string, date_format)

    return date_obj.strftime(new_format)


def create_symlink(source, target):
    if platform.system() == "Windows":
        command = 'mklink /J "{}" "{}"'.format(target, source)
        os.system(command)
    else:
        os.symlink(source, target)
