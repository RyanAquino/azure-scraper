import json
import os
import shutil
from pathlib import Path

import config

from action_utils import add_line_break, convert_date, create_symlink
from logger import logging


def create_history_metadata(history, history_path):
    for item in history:
        formatted_date = convert_date(item["Date"], date_format="%a %d/%m/%Y %H:%M")
        title = item["Title"].replace(" ", "_")
        filename = f"{formatted_date}_{item['User']}_{title}.md"
        path = Path(history_path, filename)
        with open(path, "w", encoding="utf-8") as file:
            file.write(f"* Date: {item['Date']}\n")
            file.write(f"   * User: {item['User']}\n")
            file.write(f"   * Title: {item['Title']}\n")

            if item["Content"]:
                file.write(f"   * Content: {add_line_break(item['Content'], 60)}\n")

            if item["Fields"]:
                file.write("   * Fields\n")
                fields = item["Fields"]

                for field in fields:
                    file.write(f"       * {field['name']}\n")
                    file.write(f"           * Old Value: {field['old_value']}\n")
                    file.write(f"           * New Value: {field['new_value']}\n")

            if links := item.get("Links"):
                for link in links:
                    file.write("   * Links\n")
                    file.write(f"       * Type: {link['Type']}\n")
                    file.write(
                        f"       * Link to item file: {link['Link to item file']}\n"
                    )
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
        dir_name = f"{d['Task id']}_{d['Title'].replace(' ','_')}"
        dir_path = os.path.join(path, dir_name)
        history_path = os.path.join(dir_path, "history")
        discussion_path = os.path.join(dir_path, "discussion")
        development_path = os.path.join(dir_path, "development")
        work_item_attachments_path = os.path.join(dir_path, "attachments")
        discussion_attachments_path = os.path.join(discussion_path, "attachments")
        related_works_path = os.path.join(dir_path, "related")

        print(" " * indent + dir_name)
        logging.info(f"Creating directory in {dir_path}")
        os.makedirs(dir_path, exist_ok=True)
        os.makedirs(history_path, exist_ok=True)
        os.makedirs(discussion_path, exist_ok=True)
        shutil.rmtree(discussion_path)
        os.makedirs(discussion_attachments_path, exist_ok=True)
        os.makedirs(development_path, exist_ok=True)
        os.makedirs(work_item_attachments_path, exist_ok=True)
        os.makedirs(related_works_path, exist_ok=True)

        if "history" in d and d["history"]:
            create_history_metadata(d.pop("history"), history_path)

        if "discussions" in d and d["discussions"]:
            for discussion in d.pop("discussions"):
                # TODO: Move to scrape logic
                discussion_date = convert_date(discussion["Date"])
                file_name = f"{discussion_date}_{discussion['User']}.md"
                with open(os.path.join(discussion_path, file_name), "a+") as file:
                    file.write(
                        f"* Title: <{discussion['User']} commented {convert_date(discussion['Date'], new_format='%B %d, %Y %H:%m:%S %p')}>\n"
                    )
                    file.write(
                        f"* Content: {add_line_break(discussion['Content'], 90)}\n"
                    )

                    file.write("* Absolute link to attachment/s\n")

                    if discussion["attachments"]:
                        for attachment in discussion["attachments"]:
                            source = os.path.join(
                                attachments_path, attachment["filename"]
                            )

                            new_filename = f"{discussion_date}_{discussion['User']}_{attachment['filename']}"
                            destination = Path(
                                discussion_attachments_path, new_filename
                            )
                            file.write(f"  * [{new_filename}]({destination})\n")

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
        task_title = item.get("Title").replace(" ", "_")
        folder_name = f"{task_id}_{task_title}"
        dir_path = Path(path, folder_name)

        folder_path = [i for i in Path(Path.cwd() / path).resolve().rglob(folder_name)]
        related_dir = Path(folder_path[0] / "related")

        for related_work in item.get("related_work"):
            related_work_type = related_work.get("type")

            for work_items in related_work.get("related_work_items", []):
                work_item_folder_name = work_items.get("link")
                work_item_updated_at = convert_date(work_items.get("updated_at"))

                # TODO: Move to line 230 of scrape_utils.py
                link_work_item_file_name = f"{work_item_folder_name}_update_{work_item_updated_at}_{related_work_type}"
                target_path = Path(related_dir / link_work_item_file_name)

                work_item_path = [
                    i
                    for i in Path(Path.cwd() / "data")
                    .resolve()
                    .rglob(work_item_folder_name)
                ]

                if not work_item_path:
                    create_symlink("/non-existent/another-project-source", target_path)
                    continue

                work_item_path = work_item_path[0]
                create_symlink(work_item_path, target_path)

                with open(
                    Path(related_dir / f"{link_work_item_file_name}.md"), "w"
                ) as file:
                    file.write(f"* Type: {related_work_type}\n")
                    file.write(f"    * Link to item file: `{work_item_path}`\n")
                    file.write(f"    * Last update: {work_item_updated_at}\n\n")

        if "children" in item:
            create_related_work_contents(item["children"], dir_path)


def cleanup_existing_folders(directory: Path):
    for item in directory.iterdir():
        item_path = directory / item

        if os.path.islink(item_path):
            os.unlink(item_path)

        if item.is_dir() and item.name != "attachments":
            shutil.rmtree(item_path)


def post_process_results(save_file, downloads_directory):
    with open(save_file) as f:
        scrape_result = json.load(f)
        cleanup_existing_folders((Path.cwd() / "data"))
        create_directory_hierarchy(scrape_result)
        create_related_work_contents(scrape_result)

        # Clean downloads directory after post process
        if downloads_directory.exists() and downloads_directory.is_dir():
            shutil.rmtree(downloads_directory)
