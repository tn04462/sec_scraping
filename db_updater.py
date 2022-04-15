from main.data_aggregation.bulk_files import update_bulk_files

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
fh = logging.FileHandler(r"E:\sec_scraping\resources\datasets\population_errors.txt")
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

def force_cashBurn_update(db: DilutionDB):
    companies = db.read_all_companies()
    for company in companies:
        id = company["id"]
        try:
            with db.conn() as connection:
                with connection.transaction():
                    db.init_cash_burn_rate(connection, id)
                    db.init_cash_burn_summary(connection, id)
        except KeyError as e:
            logger.info((e, company))
    

def inital_population(db: DilutionDB, dl_root_path: str, polygon_overview_files_path: str, polygon_api_key: str, tickers: list):
    polygon_client = PolygonClient(polygon_api_key)
    dl = Downloader(dl_root_path)
    if not Path(polygon_overview_files_path).exists():
        Path(polygon_overview_files_path).mkdir(parents=True)
        logger.debug(
            f"created overview_files_path and parent folders: {polygon_overview_files_path}")
    for ticker in tickers:
        logger.info(f"currently working on: {ticker}")
        # get basic info and create company
        try:
            ov = polygon_client.get_overview_single_ticker(ticker)
        except HTTPError as e:
            logger.critical((e, ticker, "couldnt get overview file"))
            logger.info("couldnt get overview file")
            continue
        with open(Path(polygon_overview_files_path) / (ov["cik"] + ".json"), "w+") as f:
            json.dump(ov, f)
        logger.debug(f"overview_data: {ov}")
        # check that we have a sic otherwise assign  9999 --> nonclassifable
        try:
            ov["sic_code"]
        except KeyError:
            ov["sic_code"] = "9999"
            ov["sic_description"] = "Nonclassifiable"
        
        # load the xbrl facts 
        companyfacts_file_path = Path(dl_root_path) / "companyfacts" / ("CIK"+ov["cik"]+".json")
        recent_submissions_file_path = Path(dl_root_path) / "submissions" / ("CIK"+ov["cik"]+".json")
        try:
            with open(companyfacts_file_path, "r") as f:
                companyfacts = json.load(f)
                
                # query for wanted xbrl facts and write to db
                try:
                    outstanding_shares = get_outstanding_shares(companyfacts)
                    if outstanding_shares is None:
                        logger.critical(("couldnt get outstanding_shares extracted", ticker))
                        continue
                except ValueError as e:
                    logger.critical((e, ticker))
                    continue
                except KeyError as e:
                    logger.critical((e, ticker))
                    continue
                logger.debug(f"outstanding_shares: {outstanding_shares}")
                # start db transaction to ensure only complete companies get added
                id = None
                with db.conn() as connection:
                    try:
                        id = db.create_company(
                            connection,
                            ov["cik"],
                            ov["sic_code"],
                            ticker, ov["name"],
                            ov["description"],
                            ov["sic_description"])
                        if not id:
                            raise ValueError("couldnt get the company id from create_company")
                        for fact in outstanding_shares:
                            db.create_outstanding_shares(
                                connection,
                                id, fact["end"], fact["val"])
                        try:
                            net_cash = get_cash_and_equivalents(companyfacts)
                            if net_cash is None:
                                logger.critical(("couldnt get netcash extracted", ticker))
                                continue
                        except ValueError as e:
                            logger.critical((e, ticker))
                            raise e
                        except KeyError as e:
                            logger.critical((e, ticker))
                            raise e
                        logger.debug(f"net_cash: {net_cash}")
                        for fact in net_cash:
                            db.create_net_cash_and_equivalents(
                                connection,
                                id, fact["end"], fact["val"])
                        # get the cash flow, partially tested
                        try:
                            cash_financing = get_cash_financing(companyfacts)
                            for fact in cash_financing:
                                db.create_cash_financing(
                                    connection,
                                    id, fact["start"], fact["end"], fact["val"]
                                )
                            cash_operating = get_cash_operating(companyfacts)
                            for fact in cash_operating:
                                db.create_cash_operating(
                                    connection,
                                    id, fact["start"], fact["end"], fact["val"]
                                )
                            cash_investing = get_cash_investing(companyfacts)
                            for fact in cash_investing:
                                db.create_cash_investing(
                                    connection,
                                    id, fact["start"], fact["end"], fact["val"]
                                )
                        except ValueError as e:
                            logger.critical((e, ticker))
                            logger.debug((e, ticker))
                            raise e 
                        # calculate cash burn per day
                    except Exception as e:
                        logger.critical(("Phase1", e, ticker))
                        connection.rollback()
                        continue
                    else:
                        connection.commit()
                    
                    
                with db.conn() as connection:
                    try:
                        db.init_cash_burn_rate(connection, id)
                    except KeyError as e:
                        logger.critical(("Phase2.1", e, ticker))
                        logger.debug((e, ticker))
                        connection.rollback()
                        raise e
                    else:
                        connection.commit()
                    try:
                        db.init_cash_burn_summary(connection, id)
                    except KeyError as e:
                        logger.critical(("Phase2.2", e, ticker))
                        logger.debug((e, ticker))
                        connection.rollback()
                        raise e
                    else:
                        connection.commit()
                    
                with db.conn() as connection1:      
                    # populate filing_links table from submissions.zip
                    try:
                        with open(recent_submissions_file_path, "r") as f:
                            submissions = db.util.format_submissions_json_for_db(
                                EDGAR_BASE_ARCHIVE_URL,
                                ov["cik"],
                                json.load(f))
                            for s in submissions:
                                with db.conn() as connection2:
                                    try:
                                        db.create_filing_link(
                                            connection2,
                                            id,
                                            s["filing_html"],
                                            s["form"],
                                            s["filingDate"],
                                            s["primaryDocDescription"],
                                            s["fileNumber"])
                                    except Exception as e:
                                        logger.debug((e, s))
                                        connection2.rollback()
                                    else:
                                        connection2.commit()
                    except Exception as e:
                        logger.critical(("Phase3", e, ticker))
                        logger.debug((e, ticker))
                        connection1.rollback()
                        raise e
                    else:
                        connection1.commit()
        except FileNotFoundError as e:
            logger.critical((e,"This is mostlikely a fund or trust and not a company.", ticker))
            continue
        


def get_filing_set(downloader: Downloader, ticker: str, forms: list, after: str):
    # # download the last 2 years of relevant filings
    if after is None:
        after = str((datetime.now() - timedelta(weeks=104)).date())
    for form in forms:
    #     # add check for existing file in pysec_donwloader so i dont download file twice
        downloader.get_filings(ticker, form, after, number_of_filings=100)


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
    for ticker in cnf.APP_CONFIG.TRACKED_TICKERS[1:]:
        get_filing_set(Downloader(dl_root_path), ticker, ["8-K"], "2020-01-01")
    # db._delete_all_tables()
    # db._create_tables()
    # db.create_sics()
    # db.create_form_types()
    
    # force_cashBurn_update(db)dl = Downloader(dl_root_path)
    # inital_population(db, dl_root_path, polygon_overview_files_path, polygon_key, cnf.APP_CONFIG.TRACKED_TICKERS[31:])
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
