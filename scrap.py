import argparse
import json
import logging
import os

from jsoncomment import JsonComment

json = JsonComment(json)

from scraper.ad_scraper import filter_ad_json_props, format_ad_data, scrap_ad
from scraper.base_scraper import BaseScraper
from scraper.gpt import generate_summary
from scraper.prompts import DEFAULT_SUMMARY_PROMPT
from scraper.search_results_scraper import scrap_search_results

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def is_url(text):
    """Determine whether given string is an url (as opposed to file path)"""
    return text.startswith("http://") or text.startswith("https://")


class CommandHandlers:

    @staticmethod
    def handle_single_ad_url(url, output):
        """Scrap data from single apartment ad url."""
        logging.info("parsing single ad: %s", url)
        data = scrap_ad(url)

    @staticmethod
    def handle_url_list_file(path, output_directory):
        """Take file path containing list of ad urls to process and process them."""
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
        """Take search results url and retrieve urls for all ads."""
        logging.info("Scanning search results: %s", url)
        urls = scrap_search_results(url)
        for url in urls:
            print(url)

    @staticmethod
    def summarize_ad_data(input_path, prompt=None, output=None) -> dict:
        """ """
        ad_data = None
        with open(input_path, "r", encoding="utf-8") as jf:
            ad_data = json.load(jf)

        ad_data = filter_ad_json_props(ad_data)

        if prompt is None:
            prompt = DEFAULT_SUMMARY_PROMPT

        formatted_json_ad = json.dumps(ad_data, ensure_ascii=False, indent=2)
        summary = generate_summary(formatted_json_ad, prompt)

        logging.info(json.dumps(summary, ensure_ascii=False, indent=2))
        return summary

    @staticmethod
    def summarize_ads_dir(input_dir, prompt=None, output=None):
        for filename in os.listdir(input_dir):
            try:
                path = os.path.join(input_dir, filename)
                output_path = os.path.join(output, f"{filename}.ai")
                if os.path.isfile(output_path):
                    logging.warning(
                        "File %s exists. Please remove it if you want to regenerate the summary.",
                        output_path,
                    )
                    continue

                logging.info("processing %s", path)
                summary = CommandHandlers.summarize_ad_data(path, prompt, output)

                with open(output_path, "w", encoding="utf-8") as output_file:
                    json.dump(summary, output_file, ensure_ascii=False)

            except Exception as e:
                logging.exception("Error has occured while summarizing ads.")

    @staticmethod
    def handle_filter_command(input_dir, priceLimit, output=None):
        """Filter only ads which are below total price limit."""
        logging.info(
            "Filtering ads which have a total price higher than %d PLN.", priceLimit
        )
        filtered = []
        for filename in os.listdir(input_dir):
            try:
                path = os.path.join(input_dir, filename)
                if not (path.endswith(".ai.json") and os.path.isfile(path)):
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

                total_price = (
                    sanitize(json_data["Price"]["Rent"])
                    + sanitize(json_data["Price"]["Administrative"])
                    + sanitize(json_data["Price"]["Parking"])
                )

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
    """Resolve handlers for command and return callable."""
    if args.subcommand == "scan":
        return lambda: CommandHandlers.handle_search_results_url(args.url)

    elif args.subcommand == "parse":

        if is_url(args.input):
            return lambda: CommandHandlers.handle_single_ad_url(args.input, args.output)

        else:
            return lambda: CommandHandlers.handle_url_list_file(args.input, args.output)

    elif args.subcommand == "gpt":
        if os.path.isfile(args.input):
            return lambda: CommandHandlers.summarize_ad_data(
                args.input, args.prompt, args.output
            )
        else:
            return lambda: CommandHandlers.summarize_ads_dir(
                args.input, args.prompt, args.output
            )

    elif args.subcommand == "filter":
        return lambda: CommandHandlers.handle_filter_command(
            args.input, args.limit, args.output
        )


def main():
    """Parse and execute commands."""
    parser = argparse.ArgumentParser(description="Apartment scraper script")
    subparsers = parser.add_subparsers(
        dest="subcommand", help="Subcommands: scan, parse, gpt"
    )

    # Subparser for the 'scan' command
    scan_parser = subparsers.add_parser(
        "scan", help="Retrieve the list of URLs from the apartment renting website"
    )
    scan_parser.add_argument("url", help="URL pointing to the search results")

    # Subparser for the 'parse' command
    parse_parser = subparsers.add_parser("parse", help="Process apartment ads")
    parse_parser.add_argument(
        "input", help="Path to the file containing a list of URLs or a single URL"
    )
    parse_parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="When processing list of urls will act as an output directory, for single url its a file path.",
    )

    # Subpraser for the 'gpt' command
    gpt_parser = subparsers.add_parser(
        "gpt",
        help="Perform analysis of the apartment json description using OpenAI GPT API.",
    )
    gpt_parser.add_argument(
        "input",
        help="Path to the file or directory containing scrapped apartment data.",
    )
    gpt_parser.add_argument(
        "-p", "--prompt", type=str, help="Overrides default prompt for GPT."
    )
    gpt_parser.add_argument("-o", "--output", type=str, help="Output file path.")

    # Subparer for the 'filter' command
    filter_parser = subparsers.add_parser(
        "filter", help="Filter ads stored in json files in the input directory."
    )
    filter_parser.add_argument(
        "input", help="Path to the directory containing ad.json.ai files."
    )
    filter_parser.add_argument("-o", "--output", type=str, help="Output file path.")
    filter_parser.add_argument(
        "-l", "--limit", type=int, default=3000, help="Upper limit for the total price."
    )

    args = parser.parse_args()

    handler = resolve_command_handler(args)
    if handler is None:
        parser.print_help()
    else:
        handler()


if __name__ == "__main__":
    main()
