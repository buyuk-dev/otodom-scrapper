import sys
import argparse
from pprint import pprint, pformat

from bs4 import BeautifulSoup
import requests
import openai

import secrets

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


def parse_otodom_ad_html(html):
    """ Attempt to parse otodom ad data from html.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Assumption: all useful data is contained within tags that have data-cy attribute.
    tags = find_tags_with_attribute(html, "data-cy", soup)

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


def parse_otodom_ad_url(url):
    """ Retrieve html source from ad page and parse it.
    """
    html = requests.get(url).text
    return parse_otodom_ad_html(html)


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
        key_mapping[k]: v for k, v in grouped.items()
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
    apartment_data = parse_otodom_ad_url(url)
    grouped_apartment_data = group_otodom_ad_data(apartment_data)
    grouped_apartment_data["URL"] = url

    formatted_data = format_mapped_ad_data(grouped_apartment_data)
    summary = generate_summary(formatted_data)
    
    print(formatted_data)
    print("============================================")
    print("\n".join(summary.splitlines()))
    print("============================================")


def scrap_search_results(url):
    """ Function to scrap search result list (retrieve url's of all result ads).
    """
    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")

    pagination_nav = find_tags_with_attribute(html, "data-cy", "nav", ["pagination"], soup)
    #pprint(pagination_nav)

    promoted_divs = find_tags_with_attribute(html, "data-cy", "div", ["search.listing.promoted"], soup)
    #pprint(promoted_divs)

    organic_divs = find_tags_with_attribute(html, "data-cy", "div", ["search.listing.organic"], soup)
    #pprint(organic_divs)

    
    

    #tags = find_tags_with_attribute(
    #    html, "data-cy", "div",
    #    [
    #     "search-list-pagination",
    #     "search.listing.promoted",
    #      "search.listing.organic",
    #    ],
    #    soup
    #)

    results = None



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    args = parser.parse_args()
    #scrap_ad(args.url)
    scrap_search_results(args.url)
