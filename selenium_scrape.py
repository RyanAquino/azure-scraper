from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
import time
import config


def click_button_by_id(driver, id):
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, id)))
    driver.find_element(By.ID, id).click()


def click_button_by_xpath(driver, xpath):
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath)))
    driver.find_element(By.XPATH, xpath).click()


def send_keys_by_name(driver, name, keys):
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.NAME, name)))
    driver.find_element(By.NAME, name).send_keys(keys)


def find_elements_by_xpath(driver, xpath):
    WebDriverWait(driver, 10).until(
        EC.visibility_of_all_elements_located((By.XPATH, xpath))
    )
    return driver.find_elements(By.XPATH, xpath)


def login(driver, email, password):
    send_keys_by_name(driver, "loginfmt", email)
    click_button_by_id(driver, "idSIButton9")
    send_keys_by_name(driver, "passwd", password)
    click_button_by_id(driver, "idSIButton9")
    click_button_by_id(driver, "idSIButton9")


def scrape_work_items(driver):
    # Extract the data you need from the current element

    result = {
        "id": driver.find_element(By.XPATH, "//span[@aria-label='ID Field']").text,
        "title": driver.find_element(
            By.XPATH, "//input[@aria-label='Title Field']"
        ).get_attribute("value"),
        "children": [],
    }

    child_xpath = (
        "//div[child::div[contains(@class, 'la-group-title') "
        "and contains(text(), 'Child')]]//div[@class='la-item']"
    )

    child_elements = find_elements_by_xpath(driver, child_xpath)

    if child_elements:
        for child in child_elements:
            result["children"].append(
                {
                    "id": child.find_element(By.XPATH, child_xpath + "//a")
                    .get_attribute("href")
                    .split("/")[-1],
                    "title": child.find_element(By.XPATH, child_xpath + "//a").text,
                    "children": [],
                }
            )

    # TODO: Fix login on recursion
    # dialog_xpath = "//div[contains(@tabindex, '-1') and contains(@role, 'dialog') and contains(@style, '10006')]"
    # click_button_by_xpath(child, child_xpath + "//a")
    # child_dialog_box = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, dialog_xpath)))
    #
    # scrape_work_items(child_dialog_box)
    #
    # click_button_by_xpath(child_dialog_box, ".//button[contains(@class, 'ui-button')]")

    # else:
    #     click_button_by_xpath(driver, ".//button[contains(@class, 'ui-button')]")

    return result


def main(driver, url, email, password):
    result_set = []

    # Navigate to site
    driver.get(url)
    wait = WebDriverWait(driver, 20)

    # Login
    login(driver, email, password)

    # Top Level Elements
    top_level_elements = find_elements_by_xpath(driver, '//div[@aria-level="1"]')

    for top_level_element in top_level_elements:
        click_button_by_xpath(top_level_element, ".//a")
        time.sleep(5)

        dialog_xpath = "//div[contains(@tabindex, '-1') and contains(@role, 'dialog')]"
        dialog_box = wait.until(
            EC.presence_of_element_located((By.XPATH, dialog_xpath))
        )

        result_set.append(scrape_work_items(dialog_box))

        click_button_by_xpath(dialog_box, ".//button[contains(@class, 'ui-button')]")

    print(result_set)


if __name__ == "__main__":
    chrome_options = ChromeOptions()
    # chrome_options.add_argument("--headless=new")
    # chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option("detach", True)

    with webdriver.Chrome(options=chrome_options) as wd:
        main(wd, config.URL, config.EMAIL, config.PASSWORD)
