#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

import json
import logging
import re
import requests
import sys
from bs4 import BeautifulSoup
from datetime import datetime
from selenium_get_more import get_all

LMS_DATA = []


def set_up_logging():
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
    console.setLevel(logging.INFO)
    logging.getLogger().addHandler(console)


def fault_tolerant(func):
    '''
    Decorator that allows functions to keep running on Exceptions, and logs
    Exception info. In case of an Exception, the wrapped function returns None.
    '''

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # extract error data from the Exception and log it in a nice format.
            error = {
                'line_number': sys.exc_info()[-1].tb_lineno,
                'name': e.__class__.__name__,
                'msg': str(e)
            }
            log_text = '{name} on line {line_number}: {msg}'.format(**error)
            logging.error(log_text)

            # it is important for some functions that to receive a value on
            # Exception to indicate inability to extract data. You can change
            # that value to anything you want here.
            return None

    return wrapper


class CapterraScraper:

    @staticmethod
    @fault_tolerant
    def find_element_sibling(dom, element, element_text, next_type):
        nodes = dom.find_all(element)    
        node = list(filter(lambda x: element_text in x.get_text(), nodes))[0]
        return node.find_next(next_type)

    @staticmethod
    @fault_tolerant
    def clean_up_text(text):
        text = [i.strip() for i in text.split('\n')]
        text = list(filter(None, text))
        text = ', '.join(text)
        text = text.replace(', /, ', '/')
        return text

    @fault_tolerant
    def consume_list(self, ul, reverse_key_val=False):

        data = {}

        list_items = ul.select('li > *')
        for item in list_items:
            pairs = item.find_all(recursive=False)
            key = self.clean_up_text(pairs[1].get_text())
            val = self.clean_up_text(pairs[0].get_text())
            if reverse_key_val:
                key, val = val, key
            data[key] = val

        return data


class PlatformPage(CapterraScraper):
    def __init__(self, url, debug=True):
        self.url = url
        self.debug = debug
        self.page_source = None
        self.dom = None
        self.data = {}

        self.scrape_data()

    def scrape_data(self):
        self.get_full_page_data()
        self.data['name'] = self.extract_name()
        self.data['ratings'] = self.extract_ratings()
        self.data['product_details'] = self.extract_product_details()
        self.data['vendor_details'] = self.extract_vendor_details()
        self.data['features'] = self.extract_features()
        self.data['about'] = self.extract_about()

    def get_full_page_data(self):
        self.page_source = get_all(self.url, self.debug)
        self.dom = BeautifulSoup(self.page_source, 'html.parser')

    @fault_tolerant
    def extract_name(self):
        return self.dom.find_all('li', 'ss-navigateright')[-1].text

    @fault_tolerant
    def extract_ratings(self):
        node = self.find_element_sibling(self.dom, 'h2', 'Average Ratings', 'ul')
        return self.consume_list(node)

    @fault_tolerant
    def extract_product_details(self):
        node = self.find_element_sibling(self.dom, 'h2', 'Product Details', 'ul')
        return self.consume_list(node, True)

    @fault_tolerant
    def extract_vendor_details(self):
        node = self.find_element_sibling(self.dom, 'h2', 'Vendor Details', 'ul')
        return [li.text for li in node.find_all('li')]

    @fault_tolerant
    def extract_about(self):
        node = self.find_element_sibling(self.dom, 'h2', 'About', 'div')
        return self.clean_up_text(node.get_text())

    @fault_tolerant
    def extract_features(self):

        data = {}
        feature_lists = dom.select('.category-features-list')

        @fault_tolerant
        def extract_feature(feature_list):
            feature_list_items = feature_list.find_all('li', 'ss-check')
            features = [node.text for node in feature_list_items]
            keys = list(filter(None, features))
            values = ['feature-disabled' not in node.get('class') for node in feature_list_items]
            return dict(zip(keys, values))

        for feature_list in feature_lists:
            key = self.clean_up_text(feature_list.find('h4').text)
            values = extract_feature(feature_list)
            data[key] = values

        return data


def get_all_reviews(dom):

    reviews = []
    
    def get_likelihood_reccomendation(review):
        try:
            return review.select('.gauge-svg-image')[0]['alt']
        except:
            return None

    def get_ratings(review):

        ratings = {}

        rating_types = [
            'overall',
            'ease-of-use',
            'features',
            'customer-service',
            'value'
        ]
        for rating in rating_types:
            try:
                if rating == 'overall':
                    selector = '.overall-rating'
                else:
                    selector = '.rating-{}'.format(rating)
                node = review.select(selector)[0]
                ratings[rating] = clean_up_text(node.get_text())
            except:
                ratings[rating] = None

        return ratings

    def get_reactions(review):
        data = {}

        reactions = review.select('.review-comments > p')
        for reaction in reactions:
            reaction_type = reaction.find_all(recursive=False)[0].text.replace(':', '')
            reaction_data = reaction.find(text=True, recursive=False)
            data[reaction_type] = reaction_data

        return data

    def get_title(review):
        try:
            return review.select('q')[0].text
        except:
            return True

    def get_user_data(review):
        # did not implement
        return None

    review_nodes = dom.select('.cell-review')
    for review in review_nodes:

        review_data = {}

        review_data['likelihood_reccomendation'] = get_likelihood_reccomendation(review)
        review_data['ratings'] = get_ratings(review)
        review_data['reactions'] = get_reactions(review)
        review_data['title'] = get_title(review)

        reviews.append(review_data)

    return reviews


def parse_lms_data(url):

    lms_data = {}

    # get full source of page including "more" paging using selenium
    full_source = get_all(url, True)

    # make a bs4 DOM tree
    dom = BeautifulSoup(full_source, 'html.parser')

    # # make the request
    # r = requests.get(url)

    # # exit if request fails
    # if r.status_code != 200:
    #     print('could not get from {}'.format(url))
    #     return

    # # make a bs4 DOM tree
    # dom = BeautifulSoup(r.text, 'html.parser')

    lms_data['number_reviews'] = get_number_reviews(dom)
    lms_data['name'] = get_name(dom)
    lms_data['ratings'] = get_ratings(dom)
    lms_data['product_details'] = get_product_details(dom)
    lms_data['vendor_details'] = get_vendor_details(dom)
    lms_data['features'] = get_all_features(dom)
    lms_data['about'] = get_about(dom)
    lms_data['reviews'] = get_all_reviews(dom)

    return lms_data


def main():

    set_up_logging()

    all_data = []

    # get capterra url input to scrape from command line
    if len(sys.argv) != 2:
        print('you must provide only one argument: the url to scrape!')
        sys.exit(1)
    results_url = sys.argv[1]

    base_url = 'https://www.capterra.com{}'

    # make the request
    r = requests.get(results_url)

    # exit if request fails
    if r.status_code != 200:
        sys.exit(1)

    # make a bs4 DOM tree
    dom = BeautifulSoup(r.text, 'html.parser')

    # find all the anchor tags in the DOM tree that link to reviews
    lms_buttons = dom.find_all('a', 'reviews-count')

    # get all the actual links from the anchor tags
    lms_links = [base_url.format(node['href']) for node in lms_buttons]

    # for url in lms_links:
    #     lms_data = parse_lms_data(url)
    #     print('parsed {}\n'.format(lms_data['name']))
    #     all_data.append(lms_data)
    
    # output = json.dumps(all_data, indent=2)
    # with open('ouput.json', 'w') as f:
    #     f.write(output)

    for url in lms_links:
        l = PlatformPage(url)
        print(l.data)
        break

if __name__ == '__main__':
    main()