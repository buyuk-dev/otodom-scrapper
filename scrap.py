import sys
import os
import argparse
import time
import logging
import json
from jsoncomment import JsonComment
from pprint import pprint, pformat

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys

import requests
import openai

import secrets

json = JsonComment(json)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
openai.api_key = secrets.OPENAI_API_KEY

DEFAULT_SUMMARY_PROMPT = """
I will give you a json description of a polish apartment ad scrapped from a website. Property names are in english, but the content is in polish.
All prices should be in PLN currency. When outputing values omit units. Prepare a summary of the ad and present it in the json format following given scheme:

// Apartment ad summary json schema
{
  "Title": "tytuł ogłoszenia",
  "Location": "lokalizacja mieszkania",
  "Size": "wymiary mieszkania w m^2",
  "Price": {
    "Rent": "czynsz najmu",
    "Administrative": "czynsz administracyjny (czasem nazywa się go opłatami administracyjnymi)",
    "Media": {
        "included": "media które są wliczone w czynsz",
        "extra": "media które trzeba opłacić dodatkowo"
    },
    "Parking": "jeżeli jest dodatkowa opłata za miejsce postojowe",
  },
  "URL": "link do ogłoszenia",
  "Pros": ["lista kluczowych zalet mieszkania"],
  "Cons": ["lista kluczowych wad mieszkania"],
  "Comments": "Additional comments which I should consider while deciding whether i am interested in this apartment."
}

// Apartment json data
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


def generate_summary(text, prompt):
    """ Use OpenAI GPT API to process scrapped ad data.
    """
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt + text,
        max_tokens=1000,
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
            "navbar", "button", "AdUnit", "AdUnit", "ad-page-ad-remote-service-tile"
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

    # Add location info
    locationTag = soup.find("a", {"aria-label": "Adres"})
    if locationTag is not None:
        expanded.append(("Location", locationTag.get_text()))

    # add info about ad publication date and last updated date.
    def contains_text_filter(tag, text, tagname="div"):
        return tag.name == tagname and text in tag.get_text()

    with open("page.html", "w") as pf:
        pf.write(soup.prettify())

    # not possible to parase these tags as they are dynamically generated with JS.
    # publishedTag = soup.find(string="Data dodania:")
    # updatedTag = soup.find(string="Data aktualizacji:")
    #if publishedTag is not None:
    #    expanded.append(("published", publishedTag.get_text()))
    #if updatedTag is not None:
    #    expanded.append(("lastUpdated", updatedTag.get_text()))

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


def flatten(data):
    if len(data) == 1: return data[0]
    else: return data


def group_otodom_ad_data(data):
    grouped = pairs_to_dict(data)

    key_mapping = {
        "adPageAdDescription": "Description",
        "adPageAdTitle": "Title",
        "adPageHeaderPrice": "Price",
        "table-label-content": "Details"
    }
    mapped = {
        key_mapping.get(k, k): flatten(v) for k, v in grouped.items()
    }

    details = mapped["Details"]
    details = pairs_to_dict(details)
    details = {k: flatten(v) for k,v in details.items()}

    mapped["Details"] = details


    return mapped


def scrap_ad(url):
    """ Function to scrap single apartment ad from its url.
    """
    apartment_data = parse_otodom_ad(url)
    grouped_apartment_data = group_otodom_ad_data(apartment_data)
    grouped_apartment_data["URL"] = url
    return grouped_apartment_data


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


def format_ad_data(data, output_file_path=None):
    json_str = json.dumps(data, sort_keys=True, indent=4, ensure_ascii=False)

    if output_file_path is not None:
        with open(output_file_path, "w+") as outf:
            outf.write(json_str)

    return json_str


def is_url(text):
    """ Determine whether given string is an url (as opposed to file path)
    """
    return text.startswith("http://") or text.startswith("https://")


class CommandHandlers:

    @staticmethod
    def handle_single_ad_url(url, output):
        """ Scrap data from single apartment ad url.
        """
        logging.info("parsing single ad: %s", url)
        data = scrap_ad(url)
        print(format_ad_data(data))


    @staticmethod
    def handle_url_list_file(path, output_directory):
        """ Take file path containing list of ad urls to process and process them.
        """
        logging.info("parsing ads from url list file: %s", path)

        with open(path) as ad_urls_file:
            for idx, line in enumerate(ad_urls_file):
                try:
                    url_path = line.strip()
                    url = f"https://www.otodom.pl{url_path}"

                    output_file_path = f"{output_directory}/{idx}.json"

                    data = scrap_ad(url)
                    print(format_ad_data(data, output_file_path))

                except Exception as err:
                    logging.exception("Failed to process url #%d: %s.", idx, line)


    @staticmethod
    def handle_search_results_url(url):
        """ Take search results url and retrieve urls for all ads.
        """
        logging.info("Scanning search results: %s", url)
        urls = scrap_search_results(url)
        for url in urls:
            print(url)


    @staticmethod
    def summarize_ad_data(input_path, prompt=None, output=None):
        """
        """
        json_str = None
        with open(input_path, "r", encoding="utf-8") as jf:
            json_str = jf.read()

        if prompt is None:
            prompt = DEFAULT_SUMMARY_PROMPT

        summary_raw = generate_summary(json_str, prompt)
        print(summary_raw)
        return summary_raw


    @staticmethod
    def summarize_ads_dir(input_dir, prompt=None, output=None):
        for filename in os.listdir(input_dir):
            try:
                path = os.path.join(input_dir, filename)
                output_path = path + ".ai"
                if os.path.isfile(output_path):
                    logging.warning("File %s exists. Please remove it if you want to regenerate the summary.", output_path)
                    continue

                if os.path.isfile(path):
                    logging.info("processing %s", path)
                    summary = CommandHandlers.summarize_ad_data(path, prompt, output)
                    with open(output_path, "w") as output_file:
                        output_file.write(summary)
            except Exception as e:
                logging.exception("Error has occured while summarizing ads.")


    @staticmethod
    def handle_filter_command(input_dir, priceLimit, output=None):
        """ Filter only ads which are below total price limit.
        """
        logging.info("Filtering ads which have a total price higher than %d PLN.", priceLimit)
        filtered = []
        for filename in os.listdir(input_dir):
            try:
                path = os.path.join(input_dir, filename)
                if not (path.endswith('.json.ai') and os.path.isfile(path)):
                    continue

                json_data = None
                with open(path, "r", encoding="utf-8") as json_file:
                    json_data = json.load(json_file)

                def sanitize(value):
                    if type(value) in (float, int):
                        return value

                    if type(value) is str:
                        try:
                            return float(value)
                        except:
                            return 0
                    else:
                        return 0

                total_price = sanitize(json_data["Price"]["Rent"]) + \
                              sanitize(json_data["Price"]["Administrative"]) + \
                              sanitize(json_data["Price"]["Parking"])

                json_data["path"] = path
                json_data["totalPrice"] = total_price

                if total_price <= priceLimit:
                    filtered.append(json_data)

            except Exception as e:
                logging.exception("Error has occured while summarizing ads.")

        filtered.sort(key=lambda x: x["totalPrice"])

        logging.debug("Filtered list contains %d ads.", len(filtered))
        json_data = json.dumps(filtered, sort_keys=True, indent=4, ensure_ascii=False)

        if output is None:
            print(json_data)
        else:
            with open(output, "w", encoding="utf-8") as json_file:
                json_file.write(json_data)


def resolve_command_handler(args):
    """ Resolve handlers for command and return callable.
    """
    if args.subcommand == 'scan':
        return lambda: CommandHandlers.handle_search_results_url(args.url)

    elif args.subcommand == 'parse':

        if is_url(args.input):
            return lambda: CommandHandlers.handle_single_ad_url(args.input, args.output)

        else:
            return lambda: CommandHandlers.handle_url_list_file(args.input, args.output)

    elif args.subcommand == 'gpt':
        if os.path.isfile(args.input):
            return lambda: CommandHandlers.summarize_ad_data(args.input, args.prompt, args.output)
        else:
            return lambda: CommandHandlers.summarize_ads_dir(args.input, args.prompt, args.output)

    elif args.subcommand == 'filter':
        return lambda: CommandHandlers.handle_filter_command(args.input, args.limit, args.output)


def main():
    """ Parse and execute commands.
    """
    parser = argparse.ArgumentParser(description='Apartment scraper script')
    subparsers = parser.add_subparsers(dest='subcommand', help='Subcommands: scan, parse, gpt')

    # Subparser for the 'scan' command
    scan_parser = subparsers.add_parser('scan', help='Retrieve the list of URLs from the apartment renting website')
    scan_parser.add_argument('url', help='URL pointing to the search results')

    # Subparser for the 'parse' command
    parse_parser = subparsers.add_parser('parse', help='Process apartment ads')
    parse_parser.add_argument('input', help='Path to the file containing a list of URLs or a single URL')
    parse_parser.add_argument('-o', '--output', type=str, help='When processing list of urls will act as an output directory, for single url its a file path.')

    # Subpraser for the 'gpt' command
    gpt_parser = subparsers.add_parser('gpt', help="Perform analysis of the apartment json description using OpenAI GPT API.")
    gpt_parser.add_argument("input", help="Path to the file or directory containing scrapped apartment data.")
    gpt_parser.add_argument("-p", "--prompt", type=str, help="Overrides default prompt for GPT.")
    gpt_parser.add_argument("-o", "--output", type=str, help="Output file path.")

    # Subparer for the 'filter' command
    filter_parser = subparsers.add_parser('filter', help="Filter ads stored in json files in the input directory.")
    filter_parser.add_argument("input", help="Path to the directory containing ad.json.ai files.")
    filter_parser.add_argument("-o", "--output", type=str, help="Output file path.")
    filter_parser.add_argument("-l", "--limit", type=int, default=3000, help="Upper limit for the total price.")

    args = parser.parse_args()

    handler = resolve_command_handler(args)
    if handler is None:
        parser.print_help()
    else:
        handler()


if __name__ == '__main__':
    main()
