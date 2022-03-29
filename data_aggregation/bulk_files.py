from pysec_downloader.downloader import Downloader

from configparser import ConfigParser
from os import path
config_path = path.normpath(path.join(path.dirname(path.abspath(__file__)), '..', "config.cfg"))
config = ConfigParser()
config.read(config_path)




dl = Downloader(config["downloader"]["bulk_file_root_path"], user_agent=config["downloader"]["sec_user_agent"])

def update_bulk_files():
    '''update submissions and companyfacts bulk files'''
    dl.get_bulk_companyfacts()
    dl.get_bulk_submissions()
    return

if __name__ == "__main__":
    '''
    entry point for what tickers to extract and update down the line will be config[general][tracked_tickers]
    get bulk company data from sbmissions.zip
    might want to make this per ticker, so ican reuse when adding more tickers later on
    
    '''
    
    pass    # update_bulk_files()