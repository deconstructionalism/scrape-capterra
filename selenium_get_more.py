from selenium import webdriver
from selenium.common.exceptions import ElementNotVisibleException
from time import sleep

def get_all(url, expand=True):

    driver = webdriver.Chrome()

    print(url)
    driver.get(url)
    if expand:
        reload_count = 0
        while True:
            try:
                start, end = reload_count, reload_count + 49
                print('loading {} to {}...'.format(start, end))
                elem = driver.find_element_by_class_name('show-more-reviews')
                sleep(5)
                elem.click()
                sleep(4)
                reload_count += 50
            except ElementNotVisibleException as e:
                print('no more left')
                break
    page_source = driver.page_source
    driver.close()            
    return page_source
