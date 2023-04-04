usage: scrap.py [-h] {scan,parse} ...

Apartment scraper script

positional arguments:
  {scan,parse}  Subcommands: scan, parse
    scan        Retrieve the list of URLs from the apartment renting website
    parse       Process apartment ads

optional arguments:
  -h, --help    show this help message and exit
(env) michal | ~/otodom-browser ( master ) > python scrap.py scan --help
usage: scrap.py scan [-h] url

positional arguments:
  url         URL pointing to the search results

optional arguments:
  -h, --help  show this help message and exit
(env) michal | ~/otodom-browser ( master ) > python scrap.py parse --help
usage: scrap.py parse [-h] [-o OUTPUT] input

positional arguments:
  input                 Path to the file containing a list of URLs or a single URL

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        When processing list of urls will act as an output directory, for single url its a file path.
