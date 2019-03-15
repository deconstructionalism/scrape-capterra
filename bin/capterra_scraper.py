import logging
import requests
import sys
import traceback
from bs4 import BeautifulSoup
from . selenium_get_more import get_all

logging = logging.getLogger(__name__)


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
                'source': func.__name__,
                'line_number': sys.exc_info()[-1].tb_lineno,
                'name': e.__class__.__name__,
                'msg': str(e)
            }
            log_text = 'Excepted Fault: {source} generated a {name}: {msg}'.format(**error)
            # logging.debug(traceback.print_exc())

            # it is important for some functions that to receive a value on
            # Exception to indicate inability to extract data. You can change
            # that value to anything you want here.
            return None

    return wrapper


class CapterraScraper(object):

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


class PlatformPageScraper(CapterraScraper):
    def __init__(self, url, debug=False):
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
        self.data['reviews'] = self.extract_reviews()

    def get_full_page_data(self):
        if self.debug:
            r = requests.get(self.url)
            self.page_source = r.text
        else:
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
        return list(filter(None, [li.text for li in node.find_all('li')]))

    @fault_tolerant
    def extract_about(self):
        node = self.find_element_sibling(self.dom, 'h2', 'About', 'div')
        return self.clean_up_text(node.get_text())

    @fault_tolerant
    def extract_features(self):

        data = {}
        feature_lists = self.dom.select('.category-features-list')

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

    @fault_tolerant
    def extract_reviews(self):
        review_data = []
        review_nodes = self.dom.select('.cell-review')

        @fault_tolerant
        def extract_review(review_node):
            review = PlatformReviewScraper(review_node, self.debug)
            return review.data

        for review_node in review_nodes:
            review_data.append(extract_review(review_node))

        return review_data


class PlatformReviewScraper(CapterraScraper):

    def __init__(self, review_node, debug=True):
        self.debug = debug
        self.review_node = review_node
        self.data = {}

        self.scrape_data()

    def scrape_data(self):
        self.data['title'] = self.extract_title()
        self.data['likelihood_reccomendation'] = self.extract_likelihood_reccomendation()
        self.data['ratings'] = self.extract_ratings()
        self.data['reactions'] = self.extract_reactions()

    @fault_tolerant
    def extract_title(self):
        return self.review_node.select('q')[0].text

    @fault_tolerant
    def extract_likelihood_reccomendation(self):
        return self.review_node.select('.gauge-svg-image')[0]['alt']

    @fault_tolerant
    def extract_ratings(self):

        ratings = {}

        rating_nodes = self.review_node.find_all('span', class_=lambda x: False if not x else 'reviews-' in x)
        rating_nodes.extend(self.review_node.select('.overall-rating'))

        @fault_tolerant
        def get_rating(rating_node):
            return self.clean_up_text(rating_node.get_text())

        for rating_node in rating_nodes:
            rating_type = list(filter(lambda x: 'rating' in x, rating_node.get('class')))[0]
            ratings[rating_type] = get_rating(rating_node)

        return ratings

    @fault_tolerant
    def extract_reactions(self):

        reactions = {}
        reaction_nodes = self.review_node.select('.review-comments p')

        @fault_tolerant
        def extract_reaction(reaction_node):
            children = reaction_node.find_all(recursive=False)
            if len(children) == 0:
                return False

            reaction_type = children[0].text.replace(':', '')
            reaction_data = reaction_node.find(text=True, recursive=False)
            return {reaction_type: reaction_data}

        for reaction_node in reaction_nodes:
            reaction_data = extract_reaction(reaction_node)
            if reaction_data:
                reactions.update(**reaction_data)

        return reactions
