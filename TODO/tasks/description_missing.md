# description from scraped data

## current
* current content is flat text
* there should be no html that is part of work item component,
    however if there is html as content then this should be part of scrapped data

## should
* file description.md should contain content of description section of the work item
* formatting for description:
    * text indentation should be preserved
    * for indented text with bullet point use "*"
    * for indented numbered or lettered preserve numbers or letters
    * web links should fallow format [highlighted word](https://somewebsite.local) 
    * text with link to work item [highlighted word](<relative path>)
        * in case it is link to work item from different project [highlighted word](<relative path>),
            no need for validating path it is for reference only

