# Scrap TFS

## TODO:
* scarp into files and folders, please find more details in tree.md


### Issues
* Selenium was used instead of Scrapy to deal with the anti scrape security of Azure website

### Requirements
* Python 3
* Google Chrome

### Setup
Set login credentials on `config.py` 
```
URL = ""
EMAIL = ""
PASSWORD = ""
```

Navigate to virtual environment and install dependencies
```bash
pip install -r requirements.txt
```

Run scrape
```bash
python selenium_scrape.py 
```
