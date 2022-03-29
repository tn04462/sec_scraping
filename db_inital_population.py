from data_aggregation import bulk_files

from os import path
from configparser import ConfigParser
config_path = path.normpath(path.join(path.dirname(path.abspath(__file__)), '..', "config.cfg"))
config = ConfigParser()
config.read(config_path)

'''take all the data from the bulk files and ...'''


if __name__ == "__main__":
    # to format tracked tickers in to list:
    # config_tickers = tickers.strip("[]").split(",")
    pass