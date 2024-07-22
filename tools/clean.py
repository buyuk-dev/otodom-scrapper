import sys

import requests
from bs4 import BeautifulSoup, Comment


def clean_html(html):
    soup = BeautifulSoup(html, "html.parser")

    # Remove all <script> and <style> tags
    for tag in soup(["script", "style"]):
        tag.decompose()

    # Remove all comments
    for comment in soup(text=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Remove all empty tags (if needed)
    for tag in soup.find_all():
        if len(tag.get_text(strip=True)) == 0:
            tag.decompose()

    # Remove style attributes from all tags
    for tag in soup.find_all(style=True):
        del tag["style"]

    return str(soup)


# Example usage
source = sys.argv[1]
html = None
if source.startswith("http"):
    url = source
    html = requests.get(url).text

else:
    with open(source) as html_file:
        html = html_file.read()

cleaned_html = clean_html(html)
print(cleaned_html)
