from pysec_downloader.downloader import Downloader
from config import ROOT_PATH, SEC_USER_AGENT

dl = Downloader(ROOT_PATH, user_agent=SEC_USER_AGENT)

def update_bulk_files():
    '''update submissions and companyfacts bulk files'''
    dl.get_bulk_companyfacts()
    dl.get_bulk_submissions()
    return

if __name__ == "__main__":
    update_bulk_files()