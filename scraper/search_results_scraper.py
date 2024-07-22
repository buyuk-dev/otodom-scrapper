from bs4 import BeautifulSoup

from .browser import get_dynamic_content


def find_tags_with_attribute(
    html, attribute, element=None, valueFilter=None, soup=None
):
    """ """
    if soup is None:
        soup = BeautifulSoup(html, "html.parser")

    tags_with_attribute = []

    for tag in soup.find_all(True):
        if attribute in tag.attrs and (element is None or element == tag.name):
            if element is None or tag.name == element:
                if valueFilter is not None:
                    if all(value != tag.get(attribute) for value in valueFilter):
                        continue

                tags_with_attribute.append(tag)

    return tags_with_attribute


def scrap_search_results_page(url):
    """Function to scrap search result list (retrieve url's of all result ads)."""
    soup = get_dynamic_content(url)

    if soup.find("div", {"data-cy": "no-search-results"}) is not None:
        return []

    promoted_items = find_tags_with_attribute(
        None,
        "data-cy",
        "a",
        ["listing-item-link"],
        soup.find("div", {"data-cy": "search.listing.promoted"}),
    )
    promoted_items = [item.get("href") for item in promoted_items]

    organic_items = find_tags_with_attribute(
        None,
        "data-cy",
        "a",
        ["listing-item-link"],
        soup.find("div", {"data-cy": "search.listing.organic"}),
    )
    organic_items = [item.get("href") for item in organic_items]

    # Merge all items.
    all_urls = []
    all_urls.extend(promoted_items)
    all_urls.extend(organic_items)

    # Return urls without duplicates.
    return list(set(all_urls))


def get_page_number_from_url(url):
    """ """
    from urllib import parse

    try:
        current_page_num = int(parse.parse_qs(parse.urlparse(url).query)["page"][0])
    except:
        return 1

    return current_page_num


def get_next_page_url(current_page_url):
    """ """
    PAGE_FORMAT = "page={}"
    current_page_num = get_page_number_from_url(current_page_url)

    return current_page_url.replace(
        PAGE_FORMAT.format(current_page_num), PAGE_FORMAT.format(current_page_num + 1)
    )


def scrap_search_results(current_page_url):
    """ """
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
