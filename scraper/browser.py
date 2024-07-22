import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys


def scroll_down(driver: webdriver.Chrome):
    scroll_pause_time = 2
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        time.sleep(scroll_pause_time)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


def get_dynamic_content(url):
    options = Options()
    options.headless = True
    driver = webdriver.Chrome(options=options)

    driver.get(url)
    driver.implicitly_wait(0.5)
    scroll_down(driver)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    return soup
