#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

import json
import logging
import os
import requests
import sys
from bs4 import BeautifulSoup
from datetime import datetime
from bin.capterra_scraper import PlatformPageScraper, PlatformReviewScraper


def set_up_logging(debug=False):
    '''
    Set up simultaneous logging to a log file and to stdout.
    '''

    # log to a file at DEBUG level in logs folder.
    logging.basicConfig(filename='./logs/{}-scrape.log'.format(datetime.now()),
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M',
                        level=logging.DEBUG,
                        filemode='w')

    # log the the stdout at INFO level as well.
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if debug else logging.INFO)
    logging.getLogger().addHandler(console)


def main(url):

    debug = False

    set_up_logging(debug)
    logging.info('set up logging (debug={})'.format(debug))

    # all_data = []
    base_url = 'https://www.capterra.com{}'

    # make the request
    r = requests.get(url)

    # exit if request fails
    if r.status_code != 200:
        sys.exit(1)

    # make a bs4 DOM tree
    dom = BeautifulSoup(r.text, 'html.parser')

    # find all the anchor tags in the DOM tree that link to reviews
    lms_buttons = dom.find_all('a', 'reviews-count')

    # get all the actual links from the anchor tags
    lms_links = [base_url.format(node['href']) for node in lms_buttons]

    buffer_file_path = os.path.join(os.getcwd(), 'scraped_data', '.extraction-buffer.tmp')
    output_file_path = os.path.join(os.getcwd(), 'scraped_data', 'data.json')

    for url in lms_links:
        logging.info('Extracting LMS data from {}'.format(url))
        lms_data = PlatformPageScraper(url, debug).data
        logging.info('Extracted data from {}\n'.format(lms_data['name']))

        with open(buffer_file_path, 'a') as cache_f:
            cache_f.write(json.dumps(lms_data))
            cache_f.write('# NEXT CHUNK #')

    with open(buffer_file_path, 'r') as cache_f:
        cached_data = cache_f.read().split('# NEXT CHUNK #')
        cached_data = filter(None, cached_data)
        all_data = [json.loads(lms_data) for lms_data in cached_data]

    with open(output_file_path, 'w') as output_f:
        output = json.dumps(all_data, indent=2)
        output_f.write(output)

    os.remove(buffer_file_path)

if __name__ == '__main__':
    # get capterra url input to scrape from command line
    if len(sys.argv) != 2:
        print('you must provide only one argument: the url to scrape!')
        sys.exit(1)
    url = sys.argv[1]
    main(url)
