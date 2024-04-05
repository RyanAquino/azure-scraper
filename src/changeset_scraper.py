import os
import shutil
import time
from pathlib import Path
from zipfile import ZipFile

from selenium import webdriver

import config
from action_utils import find_element_by_xpath, find_elements_by_xpath
from driver_utils import chrome_settings_init
from main import login


def download_changeset(driver):
    browse_files = find_element_by_xpath(driver, "//a[@id='__bolt-browse-files']")
    driver.execute_script("arguments[0].click();", browse_files)

    more_act = find_element_by_xpath(driver, "//button[@aria-label='More actions']")
    driver.execute_script("arguments[0].click();", more_act)

    download_btn = find_element_by_xpath(driver, "//div[@id='__bolt-download-text']")
    driver.execute_script("arguments[0].click();", download_btn)


def wait_for_download(chrome_downloads, downloaded_ctr):
    files = list(chrome_downloads.iterdir())

    while len(files) != downloaded_ctr:
        print("Waiting for download to finish...")
        files = list(chrome_downloads.iterdir())

        if not files:
            time.sleep(2)
            continue

        latest_file = Path(
            chrome_downloads, max(files, key=lambda f: f.stat().st_mtime)
        )

        while "crdownload" in latest_file.name:
            files = list(chrome_downloads.iterdir())
            latest_file = Path(
                chrome_downloads, max(files, key=lambda f: f.stat().st_mtime)
            )
            time.sleep(1)
        time.sleep(2)
    else:
        print("File downloaded")

    return files


def get_changeset_urls(driver):
    changeset_body = find_element_by_xpath(driver, "//tbody")
    changesets = find_elements_by_xpath(changeset_body, "a")
    changeset_urls = []

    for changeset in changesets:
        changeset_urls.append(changeset.get_attribute("href"))

    changeset_urls.reverse()

    return changeset_urls


def scrape_changeset(driver, changeset_downloads):
    files = list(changeset_downloads.iterdir())
    downloaded_ctr = len(files) + 1
    changeset_urls = get_changeset_urls(driver)

    for changeset_url in changeset_urls:
        driver.get(changeset_url)
        download_changeset(driver)
        files = wait_for_download(changeset_downloads, downloaded_ctr)
        latest_file = Path(
            changeset_downloads, max(files, key=lambda f: f.stat().st_mtime)
        )

        with ZipFile(latest_file, "r") as zObject:
            zObject.extractall(path=Path(latest_file.parent.parent, "changesets"))

        os.remove(latest_file)


def main():
    chrome_config, _ = chrome_settings_init()
    changeset_downloads = f"{Path.cwd()}/changesets_download"
    os.makedirs(changeset_downloads, exist_ok=True)
    chrome_config.get("options").experimental_options["prefs"][
        "download.default_directory"
    ] = changeset_downloads

    with webdriver.Chrome(**chrome_config) as driver:
        login(driver, config.CHANGESET_URL, config.EMAIL, config.PASSWORD)
        time.sleep(5)
        scrape_changeset(driver, Path(changeset_downloads))
        shutil.rmtree(Path(changeset_downloads), ignore_errors=True)


if __name__ == "__main__":
    main()
