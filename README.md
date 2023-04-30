# Scrap TFS

## TODO:
* scarp into files and folders, please find more details in tree.md


### Issues
* Selenium was used instead of Scrapy to deal with the anti scrape security of Azure website

### Requirements
* Python 3
* [Google Chrome Web Browser](https://www.google.com/intl/en_ph/chrome/)
* [Google Chrome Web Driver](https://chromedriver.chromium.org/downloads)

### Setup
Make sure to download the correct chrome web driver and copy it to root directory 

Navigate to source directory
```bash
cd src
```

Set Azure login credentials on `config.py` 
```
EMAIL = ""
PASSWORD = ""
```

Install dependencies
```bash
pip install -r requirements.txt
```

Run scrape
```bash
python main.py 
```
