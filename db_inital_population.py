from numpy import poly
from data_aggregation.bulk_files import update_bulk_files

from os import path
from pathlib import Path
from datetime import datetime, timedelta
from configparser import ConfigParser
config_path = path.normpath(path.join(path.dirname(path.abspath(__file__)), '.', "config.cfg"))
config = ConfigParser()
config.read(config_path)

from dilution_db import DilutionDB
from data_aggregation.polygon_basic import PolygonClient
from data_aggregation.fact_extractor import _get_fact_data, get_cash_and_equivalents, get_outstanding_shares, get_cash_financing, get_cash_investing, get_cash_operating
from data_aggregation.bulk_files import format_submissions_json_for_db
from pysec_downloader.downloader import Downloader
from _constants import EDGAR_BASE_ARCHIVE_URL



import json
import logging
logger = logging.getLogger(__package__)
if config.getboolean("environment", "production") is False:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

polygon_key = config["polygon"]["api_key"]
dl_root_path = config["downloader"]["filings_root_path"]
polygon_overview_files_path = config["polygon"]["overview_files_path"]
tickers = [t.strip() for t in config["general"]["tracked_tickers"].strip("[]").split(",")]
tracked_forms = [t.strip() for t in config["general"]["tracked_forms"].strip("[]").split(",")]

'''
1) download the bulk files if they havnt been downloaded yet (check db lud)
2) get the tracked tickers and iterate through:
    2.1) get the company_overview
    2.2) get the outstanding shares -> write to db
    2.3) get the net_cash_and_equivilants -> write to db
    2.4) get proceeds from common share issuance -> write to db
    2.5) download ["S-3", "424B1", 424B2", 424B3", 424B4", 424B5", "S-1",
                   "EFFECT", "S-3MEF", "S-1MEF", "F-1", "F-3", "F-1MEF",
                   "F-3MEF", "S-3ASR", "F-3ASR", "8-K", "6-K"]
    2.6) build filing_links from submissions file -> write to db

    ! could do 2.1-2.4/2.6 in main and 2.5 in separat process
    ! and notify the other process on completion of download
    ! but for now, KISS but slow

3) think how i can update daily    
'''
def inital_population(db: DilutionDB, dl_root_path: str, polygon_overview_files_path: str, polygon_api_key: str, tickers: list):
    polygon_client = PolygonClient(polygon_api_key)
    dl = Downloader(dl_root_path)
    if not Path(polygon_overview_files_path).exists():
        Path(polygon_overview_files_path).mkdir(parents=True)
        logger.debug(
            f"created overview_files_path and parent folders: {polygon_overview_files_path}")
    for ticker in tickers:
        # get basic info and create company
        ov = polygon_client.get_overview_single_ticker(ticker)
        with open(Path(polygon_overview_files_path) / (ov["cik"] + ".json"), "w+") as f:
            json.dump(ov, f)
        logger.debug(f"overview_data: {ov}")
        # check that we have a sic otherwise assign  9999 --> nonclassifable
        try:
            ov["sic_code"]
        except KeyError:
            ov["sic_code"] = "9999"
            ov["sic_description"] = "Nonclassifiable"
        id = db.create_company(
                    ov["cik"],
                    ov["sic_code"],
                    ticker, ov["name"],
                    ov["description"],
                    ov["sic_description"])
        if not id:
            raise ValueError("couldnt get the company id from create_company")
        # load the xbrl facts 
        companyfacts_file_path = Path(dl_root_path) / "companyfacts" / ("CIK"+ov["cik"]+".json")
        recent_submissions_file_path = Path(dl_root_path) / "submissions" / ("CIK"+ov["cik"]+".json")
        with open(companyfacts_file_path, "r") as f:
            companyfacts = json.load(f)
            
            # query for wanted xbrl facts and write to db
            outstanding_shares = get_outstanding_shares(companyfacts)
            logger.debug(f"outstanding_shares: {outstanding_shares}")
            for fact in outstanding_shares:
                db.create_outstanding_shares(
                    id, fact["end"], fact["val"])
            net_cash = get_cash_and_equivalents(companyfacts)
            logger.debug(f"net_cash: {net_cash}")
            for fact in net_cash:
                db.create_net_cash_and_equivalents(
                    id, fact["end"], fact["val"])
                if "val_excluding_restrictednoncurrent" in fact.keys():
                    db.create_net_cash_and_equivalents_excluding_restricted_noncurrent(
                        id, fact["end"], fact["val_excluding_restrictednoncurrent"])
            
            #partially tested
            cash_financing = get_cash_financing(companyfacts)
            for fact in cash_financing:
                db.create_cash_financing(
                    id, fact["start"], fact["end"], fact["val"]
                )
            cash_operating = get_cash_operating(companyfacts)
            for fact in cash_operating:
                db.create_cash_operating(
                    id, fact["start"], fact["end"], fact["val"]
                )
            cash_investing = get_cash_investing(companyfacts)
            for fact in cash_investing:
                db.create_cash_investing(
                    id, fact["start"], fact["end"], fact["val"]
                )
            
        # populate filing_links table from submissions.zip
        with open(recent_submissions_file_path, "r") as f:
            submissions = format_submissions_json_for_db(
                EDGAR_BASE_ARCHIVE_URL,
                ov["cik"],
                json.load(f))
            for s in submissions:
                db.create_filing_link(
                    id,
                    s["filing_html"],
                    s["form"],
                    s["filingDate"],
                    s["primaryDocDescription"],
                    s["fileNumber"])

def get_filing_set(self, downloader: Downloader, ticker: str, forms: list, after: str):
    # # download the last 2 years of relevant filings
    if after is None:
        after = str((datetime.now() - timedelta(weeks=104)).date())
    for form in forms:
    #     # add check for existing file in pysec_donwloader so i dont download file twice
        downloader.get_filings(ticker, form, after, number_of_filings=1000)








if __name__ == "__main__":
    db = DilutionDB(config["dilution_db"]["connectionString"])
    db._delete_all_tables()
    db._create_tables()
    db.create_sics()
    db.create_form_types()
    inital_population(db, dl_root_path, polygon_overview_files_path, polygon_key, ["CEI"])




    # db.create_tracked_companies()
    # now get filings from submissions.zip
    # populate filing_links

    # then get each companyfact from companyfacts.zip
    # and populate corresponding table

    # then download sec filings (s-3 and related files of that filing)

    #notes:
    # check what is included in the 8-k/6-k download and resolve the issue either 
    # by downloading the full submission or individual files
