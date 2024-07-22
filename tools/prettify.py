import argparse
import json
import logging
import os
import pathlib

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def prettify_json(path, encoding="utf-8"):
    logger.info("prettifying json file %s", path)
    json_str = pathlib.Path(path).read_text(encoding)
    json_data = json.loads(json_str)
    prettified = json.dumps(json_data, ensure_ascii=False, indent=2)
    pathlib.Path(path).write_text(prettified, encoding)


def prettify_directory(directory: str):
    logger.info("prettifying directory %s", directory)
    for path in pathlib.Path(directory).iterdir():
        if path.is_file() and path.suffix == ".json":
            prettify_json(path)


def main():
    parser = argparse.ArgumentParser("prettify")
    parser.add_argument("path")
    args = parser.parse_args()
    prettify_directory(args.path)


if __name__ == "__main__":
    main()
