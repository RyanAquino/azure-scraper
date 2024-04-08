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


def download_changeset(driver, changeset_downloads):
    browse_files = find_element_by_xpath(driver, "//a[@id='__bolt-browse-files']")
    driver.execute_script("arguments[0].click();", browse_files)

    more_act = find_element_by_xpath(driver, "//button[@aria-label='More actions']")
    driver.execute_script("arguments[0].click();", more_act)

    download_btn = find_element_by_xpath(driver, "//div[@id='__bolt-download-text']")
    driver.execute_script("arguments[0].click();", download_btn)

    return wait_for_download(changeset_downloads)


def wait_for_download(chrome_downloads):
    files = [
        file for file in chrome_downloads.iterdir() if not file.name.startswith(".")
    ]
    latest_file = None
    print("Initial", files)

    if files:
        latest_file = Path(files[0])

    while len(files) != 1 or (latest_file and "crdownload" in latest_file.name):
        print("Waiting for download to finish...")
        files = [
            file for file in chrome_downloads.iterdir() if not file.name.startswith(".")
        ]
        print("While ", files)

        if not files:
            time.sleep(2)
            continue

        latest_file = Path(
            chrome_downloads, max(files, key=lambda f: f.stat().st_mtime)
        )
        print(latest_file.name)
        time.sleep(2)
    else:
        print("File downloaded")

    print("Downloads ", os.listdir(chrome_downloads))
    latest_file = Path(chrome_downloads, max(files, key=lambda f: f.stat().st_mtime))

    return latest_file


def get_all_changeset_urls(driver):
    changeset_urls = get_changeset_urls(driver)

    scroll_increment = 250
    content_container = find_element_by_xpath(driver, "//div[@role='main']/div")
    content_height = driver.execute_script(
        "return arguments[0].scrollHeight;", content_container
    )
    scroll_init = 0

    while scroll_init <= content_height + (scroll_increment * 2):
        driver.execute_script(
            "arguments[0].scrollTop += arguments[1];",
            content_container,
            scroll_increment,
        )

        # Wait to load page
        time.sleep(0.5)

        # Get urls
        changeset_body = find_element_by_xpath(driver, "//tbody")
        changesets = find_elements_by_xpath(changeset_body, "a")

        for changeset in changesets:
            changeset_url = changeset.get_attribute("href")
            if changeset_url not in changeset_urls:
                changeset_urls.append(changeset_url)

        scroll_init += scroll_increment

    return changeset_urls


def get_changeset_urls(driver):
    try:
        changeset_body = find_element_by_xpath(driver, "//tbody")
        changesets = find_elements_by_xpath(changeset_body, "a")
        changeset_urls = []

        for changeset in changesets:
            changeset_urls.append(changeset.get_attribute("href"))

        return changeset_urls

    except Exception as e:
        print("Retrying...")
        return get_changeset_urls(driver)


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
    changeset_urls = get_all_changeset_urls(driver)
    print("Changeset URLs ", len(changeset_urls))

    for changeset_url in changeset_urls:
        print("Scraping ", changeset_url)
        driver.get(changeset_url)
        _id = changeset_url.split("/")[-2]

        valid_file_paths = get_valid_paths(driver)
        latest_file = download_changeset(driver, changeset_downloads)
        extract_path = clean_extract(latest_file, _id)
        validate_files(valid_file_paths, extract_path, latest_file.stem)


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
