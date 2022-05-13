
from os import path
from pathlib import Path
from datetime import datetime, timedelta
import json
import logging



from dilution_db import DilutionDB
from main.data_aggregation.polygon_basic import PolygonClient
from main.data_aggregation.fact_extractor import _get_fact_data, get_cash_and_equivalents, get_outstanding_shares, get_cash_financing, get_cash_investing, get_cash_operating
from pysec_downloader.downloader import Downloader
from main.configs import cnf
from _constants import EDGAR_BASE_ARCHIVE_URL
from requests.exceptions import HTTPError



logger = logging.getLogger(__package__)
# fh = logging.FileHandler(r"E:\sec_scraping\resources\datasets\population_errors.txt")
fh = logging.FileHandler(Path(cnf.DEFAULT_LOGGING_FILE).parent / "population_errors.txt")
fh.setLevel(logging.CRITICAL)
logger.addHandler(fh)
if cnf.ENV_STATE != "prod":
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

polygon_key = cnf.POLYGON_API_KEY
dl_root_path = cnf.DOWNLOADER_ROOT_PATH
polygon_overview_files_path = cnf.POLYGON_OVERVIEW_FILES_PATH
tickers = cnf.APP_CONFIG.TRACKED_TICKERS
tracked_forms = cnf.APP_CONFIG.TRACKED_FORMS


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

class DilutionDBUpdater:
    def __init__(self, db: DilutionDB):
        self.db = db
        # what to update: cusips, filings, from new filings -> data in database
        # filings: update submissions.zip -> get date of last update for ticker -> get list of filings after that date -> download filings -> write new update date for filings download
            # add a table to keep track which filings have been processed 


        


def get_filing_set(downloader: Downloader, ticker: str, forms: list, after: str, number_of_filings: int = 250):
    # # download the last 2 years of relevant filings
    if after is None:
        after = str((datetime.now() - timedelta(weeks=104)).date())
    for form in forms:
    #     # add check for existing file in pysec_donwloader so i dont download file twice
        downloader.get_filings(ticker, form, after, number_of_filings=100)



# __________experimenting___________
import pandas as pd
import re
from functools import reduce
import numpy as np
from main.data_aggregation.fact_extractor import  _get_fact_data
class ReviewUtility:
    def test_outstanding_shares_from_facts(self, dl_root_path, cik):
        companyfacts_file_path = Path(dl_root_path) / "companyfacts" / ("CIK"+cik+".json")
        with open(companyfacts_file_path, "r") as f:
            companyfacts = json.load(f)
            dfs = []
            # copy of get_outstanding shares function in fact_extractor
            for key, i in {"us-gaap": [
        "Cash",
        'CashAndCashEquivalentsAtCarryingValue',
        "RestrictedCashAndCashEquivalentsAtCarryingValue",
        "RestrictedCash"
        ],
                            "dei": [
        "Cash",
        'CashAndCashEquivalentsAtCarryingValue',
        "RestrictedCashAndCashEquivalentsAtCarryingValue"
        ]}.items():
                if len(i) > 1:
                    for tag in i:
                        facts = _get_fact_data(companyfacts, tag, key)
                        for fact in facts:
                            df = pd.DataFrame(facts[fact])
                            try:
                                df = df.sort_values(by=["val"], ascending=True).drop_duplicates(["end"], keep="last")[["end", "val", "name"]]
                                df = df.rename({"val": fact}, axis=1).drop("name", axis=1)
                            except Exception as e:
                                raise e
                            dfs.append(df)
                elif len(i) == 1:
                    facts = _get_fact_data(companyfacts, i[0], key)
                    for fact in facts:
                        df = pd.DataFrame(facts[fact])
                        try:
                            df = df.sort_values(by=["val"], ascending=True).drop_duplicates(["end"], keep="last")[["end", "val", "name"]]
                        except Exception as e:
                            raise e
                        dfs.append(df)
                elif len(i) == 0:
                    continue 
            os = reduce(
                lambda l, r: pd.merge(l, r, on=["end"], how="outer"),
                dfs,
                )
            # return (os.sort_values(by="end"), os["name"].unique())
            return os.sort_values(by="end")
    
    def test_cash_and_equivalents_from_facts(self, dl_root_path, cik):
        companyfacts_file_path = Path(dl_root_path) / "companyfacts" / ("CIK"+cik+".json")
        with open(companyfacts_file_path, "r") as f:
            companyfacts = json.load(f)
            # net_including_restricted_cash_keys = [
            #     "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
            #     'RestrictedCashAndCashEquivalentsAtCarryingValue'
            #     ]
            # net_excluding_restricted_cash_keys = [
            #     "Cash",
            #     'CashAndCashEquivalentsAtCarryingValue'
            #     ]
            net_cash_keys_all = [
                "Cash",
                'CashAndCashEquivalentsAtCarryingValue',
                "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
                'RestrictedCashAndCashEquivalentsAtCarryingValue'
                ]
            dfs = []
            for key in net_cash_keys_all:
                try:
                    facts = _get_fact_data(companyfacts, key, "us-gaap")
                    df = pd.DataFrame(facts[key])
                    # clean and sort
                    df = df.sort_values(by=["val"], ascending=True).drop_duplicates(["end"], keep="last")[["end", "val", "name"]]
                    # rename val and drop name column
                    df = df.rename({"val": key}, axis=1).drop("name", axis=1)
                    dfs.append(df)
                except KeyError:
                    continue
            # merge all together
            cash = reduce(
                lambda l, r: pd.merge(l, r, on=["end"], how="outer"),
                dfs,
                )
            cash["val"] = cash.loc[:, cash.columns != "end"].agg(lambda x: np.nanmax(x.values), axis=1)
            return cash[["end", "val"]].to_dict("records")
            
if __name__ == "__main__":
    # ru = ReviewUtility()
    # os = ru.test_outstanding_shares_from_facts(cnf.DOWNLOADER_ROOT_PATH, '0000883945')
    # dollars = ru.test_cash_and_equivalents_from_facts(cnf.DOWNLOADER_ROOT_PATH, '0000883945')
    
    
    
    
    db = DilutionDB(cnf.DILUTION_DB_CONNECTION_STRING)
    # for ticker in cnf.APP_CONFIG.TRACKED_TICKERS:
    #     get_filing_set(Downloader(dl_root_path), ticker, cnf.APP_CONFIG.TRACKED_FORMS, "2018-01-01")
    # db._delete_all_tables()
    # db._create_tables()
    # db.create_sics()
    # db.create_form_types()


    # inital_population(db, cnf.DOWNLOADER_ROOT_PATH, cnf.POLYGON_OVERVIEW_FILES_PATH, cnf.POLYGON_API_KEY, cnf.APP_CONFIG.TRACKED_TICKERS)
    # inital_population(db, dl_root_path, polygon_overview_files_path, polygon_key, ["CEI", "USAK", "BBQ"])


    # db.create_tracked_companies()
    # now get filings from submissions.zip
    # populate filing_links

    # then get each companyfact from companyfacts.zip
    # and populate corresponding table

    # then download sec filings (s-3 and related files of that filing)

    #notes:
    # check what is included in the 8-k/6-k download and resolve the issue either 
    # by downloading the full submission or individual files
