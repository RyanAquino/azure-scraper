import json
import os
import shutil
from datetime import datetime
from pathlib import Path

import config
from action_utils import add_line_break
from logger import logging


def create_history_metadata(history, file):
    for item in history:
        file.write(f"* Date: {item['Date']}\n")
        file.write(f"   * User: {item['User']}\n")
        file.write(f"   * Title: {item['Title']}\n")

        if item["Content"]:
            file.write(f"   * Content: {add_line_break(item['Content'], 60)}\n")

        if item["Fields"]:
            file.write(f"   * Fields\n")
            fields = item["Fields"]

            for index in range(0, len(fields)):
                field = fields[index]

                file.write(f"       * {field['name']}\n")
                file.write(f"           * Old Value: {field['old_value']}\n")
                file.write(f"           * New Value: {field['new_value']}\n")

        if links := item.get("Links"):
            for link in links:
                file.write(f"   * Links\n")
                file.write(f"       * Type: {link['Type']}\n")
                file.write(f"       * Link to item file: {link['Link to item file']}\n")
                file.write(f"       * Title: {link['Title']}\n")


def create_directory_hierarchy(
    dicts,
    path=os.path.join(os.getcwd(), "data"),
    attachments_path=(Path.cwd() / "data" / "attachments"),
    indent=0,
):
    exclude_fields = [
        "children",
        "related_work",
        "discussions",
        "history",
        "attachments",
    ]

    for d in dicts:
        dir_name = f"{d['Task id']}_{d['Title']}"
        dir_path = os.path.join(path, dir_name)
        discussion_path = os.path.join(dir_path, "discussion")
        development_path = os.path.join(dir_path, "development")
        work_item_attachments_path = os.path.join(dir_path, "attachments")
        discussion_attachments_path = os.path.join(discussion_path, "attachments")

        print(" " * indent + dir_name)
        logging.info(f"Creating directory in {dir_path}")
        os.makedirs(dir_path, exist_ok=True)
        os.makedirs(discussion_path, exist_ok=True)
        shutil.rmtree(discussion_path)
        os.makedirs(discussion_attachments_path, exist_ok=True)
        os.makedirs(development_path, exist_ok=True)
        os.makedirs(work_item_attachments_path, exist_ok=True)

        if "history" in d and d["history"]:
            with open(os.path.join(dir_path, "history.md"), "w") as file:
                create_history_metadata(d.pop("history"), file)

        if "discussions" in d and d["discussions"]:
            for discussion in d.pop("discussions"):
                discussion_date = datetime.strptime(
                    discussion["Date"], "%d %B %Y %H:%M:%S"
                )

                file_name = (
                    f"{discussion_date.strftime('%Y_%m_%d')}_{discussion['User']}.md"
                )
                with open(os.path.join(discussion_path, file_name), "a+") as file:
                    file.write(
                        f"* Title: <{discussion['User']} commented {discussion_date.strftime('%B %d, %Y %H:%m:%S %p')}>\n"
                    )
                    file.write(
                        f"* Content: {add_line_break(discussion['Content'], 90)}\n"
                    )

                if discussion["attachments"]:
                    for attachment in discussion["attachments"]:
                        source = os.path.join(attachments_path, attachment["filename"])
                        destination = os.path.join(
                            discussion_attachments_path, attachment["filename"]
                        )

                        if os.path.exists(source):
                            shutil.move(source, destination)

        if d.get("attachments"):
            for attachment in d["attachments"]:
                source = os.path.join(attachments_path, attachment["filename"])
                destination = os.path.join(
                    work_item_attachments_path, attachment["filename"]
                )

                if os.path.exists(source):
                    shutil.move(source, destination)

        with open(os.path.join(dir_path, "description.md"), "w") as file:
            if d["description"]:
                file.write(d.pop("description"))

        with open(os.path.join(dir_path, "metadata.md"), "w") as file:
            for key, value in d.items():
                if key not in exclude_fields:
                    file.write(f"* {key}: {value}\n")

        with open(os.path.join(dir_path, "origin.md"), "w") as file:
            file.write(config.BASE_URL + config.WORK_ITEM_ENDPOINT + d["Task id"])

        for development in d.pop("development"):
            with open(
                os.path.join(development_path, f"changeset_{development['ID']}.md"), "w"
            ) as file:
                if change_sets := development["change_sets"]:
                    for change_set in change_sets:
                        file.write(f"* 'File Name': {change_set['File Name']}\n")
                        file.write(f"* 'Path': {change_set['Path']}\n")
                        file.write(f"* 'Content': {change_set['content']}\n")

        if "children" in d:
            create_directory_hierarchy(d["children"], dir_path, indent=indent + 2)


def create_related_work_contents(scrape_results, path: Path = Path("data")):
    for item in scrape_results:
        task_id = item.get("Task id")
        task_title = item.get("Title")
        folder_name = f"{task_id}_{task_title}"
        dir_path = Path(path, folder_name)

        folder_path = [i for i in Path(Path.cwd() / path).resolve().rglob(folder_name)]

        with open(os.path.join(folder_path[0], "related_work.md"), "w") as file:
            for related_work in item.get("related_work"):
                related_work_type = related_work.get("type")
                related_work_data = {
                    "type": related_work_type,
                    "links to item file": [],
                }

                for work_items in related_work.get("related_work_items", []):
                    work_item_folder_name = work_items.get("link")
                    work_item_updated_at = work_items.get("updated_at")

                    work_item_path = [
                        i
                        for i in Path(Path.cwd() / "data")
                        .resolve()
                        .rglob(work_item_folder_name)
                    ]

                    if not work_item_path:
                        logging.error(work_items)
                        continue

                    work_item_path = work_item_path[0]
                    related_work_data["links to item file"].append(
                        {"link": work_item_path, "updated_at": work_item_updated_at}
                    )

                file.write(f"* Type: {related_work_type}\n")

                for links in related_work_data.get("links to item file"):
                    file.write(f"    * Link to item file: `{links.get('link')}`\n")
                    file.write(f"    * Last update: {links.get('updated_at')}\n\n")

        if "children" in item:
            create_related_work_contents(item["children"], dir_path)


def post_process_results(save_file, downloads_directory):
    with open(save_file) as f:
        scrape_result = json.load(f)
        create_directory_hierarchy(scrape_result)
        create_related_work_contents(scrape_result)

        # Clean downloads directory after post process
        shutil.rmtree(downloads_directory)