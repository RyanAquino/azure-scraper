# Scrap TFS

## TODO:
* scarp into files and folders, please find more details in tree.md


### Issues
* Selenium was used instead of Scrapy to deal with the anti scrape security of Azure website

### Requirements
* Python 3
* [Ungoogled-Chromium Web Browser](https://ungoogled-software.github.io/ungoogled-chromium-binaries/)

### Setup
Navigate to source directory
```bash
cd src
```

Set Azure login credentials and replace Chromium binary path on `config.py`
```
EMAIL = ""
PASSWORD = ""
BINARY_PATH_LOCATION = ""
```

Install dependencies
```bash
pip install -r requirements.txt
```

Run scrape
```bash
python main.py 
```
