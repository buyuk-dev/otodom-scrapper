import sys
import requests
from bs4 import BeautifulSoup, Comment


def clean_html(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

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
url = sys.argv[1]
cleaned_html = clean_html(url)
print(cleaned_html)

