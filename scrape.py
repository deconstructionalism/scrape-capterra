#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import requests
import sys
import json
import re
from selenium_get_more import get_all

LMS_DATA = []

'''
{
    name: String,
    number_reviews: Integer,
    ratings: {
        overall: Integer,
        ease_of_use: Integer,
        customer_service: Integer
    },
    product_details: {
        [detail]: Array of Strings
    },
    vendor_details: {
        [detail]: String
    },
    features: [{
        [feature_type]: {
            [feature]: Boolean
        }
    }]
}
'''


def get_name(dom):
    return dom.find_all('li', 'ss-navigateright')[-1].text


def get_number_reviews(dom):
    return dom.find('a', 'reviews-count').span.text


def get_ratings(dom):
    node = find_element_sibling(dom, 'h2', 'Average Ratings', 'ul')
    return consume_list(node)


def get_product_details(dom):
    node = find_element_sibling(dom, 'h2', 'Product Details', 'ul')
    return consume_list(node, True)


def get_vendor_details(dom):
    node = find_element_sibling(dom, 'h2', 'Vendor Details', 'ul')
    return [li.text for li in node.find_all('li')]


def get_about(dom):
    node = find_element_sibling(dom, 'h2', 'About', 'div')
    return clean_up_text(node.get_text())


def find_element_sibling(dom, element, element_text, next_type):
    nodes = dom.find_all(element)    
    node = list(filter(lambda x: element_text in x.get_text(), nodes))[0]
    return node.find_next(next_type)


def clean_up_text(text):
    text = [i.strip() for i in text.split('\n')]
    text = list(filter(None, text))
    text = ', '.join(text)
    text = text.replace(', /, ', '/')
    return text


def consume_list(ul, reverse_key_val=False):

    data = {}

    list_items = ul.select('li > *')
    for item in list_items:
        pairs = item.find_all(recursive=False)
        key = clean_up_text(pairs[1].get_text())
        val = clean_up_text(pairs[0].get_text())
        if reverse_key_val:
            key, val = val, key
        data[key] = val

    return data


def get_all_features(dom):

    data = {}
    feature_lists = dom.select('.category-features-list')

    def get_features(feature_list):
        feature_list_items = feature_list.find_all('li', 'ss-check')
        features = [node.text for node in feature_list_items]
        keys = list(filter(None, features))
        vals = ['feature-disabled' not in node.get('class') for node in feature_list_items]
        return dict(zip(keys, vals))

    for feature_list in feature_lists:
        key = clean_up_text(feature_list.find('h4').text)
        vals = get_features(feature_list)
        data[key] = vals

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

    for link in lms_links:
        lms_data = parse_lms_data(link)
        print('parsed {}\n'.format(lms_data['name']))
        all_data.append(lms_data)
    
    output = json.dumps(all_data, indent=2)
    with open('ouput.json', 'w') as f:
        f.write(output)

if __name__ == '__main__':
    main()