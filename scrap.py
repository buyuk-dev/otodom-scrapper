import sys
import argparse
import time
import logging
from pprint import pprint, pformat

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys

import requests
import openai

import secrets

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

openai.api_key = secrets.OPENAI_API_KEY


SUMMARY_PROMPT = """
Calculate the price breakdown for the apartment based on the given data.
Data labels are in english, but all text is written in polish language.
Price breakdown should be in json format where price is represented as a tuple: price and unit.
Include the following information in the breakdown (names in polish) czynsz najmu, czynsz administracyjny, opaty za media, oraz pozostałe.
Specify what are the costs included in "Pozostałe" category.

Data:
---------------
{}
---------------
Price breakdown:
"""


def scroll_down(driver):
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

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()
    
    return soup


def find_tags_with_attribute(html, attribute, element=None, valueFilter=None, soup=None):
    """ 
    """
    if soup is None:
        soup = BeautifulSoup(html, 'html.parser')

    tags_with_attribute = []

    for tag in soup.find_all(True):
        if attribute in tag.attrs and (element is None or element == tag.name):
            if element is None or tag.name == element:
                if valueFilter is not None:
                    if all(value != tag.get(attribute) for value in valueFilter):
                        continue

                tags_with_attribute.append(tag)

    return tags_with_attribute


def generate_summary(text):
    """ Use OpenAI GPT API to process scrapped ad data.
    """
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=SUMMARY_PROMPT.format(text),
        max_tokens=500,
        n=1,
        stop=None,
        temperature=0,
    )
    summary = response.choices[0].text.strip()
    return summary


def parse_labeled_content(tag):
    """ Given tag that has data-cy == 'table-label-content'
        assuming the label relates to the next div tag
        return pair (label, text) where text is the content
        of the labeled div tag.
    """
    return tag.get_text(strip=True), tag.find_next().get_text(strip=True)


def parse_otodom_ad(url):
    """ Attempt to parse otodom ad data from html.
    """
    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")

    # Assumption: all useful data is contained within tags that have data-cy attribute.
    def filter_data_cy_tags(tag):
        return tag.has_attr("data-cy")

    tags = soup.find_all(filter_data_cy_tags)

    # Expand all tags based on their data-cy attribute value.
    expanded = []
    for tag in tags:
        type_ = tag.get("data-cy")
        data = None

        # Filter out unwanted data-cy values.
        if any(value in type_ for value in [
            "navbar", "button", "AdUnit", "AdUnit"
        ]):
            continue

        # Expand selected elements based on their data-cy value.
        if type_ == "table-label-content":
            data = parse_labeled_content(tag)

        elif type_ == "adPageAdDescription":
            data = tag.get_text(strip=True)

        else:
            data = tag.get_text(strip=True)

        expanded.append((type_, data))

    return expanded


def pairs_to_dict(pairs):
    """ Convert list of pairs <key, value> into a dictionary
        {key: [list of values]}.
    """
    result = {}
    for key, value in pairs:
        if key in result:
            result[key].append(value)
        else:
            result[key] = [value]
    return result


def group_otodom_ad_data(data):
    grouped = pairs_to_dict(data)

    key_mapping = {
        "adPageAdDescription": "Description",
        "adPageAdTitle": "Title",
        "adPageHeaderPrice": "Price",
        "table-label-content": "Details"
    }
    mapped = {
        key_mapping.get(k, k): v for k, v in grouped.items()
    }

    details = mapped["Details"]
    mapped["Details"] = pairs_to_dict(details)

    return mapped


def format_mapped_ad_data(data):
    details = "\n".join(f"    {k}: {v}" for k,v in data["Details"].items())
    formatted = f"""
URL: {data['URL']}
Title: {data['Title']}
Price: {data['Price']}
Description: {data['Description']}
Details:
{details}
"""
    return formatted


def scrap_ad(url):
    """ Function to scrap single apartment ad from its url.
    """
    apartment_data = parse_otodom_ad(url)
    grouped_apartment_data = group_otodom_ad_data(apartment_data)
    grouped_apartment_data["URL"] = url

    formatted_data = format_mapped_ad_data(grouped_apartment_data)
    #summary = generate_summary(formatted_data)
    
    print(formatted_data)
    print("============================================")
    print("\n".join(summary.splitlines()))
    print("============================================")


def scrap_search_results_page(url):
    """ Function to scrap search result list (retrieve url's of all result ads).
    """
    soup = get_dynamic_content(url)

    if soup.find("div", {"data-cy": "no-search-results"}) is not None:
        return []

    promoted_items = find_tags_with_attribute(
        None, "data-cy", "a", ["listing-item-link"],
        soup.find("div", {"data-cy": "search.listing.promoted"})
    )
    promoted_items = [item.get("href") for item in promoted_items]

    organic_items = find_tags_with_attribute(
        None, "data-cy", "a", ["listing-item-link"],
        soup.find("div", {"data-cy": "search.listing.organic"})
    )
    organic_items = [item.get("href") for item in organic_items]

    # Merge all items.
    all_urls = []
    all_urls.extend(promoted_items)
    all_urls.extend(organic_items)

    # Return urls without duplicates.
    return list(set(all_urls))


def get_page_number_from_url(url):
    """
    """
    from urllib import parse

    current_page_num = int(parse.parse_qs(
        parse.urlparse(url).query
    )['page'][0])

    return current_page_num


def get_next_page_url(current_page_url):
    """
    """
    PAGE_FORMAT = "page={}"
    current_page_num = get_page_number_from_url(current_page_url)

    return current_page_url.replace(
        PAGE_FORMAT.format(current_page_num),
        PAGE_FORMAT.format(current_page_num + 1)
    )


def scrap_search_results(current_page_url):
    """
    """
    all_urls = []

    urls = scrap_search_results_page(current_page_url)
    current_page_url = get_next_page_url(current_page_url)
    all_urls.extend(urls)

    while urls is not None and len(urls) > 0:

        pgnum = get_page_number_from_url(current_page_url)
        print(f"scrapping result page {pgnum}")

        urls = scrap_search_results_page(current_page_url)
        current_page_url = get_next_page_url(current_page_url)

        all_urls.extend(urls)

    return set(all_urls)


def handle_single_ad_url(url):
    """ Scrap data from single apartment ad url.
    """
    logging.info("parsing single ad: %s", url)
    data = scrap_ad(url)
    pprint(data)


def handle_url_list_file(path):
    """ Take file path containing list of ad urls to process and process them.
    """
    logging.info("parsing ads from url list file: %s", path)

    with open(path) as ad_urls_file:

        for idx, line in enumerate(ad_urls_file):
            url_path = line.strip()
            url = f"https://www.otodom.pl{url_path}"
            scrap_ad(url)


def handle_search_results_url(url):
    """ Take search results url and retrieve urls for all ads.
    """
    logging.info("Scanning search results: %s", url)
    urls = scrap_search_results(url)
    for url in urls:
        print(url)

def is_url(text):
    """ Determine whether given string is an url (as opposed to file path)
    """
    return text.startswith("http://") or text.startswith("https://")


def resolve_command_handler(args):
    """ Resolve handlers for command and return callable.
    """
    if args.subcommand == 'scan':
        return lambda: handle_search_results_url(args.url)

    elif args.subcommand == 'parse':

        if is_url(args.input):
            return lambda: handle_single_ad_url(args.input)
 
        else:
            return lambda: handle_url_list_file(args.input)


def main():
    """ Parse and execute commands.
    """
    parser = argparse.ArgumentParser(description='Apartment scraper script')
    subparsers = parser.add_subparsers(dest='subcommand', help='Subcommands: scan, parse')

    # Subparser for the 'scan' command
    scan_parser = subparsers.add_parser('scan', help='Retrieve the list of URLs from the apartment renting website')
    scan_parser.add_argument('url', help='URL pointing to the search results')

    # Subparser for the 'parse' command
    parse_parser = subparsers.add_parser('parse', help='Process apartment ads')
    parse_parser.add_argument('input', help='Path to the file containing a list of URLs or a single URL')

    args = parser.parse_args()

    handler = resolve_command_handler(args)
    if handler is None:
        parser.print_help()
    else:
        handler()


if __name__ == '__main__':
    main()
