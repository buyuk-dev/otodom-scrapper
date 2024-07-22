import json
import logging

from bs4 import BeautifulSoup
from jsoncomment import JsonComment

from .base_scraper import BaseScraper

json = JsonComment(json)


def filter_ad_json_props(ad_dict: dict) -> dict:
    ALLOW = {"Description", "Details", "Location", "Title", "Price", "URL"}
    filtered = {k: v for k, v in ad_dict.items() if k in ALLOW}
    return filtered


def parse_labeled_content(tag):
    """Given tag that has data-cy == 'table-label-content'
    assuming the label relates to the next div tag
    return pair (label, text) where text is the content
    of the labeled div tag.
    """
    return tag.get_text(strip=True), tag.find_next().get_text(strip=True)


def parse_otodom_ad(url):
    """Attempt to parse otodom ad data from html."""
    html = BaseScraper().download_url(url)
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
        if any(
            value in type_
            for value in [
                "navbar",
                "button",
                "AdUnit",
                "AdUnit",
                "ad-page-ad-remote-service-tile",
            ]
        ):
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
    # if publishedTag is not None:
    #    expanded.append(("published", publishedTag.get_text()))
    # if updatedTag is not None:
    #    expanded.append(("lastUpdated", updatedTag.get_text()))

    return expanded


def pairs_to_dict(pairs):
    """Convert list of pairs <key, value> into a dictionary
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
    if len(data) == 1:
        return data[0]
    else:
        return data


def group_otodom_ad_data(data):
    grouped = pairs_to_dict(data)

    key_mapping = {
        "adPageAdDescription": "Description",
        "adPageAdTitle": "Title",
        "adPageHeaderPrice": "Price",
        "table-label-content": "Details",
    }
    mapped = {key_mapping.get(k, k): flatten(v) for k, v in grouped.items()}

    details = mapped["Details"]
    details = pairs_to_dict(details)
    details = {k: flatten(v) for k, v in details.items()}

    mapped["Details"] = details

    return mapped


def scrap_ad(url):
    """Function to scrap single apartment ad from its url."""
    apartment_data = parse_otodom_ad(url)
    logging.info(apartment_data)

    grouped_apartment_data = group_otodom_ad_data(apartment_data)
    grouped_apartment_data["URL"] = url

    return grouped_apartment_data


def format_ad_data(data, output_file_path=None):
    json_str = json.dumps(data, sort_keys=True, indent=4, ensure_ascii=False)

    if output_file_path is not None:
        with open(output_file_path, "w+") as outf:
            outf.write(json_str)

    return json_str
