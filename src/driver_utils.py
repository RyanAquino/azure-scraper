import os
import shutil
from pathlib import Path
from platform import system

from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service

import config


def chrome_settings_init():
    download_directory = Path(os.getcwd(), "data", "attachments")
    language_code = "en-GB"

    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.accept_insecure_certs = True
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("--disk-cache-size=0")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1900,1080")
    chrome_options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": str(download_directory),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "intl.accept_languages": language_code,
        },
    )

    chrome_options.add_experimental_option("detach", True)
    chrome_settings = {"options": chrome_options}

    if config.BINARY_PATH_LOCATION:
        chrome_options.binary_location = config.BINARY_PATH_LOCATION

    if system() == "Windows":
        chrome_settings["service"] = Service(executable_path="drivers/chromedriver.exe")

    # Clean attachments directory
    if os.path.isdir(download_directory) and not os.listdir(download_directory):
        shutil.rmtree(download_directory)

    os.makedirs(download_directory, exist_ok=True)

    return chrome_settings, download_directory


def session_re_authenticate(request_session, driver):
    selenium_user_agent = driver.execute_script("return navigator.userAgent;")
    request_session.headers.update({"user-agent": selenium_user_agent})

    for cookie in driver.get_cookies():
        request_session.cookies.set(
            cookie["name"], cookie["value"], domain=cookie["domain"]
        )
