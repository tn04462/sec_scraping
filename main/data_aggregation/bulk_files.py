from pysec_downloader.downloader import Downloader
from ..configs import cnf
from os import path



dl = Downloader(cnf.DOWNLOADER_ROOT_PATH, user_agent=cnf.SEC_USER_AGENT)

def update_bulk_files():
    '''update submissions and companyfacts bulk files'''
    # dl.get_bulk_companyfacts()
    dl.get_bulk_submissions()



if __name__ == "__main__":
    update_bulk_files()