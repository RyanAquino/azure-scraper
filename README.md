# Scrap TFS

## TODO:
* scarp into files and folders, please find more details in tree.md

### Requirements
* Python 3
* [Ungoogled-Chromium Web Browser](https://ungoogled-software.github.io/ungoogled-chromium-binaries/)

### Setup
Navigate to source directory
```bash
cd src
```

Set Azure login credentials and replace Chromium binary path on `.env`
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

### Issues encountered
* Selenium was used instead of Scrapy to deal with the anti scrape security of Azure website
* Unable to find element since it is still loading
> Use implicit wait (Webdriver.Wait) to make sure element is present on the view and add try catch to handle elements which are not present on the page/dialog box
* `None` type error caused by unloaded data when scraping dialog box (usually happen after clicking the parent work item)
> Add wait time in sleep seconds before scraping the data
* Multiple dialog box will cause a reference error since there are multiple (ex. Element not attached to the page)
> Use the last() module of xpath to retrieve the upper element viewable.
* Site structure contains multiple duplicate classes which will return None or incorrect output 
> Use xpath to navigate the site structure
* http requests cannot be used to download attachments since we cannot authenticate the user via API
> Use driver.get to retrieve the attachments using Selenium browser which is already logged in
* Attachments are not downloading using driver.get() 
> Added `download=True` to the url parameter
* There are instances where child dialog box does not open because the tooltip on hover blocks the link to be clicked 
> added move to description element to remove the tooltip
* Hover actions maybe disrupted
> Avoid moving / clicking cursor when running the program
* Login may sometime fail due to timeout
> Retry. This is due to internet connection speed on loading the page
* Selecting sub elements using xpath might sometimes result to None
> Target the element in a more specific xpath hierarchy
* Hover not finding any value
> Implement retry every 5 sec until max retry or value has been found
