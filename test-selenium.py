from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions

def click_button_by_id(driver, id):
    WebDriverWait(driver, 60).until(EC.element_to_be_clickable((By.ID, id)))
    driver.find_element(By.ID, id).click()


def send_keys_by_name(driver, name, keys):
    WebDriverWait(driver, 60).until(EC.element_to_be_clickable((By.NAME, name)))
    driver.find_element(By.NAME, name).send_keys(keys)


def main(driver):
    url = "https://dev.azure.com/nvtmsovybqhxqzgyzf/scrum/_backlogs/backlog/scrum%20Team/Epics/"
    email = "zumhxnwvstlnqvarxa@bbitq.com"
    password = "7aa2|id?ly3_4*{4U3^w"

    driver.get(url)

    send_keys_by_name(driver, "loginfmt", email)
    click_button_by_id(driver, "idSIButton9")
    send_keys_by_name(driver, "passwd", password)
    click_button_by_id(driver, "idSIButton9")
    click_button_by_id(driver, "idSIButton9")

    print(driver.get("meta"))

if __name__ == '__main__':
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless=new")
    # chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=chrome_options)

    main(driver)

    driver.close()




