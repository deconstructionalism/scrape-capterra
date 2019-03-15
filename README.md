# Capterra Scraper Tool

This program can take a [Capterra](https://www.capterra.com/) category result and
extract all of the data from every platform reviewed within that result.

## Dependencies

- python `3.6+`
- Chrome browser (tested on `73.0.3683.75`)
- Chromedriver ([install instructions](http://chromedriver.chromium.org/getting-started))

## Installation

1. make sure you have all the dependencies installed
1. clone this repo
1. `cd` into repo in your terminal
1. run `pip install -r requirements.txt`

## Usage

1. use the Capterra site to select a category. Here is an 
   [example search result](https://www.capterra.com/learning-management-system-software/)
1. run `./scrape.py <category page path>`. Do not close or otherwise interact
   with the Chrome windows that automatically opened
1. once finished, the data will be saved in `scraped_data/data.json`
1. logs of each run are created in `logs/`