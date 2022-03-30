from data_aggregation import bulk_files

from os import path
from configparser import ConfigParser
config_path = path.normpath(path.join(path.dirname(path.abspath(__file__)), '..', "config.cfg"))
config = ConfigParser()
config.read(config_path)

from dilution_db import DilutionDB
from data_aggregation.polygon_basic import get_tracked_tickers
'''take all the data from the bulk files and ...'''


if __name__ == "__main__":
    db = DilutionDB(config["dilution_db"]["connectionString"])
    db._create_tables()
    db._create_sics()
    get_tracked_tickers()
    db.create_tracked_companies()
    # now get filings from submissions.zip
    # populate filing_links

    # then get each companyfact from companyfacts.zip
    # and populate corresponding table

    # then download sec filings (s-3 and related files of that filing)
