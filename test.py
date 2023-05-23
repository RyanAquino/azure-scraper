import json


def analyze_data(data):
    data_error = {
        "link_error_count": 0,
        "field_error_count": 0,
        "comment_error_count": 0,
    }

    for i in data:
        if history := i["history"]:
            for history_item in history:
                if "link" in history_item["Title"]:
                    if len(history_item["Links"]) == 0:
                        data_error["link_error_count"] += 1

                if "Changed" in history_item["Title"]:
                    if len(history_item["Fields"]) == 0:
                        data_error["field_error_count"] += 1

                if "comment" in history_item["Title"]:
                    if history_item["Content"] is None:
                        data_error["comment_error_count"] += 1
        if "children" in i:
            children = i.pop("children")
            analyze_data(children)
    return data_error


if __name__ == "__main__":
    save_file = "data/scrape_result.json"

    with open(save_file) as f:
        scrape_result = json.load(f)
        data_error = analyze_data(scrape_result)
        print(data_error)
