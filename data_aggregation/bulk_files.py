from pysec_downloader.downloader import Downloader

from configparser import ConfigParser
from os import path
from posixpath import join as urljoin
import json
config_path = path.normpath(path.join(path.dirname(path.abspath(__file__)), '..', "config.cfg"))
config = ConfigParser()
config.read(config_path)




dl = Downloader(config["downloader"]["bulk_file_root_path"], user_agent=config["downloader"]["sec_user_agent"])

def update_bulk_files():
    '''update submissions and companyfacts bulk files'''
    dl.get_bulk_companyfacts()
    dl.get_bulk_submissions()
    return


cik = "0001718405"
base_path = r"C:\Users\Olivi\Testing\sec_scraping\resources\test_set\bulk\submissions"
from pathlib import Path
with open(Path(base_path)/("CIK"+cik+".json"), "r") as f:
    sub = json.load(f)
    
def format_submissions_json_for_db(base_url, cik, sub):
    filings = sub["filings"]["recent"]
    wanted_fields = ["accessionNumber", "filingDate", "form", "fileNumber", "primaryDocument", "primaryDocDescription", "primaryDocument"]
    cleaned = []
    for r in range(0, len(filings["accessionNumber"]), 1):
        entry = {}
        for field in wanted_fields:
            entry[field] = filings[field][r]
        entry["filing_html"] = build_submission_link(base_url, cik, entry["accessionNumber"].replace("-", ""), entry["primaryDocument"])
        # print(entry.keys())
        cleaned.append(entry)
    return cleaned

def build_submission_link(base_url, cik, accession_number, primary_document):
    return urljoin(urljoin(urljoin(base_url, cik), accession_number), primary_document)


if __name__ == "__main__":
    format_submissions_json_for_db("https://www.sec.gov/Archives/edgar/data", "00001718405", sub)
    '''
    entry point for what tickers to extract and update down the line will be config[general][tracked_tickers]
    get bulk company data from sbmissions.zip
    might want to make this per ticker, so ican reuse when adding more tickers later on
    
    '''
    
    pass    # update_bulk_files()