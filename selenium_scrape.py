from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
import time
import config


def click_button_by_id(driver, id):
    element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, id)))
    element.click()


def click_button_by_xpath(driver, xpath):
    element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath)))
    element.click()


def click_button_by_tag(driver, tag):
    element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.TAG_NAME, tag)))
    element.click()


def send_keys_by_name(driver, name, keys):
    element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.NAME, name)))
    element.send_keys(keys)


def find_elements_by_xpath(driver, xpath):
    try:
        e = WebDriverWait(driver, 10).until(
            EC.visibility_of_all_elements_located((By.XPATH, xpath))
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


def scrape_work_items(driver, e):
    # Extract the data you need from the current element

    result = {
        "id": e.find_element(By.XPATH, "//span[@aria-label='ID Field']").text,
        "title": e.find_element(
            By.XPATH, "//input[@aria-label='Title Field']"
        ).get_attribute("value"),
        "children": [],
    }

    child_xpath = (
        ".//div[child::div[contains(@class, 'la-group-title') "
        "and contains(text(), 'Child')]]//div[@class='la-item']"
    )

    child_elements = find_elements_by_xpath(e, child_xpath)

    if child_elements:
        for child in child_elements:
            task = child.find_element(By.XPATH, ".//a")
            child_id = task.get_attribute("href").split("/")[-1]
            result["children"].append(
                {
                    "id": child_id,
                    "title": task.text,
                    "children": [],
                }
            )

            task.click()
            time.sleep(5)

            dialog_xpath = f"//span[@aria-label='ID Field' and " \
                           f"contains(text(), '{child_id}')]//ancestor::div"

            child_dialog_box = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, dialog_xpath))
            )
            scrape_work_items(driver, child_dialog_box)
            # TODO: Fix the closing of dialog boxes
            click_button_by_xpath(child_dialog_box, ".//button[contains(@class, 'ui-button')]")
    else:
        click_button_by_xpath(e, ".//button[contains(@class, 'ui-button')]")

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

        result = scrape_work_items(driver, dialog_box)
        result_set.append(result)

        click_button_by_xpath(dialog_box, ".//button[contains(@class, 'ui-button')]")

    for result in result_set:
        print(result)

if __name__ == "__main__":
    chrome_options = ChromeOptions()
    # chrome_options.add_argument("--headless=new")
    # chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option("detach", True)

    with webdriver.Chrome(options=chrome_options) as wd:
        main(wd, config.URL, config.EMAIL, config.PASSWORD)
