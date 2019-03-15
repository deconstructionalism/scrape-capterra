# -*- coding: utf-8 -*-

from selenium import webdriver
from time import sleep


class LoadedPage(object):
    def __init__(self, url, debug):
        self.url = url
        self.debug = debug
        self.driver = webdriver.Chrome()
        self.page_source = None

        self.get_page_data()

    def load_page(self):
        self.driver.get(self.url)
        sleep(1)

    def close_popup(self):
        try:
            close = self.driver.find_element_by_class_name('.qual_x_svg_x')
            close.click()
            sleep(1)
        except Exception:
            pass

    def expand_page_data(self):
        while True:
            try:
                more = self.driver.find_element_by_class_name('show-more-reviews')
                sleep(5)
                mode.click()
                sleep(4)
            except Exception:
                break

    def get_page_data(self):
        self.load_page()
        self.close_popup()
        if not self.debug:
            self.expand_page_data()

        self.page_source = self.driver.page_source
        self.driver.close()
