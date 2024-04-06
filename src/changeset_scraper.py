import glob
import os
import re
import shutil
import time
import traceback
from pathlib import Path
from zipfile import ZipFile

from selenium import webdriver

import config
from action_utils import find_element_by_xpath, find_elements_by_xpath, get_text
from driver_utils import chrome_settings_init
from main import login


def download_changeset(driver, changeset_downloads, downloaded_ctr):
    browse_files = find_element_by_xpath(driver, "//a[@id='__bolt-browse-files']")
    driver.execute_script("arguments[0].click();", browse_files)

    more_act = find_element_by_xpath(driver, "//button[@aria-label='More actions']")
    driver.execute_script("arguments[0].click();", more_act)

    download_btn = find_element_by_xpath(driver, "//div[@id='__bolt-download-text']")
    driver.execute_script("arguments[0].click();", download_btn)

    return wait_for_download(changeset_downloads, downloaded_ctr)


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

    latest_file = Path(chrome_downloads, max(files, key=lambda f: f.stat().st_mtime))

    return latest_file


def get_changeset_urls(driver):
    changeset_body = find_element_by_xpath(driver, "//tbody")
    changesets = find_elements_by_xpath(changeset_body, "a")
    changeset_urls = []

    for changeset in changesets:
        changeset_urls.append(changeset.get_attribute("href"))

    changeset_urls.reverse()

    return changeset_urls


def get_valid_paths(driver):
    files_changed = find_elements_by_xpath(driver, "//tr[@role='treeitem']") or []
    valid_file_paths = set()

    for file in files_changed:
        driver.execute_script("arguments[0].click();", file)
        path = find_element_by_xpath(
            driver, "//span[@role='heading']/parent::span/following-sibling::span"
        )

        header_xpath = "//span[@role='heading']"
        file_name = get_text(driver, header_xpath)

        pattern = r"^\d+ changed files?$"
        match = re.match(pattern, file_name)

        if not path or match:
            continue

        path = "/".join(path.text.split("/")[1:])
        valid_file_paths.add(Path(path))

    return valid_file_paths


def clean_extract(latest_file, _id):
    print("Extracting ", latest_file)
    extract_path = Path(latest_file.parent.parent, "changesets", _id)
    with ZipFile(latest_file, "r") as zObject:
        zObject.extractall(path=extract_path)

    os.remove(latest_file)

    return extract_path


def scrape_changeset(driver, changeset_downloads):
    files = list(changeset_downloads.iterdir())
    downloaded_ctr = len(files) + 1
    changeset_urls = get_changeset_urls(driver)
    print(changeset_urls)

    for changeset_url in changeset_urls:
        print("Scraping ", changeset_url)
        driver.get(changeset_url)
        _id = changeset_url.split("/")[-2]

        valid_file_paths = get_valid_paths(driver)
        latest_file = download_changeset(driver, changeset_downloads, downloaded_ctr)
        extract_path = clean_extract(latest_file, _id)
        validate_files(valid_file_paths, extract_path, latest_file.stem)
        shutil.rmtree(latest_file.stem, ignore_errors=True)


def validate_files(valid_file_paths, extract_path, downloaded_file_name):
    downloaded_directory = Path(extract_path, downloaded_file_name)
    valid_file_paths = {f"{extract_path}/{file_path}" for file_path in valid_file_paths}

    for filename in glob.iglob(f"{downloaded_directory}/**", recursive=True):
        if not os.path.isfile(filename):
            continue

        if filename not in valid_file_paths:
            os.remove(filename)

    delete_empty_folders(downloaded_directory, valid_file_paths)


def delete_empty_folders(path, valid_file_paths):
    for folder in glob.glob(os.path.join(path, "*")):
        if os.path.isdir(folder):
            delete_empty_folders(folder, valid_file_paths)

    dir_path = os.listdir(path)
    if not dir_path and valid_file_paths and path not in valid_file_paths:
        os.rmdir(path)


def init_chrome_config():
    chrome_config, _ = chrome_settings_init()
    changeset_downloads = f"{Path.cwd()}/changesets_download"
    os.makedirs(changeset_downloads, exist_ok=True)
    chrome_config.get("options").experimental_options["prefs"][
        "download.default_directory"
    ] = changeset_downloads

    return chrome_config, changeset_downloads


def main():
    chrome_config, changeset_downloads = init_chrome_config()

    try:
        with webdriver.Chrome(**chrome_config) as driver:
            login(driver, config.CHANGESET_URL, config.EMAIL, config.PASSWORD)
            time.sleep(5)
            scrape_changeset(driver, Path(changeset_downloads))
    except Exception as e:
        print(str(e))
        print(traceback.format_exc())
    finally:
        shutil.rmtree(Path(changeset_downloads), ignore_errors=True)


if __name__ == "__main__":
    main()
