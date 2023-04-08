# Otodom.pl Scrapper

A command-line Python script that scrapes apartment data from a rental apartment listings website (otodom.pl).
This script retrieves a list of URLs from a search results page and then scrapes the apartment information from each individual ad page.
The collected data is stored in JSON files in an output directory.
Optionally, the script can send each ad for processing to the GPT API to parse the data into a more concise and easier-to-read form (also in JSON).
Once the data is collected (and possibly processed), you can filter the apartments based on conditions such as total price.


## Features

+ Scrape apartment data from a rental apartment listings website
+ Retrieve list of URLs from search results page
+ Scrape apartment information from individual ad pages
+ Store collected data in JSON files in an output directory
+ Optional GPT API processing for more concise and easy-to-read data
+ Filter apartments based on conditions (e.g., total price)


## Requirements

+ Python 3.x
+ selenium (optional for dynamic content)
+ jsoncomment
+ requests
+ BeautifulSoup4


## Installation

1. Clone this repository or download the script.

    git clone https://github.com/buyuk-dev/otodom-scrapper.git

2. Install the required dependencies:

    pip install -r requirements.txt

3. Usage:

To retrieve a list of URLs from a search results page:

    python scrap.py scan <url-pointing-to-search-result> > urls

This will create a `urls` file in the current directory containing a list of URLs to the apartment ads.
To scrape apartment information from a list of URLs in a file:

    python scrap.py parse <path-to-urls-file>

This will process each URL one by one, scraping the apartment information and storing it in JSON files in the output directory.
To scrape apartment information from a single URL:

    python scrap.py parse <url-to-apartment-ad>

This will process the given URL, scraping the apartment information and storing it in a JSON file in the output directory.
To enable GPT API processing for more concise and easy-to-read data, add the --gpt flag when calling the script:

    python scrap.py parse <path-to-urls-file> --gpt

To filter the collected apartments based on conditions such as total price use the `filter` command.
Currently it is required to process the ads using gpt before filtering in order to compute total price.

    python scrap.py filter --limit 3000 <directory>


## Contributing

Feel free to submit pull requests or open issues with suggestions for improvements or new features.


## License

This project is released under the MIT License.
