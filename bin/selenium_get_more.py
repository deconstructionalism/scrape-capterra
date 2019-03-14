from selenium import webdriver
from selenium.common.exceptions import ElementNotVisibleException, NoSuchElementException
from time import sleep

def get_all(url, debug=False):

    driver = webdriver.Chrome()

    driver.get(url)
    sleep(2)
    try:
        qual = driver.find_element_by_class_name('.qual_x_svg_x')
        qual.click()
        sleep(1)
    # except NoSuchElementException as e:
    except Exception:
        pass

    if not debug:
        reload_count = 0
        while True:
            try:
                start, end = reload_count, reload_count + 49
                elem = driver.find_element_by_class_name('show-more-reviews')
                sleep(5)
                elem.click()
                sleep(4)
                reload_count += 50
            # except (ElementNotVisibleException, NoSuchElementException) as e:
            except Exception:
                break
    page_source = driver.page_source
    driver.close()            
    return page_source
