import json
import os
import random
import shutil
import string
from pathlib import Path
from urllib.parse import urlparse

import config
from action_utils import add_line_break, convert_date, create_symlink, validate_title
from logger import logging


def create_history_metadata(history, history_path, attachments_path, msg_clip_size):
    characters = string.ascii_letters + string.digits

    for item in history:
        uuid_randomizer = "".join(random.choices(characters, k=2))
        formatted_date = convert_date(item["Date"], date_format="%a %d/%m/%Y %H:%M")
        title = validate_title(item["Title"])
        title = title[: msg_clip_size] if msg_clip_size else title
        user = "_".join(item["User"].split(" "))
        filename = f"{formatted_date}_{uuid_randomizer}_{user}_{title}.md"
        path = Path(history_path, filename)

        history_attachments_path = Path(history_path, "attachments")
        history_contents_path = Path(history_path, "contents")
        history_deleted_attachments_path = Path(history_path, "removed_attachments")
        os.makedirs(history_attachments_path, exist_ok=True)
        os.makedirs(history_contents_path, exist_ok=True)
        os.makedirs(history_deleted_attachments_path, exist_ok=True)

        with open(path, "w", encoding="utf-8") as file:
            file.write(f"* Date: {item['Date']}\n")
            file.write(f"   * User: {item['User']}\n")
            file.write(f"   * Title: {item['Title']}\n")

            if item["Fields"]:
                file.write("   * Fields\n")
                fields = item["Fields"]

                for field in fields:
                    file.write(f"       * {field['name']}\n")
                    file.write(f"           * Old Value: {field['old_value']}\n")
                    file.write(f"           * New Value: {field['new_value']}\n")

                    if raw_old_val := field.get("raw_old_value"):
                        with open(
                            Path(
                                history_contents_path, f"{path.stem}_old{path.suffix}"
                            ),
                            "w",
                            encoding="utf-8",
                        ) as raw_file:
                            raw_file.write(raw_old_val)

                    if raw_new_val := field.get("raw_new_value"):
                        with open(
                            Path(
                                history_contents_path, f"{path.stem}_new{path.suffix}"
                            ),
                            "w",
                            encoding="utf-8",
                        ) as raw_file:
                            raw_file.write(raw_new_val)

                    if old_atts := field.get("old_attachments"):
                        file.write(f"           * Old Attachments\n")
                        for old_att in old_atts:
                            att_file_name = old_att["File Name"]
                            source = Path(attachments_path, att_file_name)
                            destination = Path(
                                history_deleted_attachments_path, att_file_name
                            )
                            file.write(
                                f"               * File Name: {old_att['File Name']}\n"
                            )
                            file.write(
                                f"               * Absolute link to attachment:  [{att_file_name}]({destination})\n"
                            )
                            if os.path.exists(source):
                                shutil.copy(source, destination)

                    if new_atts := field.get("new_attachments"):
                        file.write(f"           * New Attachments\n")
                        for new_att in new_atts:
                            att_file_name = new_att["File Name"]
                            source = Path(attachments_path, att_file_name)
                            destination = Path(history_attachments_path, att_file_name)
                            file.write(f"               * File Name: {att_file_name}\n")
                            file.write(
                                f"               * Absolute link to attachment:  [{att_file_name}]({destination})\n"
                            )

                            if os.path.exists(source):
                                shutil.copy(source, destination)

            if links := item.get("Links"):
                for link in links:
                    file.write("   * Links\n")
                    file.write(f"       * Type: {link['Type']}\n")
                    file.write(f"       * Change Type: {link['Change Type']}\n")
                    file.write(
                        f"       * Link to item file: {link['Link to item file']}\n"
                    )
                    file.write(f"       * Title: {link['Title']}\n")

            if attachments := item.get("Attachments"):
                for attachment in attachments:
                    file.write("   * Attachment\n")
                    file.write(f"       * Change Type: {attachment['Change Type']}\n")
                    file.write(f"       * File Name: {attachment['File Name']}\n")


def create_directory_hierarchy(
    dicts,
    msg_clip_size,
    attachments_path=(Path(Path.cwd(), "data", "attachments")),
    indent=0,
):
    exclude_fields = [
        "children",
        "related_work",
        "discussions",
        "history",
        "attachments",
        "development",
        "img_description",
        "Source Description",
    ]

    for d in dicts:
        title = validate_title(d["Title"])
        title = title[: msg_clip_size] if msg_clip_size else title
        dir_name = f"{d['Task id']}_{title}"
        d["dir_name"] = dir_name
        dir_path = Path(dir_name)

        print(" " * indent + dir_name)
        logging.info(f"Creating directory in {dir_path}")
        os.makedirs(dir_path, exist_ok=True)
        os.chdir(dir_path)

        history_path = Path("history")
        discussion_path = Path("discussion")
        discussion_contents_path = Path(discussion_path, "contents")
        development_path = Path("development")
        work_item_attachments_path = Path("attachments")
        discussion_attachments_path = Path(discussion_path, "attachments")
        related_works_path = Path("related")
        work_item_img_description_path = Path("img_description")

        os.makedirs(history_path, exist_ok=True)
        os.makedirs(discussion_path, exist_ok=True)
        os.makedirs(discussion_contents_path, exist_ok=True)
        os.makedirs(discussion_attachments_path, exist_ok=True)
        os.makedirs(development_path, exist_ok=True)
        os.makedirs(work_item_attachments_path, exist_ok=True)
        os.makedirs(related_works_path, exist_ok=True)
        os.makedirs(work_item_img_description_path, exist_ok=True)

        if "history" in d and d["history"]:
            create_history_metadata(d.pop("history"), history_path, attachments_path, msg_clip_size)

        if "discussions" in d and d["discussions"]:
            for discussion in d.pop("discussions"):
                user = "_".join(discussion["User"].split(" "))
                file_name = f'{discussion["Date"]}_{user}.md'
                new_date = discussion["Date"]

                with open(
                    Path(discussion_path, f"source_discussion_{file_name}"),
                    "w",
                    encoding="utf-8",
                ) as file:
                    file.write(discussion["Source Content"])

                with open(
                    Path(discussion_contents_path, file_name), "a+", encoding="utf-8"
                ) as file:
                    file.write(
                        f"* Title: <{discussion['User']} commented {new_date}>\n"
                    )
                    file.write(
                        f"* Content: {add_line_break(discussion['Content'], 90)}\n"
                    )

                    file.write("* Absolute link to attachment/s\n")

                    if discussion["attachments"]:
                        for attachment in discussion["attachments"]:
                            source = Path(attachments_path, attachment["filename"])
                            destination = Path(
                                discussion_attachments_path, attachment["filename"]
                            )
                            file.write(
                                f"  * [{attachment['filename']}]({destination})\n"
                            )
                            logging.info(
                                f"Discussion Attachment: {attachment['filename']}"
                            )

                            if os.path.exists(source):
                                shutil.copy(source, destination)

        if d.get("attachments"):
            for attachment in d["attachments"]:
                source = Path(attachments_path, attachment["filename"])
                destination = Path(work_item_attachments_path, attachment["filename"])
                logging.info(f"Attachment: {attachment['filename']}")

                if os.path.exists(source):
                    shutil.copy(source, destination)

        if d.get("img_description"):
            for attachment in d["img_description"]:
                source = Path(attachments_path, attachment["filename"])
                destination = Path(
                    work_item_img_description_path, attachment["filename"]
                )
                logging.info(f"Image description Attachment: {attachment['filename']}")

                if os.path.exists(source):
                    shutil.copy(source, destination)

        with open(Path("description.md"), "w", encoding="utf-8") as file:
            if d["description"]:
                file.write(str(d.pop("description")))

        with open(Path("metadata.md"), "w", encoding="utf-8") as file:
            for key, value in d.items():
                if key not in exclude_fields:
                    file.write(f"* {key}: {value}\n")

        with open(Path("source_description.md"), "w", encoding="utf-8") as file:
            file.write(d["Source Description"])

        with open(Path("origin.md"), "w", encoding="utf-8") as file:
            scheme, domain, url_path = urlparse(config.BASE_URL)[0:3]
            url_path = "/".join(url_path.split("/")[1:3])
            origin = f"{scheme}://{domain}/{url_path}/_workitems/edit/{d['Task id']}"
            file.write(origin)

        for development in d.pop("development"):
            file_name = f"changeset_{development['ID']}"
            change_filename = Path(development_path, f"{file_name}.md")
            with open(change_filename, "w", encoding="utf-8") as file:
                if change_sets := development["change_sets"]:
                    for change_set in change_sets:
                        file.write(f"* 'File Name': {change_set['File Name']}\n")
                        file.write(f"* 'Path': {change_set['Path']}\n")

        if "children" in d:
            create_directory_hierarchy(d["children"], msg_clip_size, indent=indent + 2)

        os.chdir("..")


def clipped_related_work_title(related_work, msg_clip_size):
    work_item_target = related_work.get("link_target")
    work_item_file_name = related_work.get("filename_source", "")

    if msg_clip_size:
        work_item_id, work_item_target_name, *_ = work_item_file_name.split("_", 1)
        work_item_file_name = (
            f"{work_item_id}_{work_item_target_name[:msg_clip_size]}"
        )

        work_item_id, work_item_target_name, substring = work_item_target.split("_", 2)
        work_item_target = (
            f"{work_item_id}_{work_item_target_name[:msg_clip_size]}_{substring}"
        )

    return work_item_target, work_item_file_name


def create_related_work_contents(scrape_results, main_data_path: Path, msg_clip_size):
    for item in scrape_results:
        folder_name = item["dir_name"]
        os.chdir(folder_name)
        related_dir = Path("related")

        for related_work in item.get("related_work"):
            related_work_type = related_work.get("type")

            for work_items in related_work.get("related_work_items", []):
                project_url = work_items.get("url")
                work_item_target, work_item_file_name = clipped_related_work_title(
                    work_items, msg_clip_size
                )
                work_item_updated_at = convert_date(work_items.get("updated_at"))
                target_path = Path(related_dir, work_item_target)
                work_item_path = [i for i in main_data_path.rglob(work_item_file_name)]

                # Another project
                if not work_item_path:
                    with open(
                        Path(related_dir, f"{work_item_target}.md"),
                        "w",
                        encoding="utf-8",
                    ) as file:
                        file.write(f"origin: {project_url}")
                    continue

                work_item_path = work_item_path[0]
                if os.path.exists(target_path):
                    logging.info(f"Skipping existing related work: {target_path}")
                    continue
                create_symlink(work_item_path, target_path)

                related_md_filename = Path(related_dir, f"{work_item_target}.md")
                with open(related_md_filename, "w", encoding="utf-8") as file:
                    file.write(f"* Type: {related_work_type}\n")
                    file.write(f"    * Link to item file: `{work_item_path}`\n")
                    file.write(f"    * Last update: {work_item_updated_at}\n\n")

        if "children" in item:
            create_related_work_contents(item["children"], main_data_path, msg_clip_size)

        os.chdir("..")


def cleanup_existing_folders():
    for item in Path.cwd().iterdir():
        item_path = item

        if os.path.islink(item_path):
            os.unlink(item_path)

        if item.is_dir() and item.name != "attachments":
            shutil.rmtree(item_path)


def post_process_results(save_file, downloads_directory, src_directory, msg_clip_size=os.pathconf("/", 'PC_NAME_MAX')):
    os.chdir(src_directory)
    data_folder = Path("data")

    try:
        with open(save_file, "r", encoding="utf-8") as file:
            scrape_result = json.load(file)
            os.makedirs(data_folder, exist_ok=True)
            os.chdir(data_folder)
            cleanup_existing_folders()
            create_directory_hierarchy(scrape_result, msg_clip_size)
            create_related_work_contents(scrape_result, data_folder, msg_clip_size=msg_clip_size)
            os.chdir("..")

            # Clean downloads directory after post process
            if downloads_directory.exists() and downloads_directory.is_dir():
                shutil.rmtree(downloads_directory)

    except OSError as e:
        if e.args[1] == "File name too long":
            os.chdir("..")
            print(f"Retrying folder creation on clip size: {msg_clip_size - 10}")
            post_process_results(save_file, downloads_directory, src_directory, msg_clip_size - 10)
            return
        print(f"Exception: {str(e)}")

