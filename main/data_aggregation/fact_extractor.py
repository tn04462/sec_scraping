


'''aggregate following data:

resources: 
https://xbrl.us/data-rule/guid-cashflowspr/#5
https://asc.fasb.org/viewpage

- Outstanding shares [value, instant] us-gaap:CommonStockSharesOutstanding, EntityCommonStockSharesOutstanding ?

- cash and equiv. NET at end of period [value, instant] us-gaap:[
    CashAndCashEquivalentsPeriodIncreaseDecrease,
    CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect,
    CashAndCashEquivalentsPeriodIncreaseDecreaseExcludingExchangeRateEffect,
    CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseExcludingExchangeRateEffect,
    CashPeriodIncreaseDecrease,
    CashPeriodIncreaseDecreaseExcludingExchangeRateEffect
]
capital rais in a period seen on sheet as proceeds from issuance of...
look for us-gaap elements that represent atms, warrants, notes ect.
- s-1 shelves
- s-3 shelves
- warrants - keys: ProceedsFromIssuanceOfWarrants
- notes
- ATM's
- what is considered to be a private placement - keys us-gaap: ProceedsFromIssuanceOfPrivatePlacement
- issuance of common stock [value, from, to] us-gaap:ProceedsFromIssuanceOfCommonStock
 CommonStockSharesIssued
- 

other terms to check and maybe implement: 
    re.compile("(.*)proceedsfromissu(.*)", re.I) -> proceeds from issuance of all kind of stock, warrant, preferred series ect

other notes relating to filings:
    stock splits: 8-k, 10-q, 10-k
    
'''
import re
import pandas as pd
import logging
from functools import reduce
import numpy as np
logger = logging.getLogger(__package__)


def _clean_outstanding_shares(facts: dict):
    try:
        df = pd.DataFrame(facts["CommonStockSharesOutstanding"])
    except KeyError:
        df = pd.DataFrame(facts["EntityCommonStockSharesOutstanding"])
    cleaned = df.drop_duplicates(["end", "val"])
    return cleaned.to_dict("records")

def get_outstanding_shares(companyfacts):
    dfs = []
    # first get all possible facts for outstanding shares
    for key, i in {"us-gaap": ["CommonStockSharesOutstanding", "EntityCommonStockSharesOutstanding"],
                    "dei": ["CommonStockSharesOutstanding", "EntityCommonStockSharesOutstanding"]}.items():
        if len(i) > 1:
            for tag in i:
                facts = _get_fact_data(companyfacts, tag, key)
                for fact in facts:
                    df = pd.DataFrame(facts[fact])
                    try:
                        df = df.sort_values(by=["val"], ascending=True).drop_duplicates(["end"], keep="last")[["end", "val", "name"]]
                    except Exception as e:
                        raise e
                    dfs.append(df)
        elif len(i) == 1:
            facts = _get_fact_data(companyfacts, i[0], key)
            try:
                df = pd.DataFrame(facts[key])
                try:
                    df = df.sort_values(by=["val"], ascending=True).drop_duplicates(["end"], keep="last")[["end", "val", "name"]]
                except Exception as e:
                    raise e
                dfs.append(df)
            except KeyError:
                pass
        elif len(i) == 0:
            continue
    if dfs == []:
        return None
    os = reduce(
        lambda l, r: pd.merge(l, r, on=["end", "val", "name"], how="outer"),
        dfs,
        )
    logger.debug(f"outstanding shares according to get_outstanding_shares: {os}")
    return os.to_dict("records")
    

def get_cash_and_equivalents(companyfacts):
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
    if dfs == []:
        return None
    cash = reduce(
        lambda l, r: pd.merge(l, r, on=["end"], how="outer"),
        dfs,
        )
    cash["val"] = cash.loc[:, cash.columns != "end"].agg(lambda x: np.nanmax(x.values), axis=1)
    return cash[["end", "val"]].to_dict("records")

def get_cash_financing(companyfacts):
    cash_financing = _get_fact_data(companyfacts, re.compile("netcash(.*)financ(.*)",  re.I), "us-gaap")
    if cash_financing == {}:
        raise(ValueError(f"couldnt get cash from financing for company, manually find the right name or taxonomy: {companyfacts['facts'].keys()}"))
    else:
        try:
            cash_financing = cash_financing["NetCashProvidedByUsedInFinancingActivities"]
            df = pd.DataFrame(cash_financing)
            # if there are two entries left it is probably from a merger/aquisition 
            # so we take the newer entry
            df.sort_values(by=["fy"], axis=0).drop_duplicates(["start", "end"], keep="last")
            logger.debug(f"cash_financing: {df}")
            return df.to_dict("records")
        except KeyError as e:
            raise e
        

def get_cash_investing(companyfacts):
    cash_investing = _get_fact_data(companyfacts, re.compile("netcash(.*)invest(.*)", re.I), "us-gaap")
    if cash_investing == {}:
        raise(ValueError(f"couldnt get cash from investing for company, manually find the right name or taxonomy: {companyfacts['facts'].keys()}"))
    else:
        try:
            cash_investing = cash_investing["NetCashProvidedByUsedInInvestingActivities"]
            df = pd.DataFrame(cash_investing)
            # if there are two entries left it is probably from a merger/aquisition 
            # so we take the newer entry
            df = df.sort_values(by=["fy"], axis=0).drop_duplicates(["start", "end"], keep="last")
            logger.debug(f"cash_investing: {df}")
            return df.to_dict("records")
        except KeyError as e:
            raise e
        

def get_cash_operating(companyfacts):
    cash_operations = _get_fact_data(companyfacts, re.compile("netcash(.*)operat(.*)", re.I), "us-gaap")
    if cash_operations == {}:
        raise(ValueError(f"couldnt get cash from operations for company, manually find the right name or taxonomy: {companyfacts['facts'].keys()}"))
    else:
        try:
            cash_operations = cash_operations["NetCashProvidedByUsedInOperatingActivities"]
            df = pd.DataFrame(cash_operations)
            # if there are two entries left it is probably from a merger/aquisition 
            # so we take the newer entry
            df = df.sort_values(by=["fy"], axis=0).drop_duplicates(["start", "end"], keep="last")
            logger.debug(f"cash_operations: {df}")
            return df.to_dict("records")
        except KeyError as e:
            raise e
       


def _get_fact_data(companyfacts, name, taxonomy):
    facts = {}
    data_points = companyfacts["facts"][taxonomy]
    if isinstance(name, re.Pattern):
        for d in data_points:
            fname = re.search(name, d)
            if fname:
                fstring = fname.string
                for unit in companyfacts["facts"][taxonomy][fstring]["units"]:
                    for single_fact in companyfacts["facts"][taxonomy][fstring]["units"][unit]:
                        single_fact["taxonomy"] = taxonomy
                        single_fact["unit"] = unit
                        single_fact["name"] = fstring
                        if fstring in facts.keys():
                            facts[fstring].append(single_fact)
                        else:
                            facts[fstring] = [single_fact]
    else:
        for d in data_points:
            fname = re.search(re.compile("^("+name+")$", re.I), d)
            if fname:
                fstring = fname.string
                for unit in companyfacts["facts"][taxonomy][fstring]["units"]:
                    for single_fact in companyfacts["facts"][taxonomy][fstring]["units"][unit]:
                        single_fact["taxonomy"] = taxonomy
                        single_fact["unit"] = unit
                        single_fact["name"] = fstring
                        if fstring in facts.keys():
                            facts[fstring].append(single_fact)
                        else:
                            facts[fstring] = [single_fact]
    return facts




if __name__ == "__main__":
        
    import json
    import re
    from pathlib import Path

    # dl = Downloader(r"C:\Users\Olivi\Testing\sec_scraping_testing\pysec_downloader\companyfacts", user_agent="john smith js@test.com")
    # print(len(dl._lookuptable_ticker_cik.keys()))
    # symb = ["PHUN", "GNUS", "IMPP"]
    # for s in symb:
    #     j = dl.get_xbrl_companyfacts(s)
    #     with open((dl.root_path / (s +".json")), "w") as f:
    #         json.dump(j, f)

    with open(Path(r"C:\Users\Olivi\Testing\sec_scraping\resources\test_set\companyfacts") / ("CIK0001309082" + ".json"), "r") as f:
        j = json.load(f)

        for search_term in [
            re.compile("(.*)sharesoutstanding(.*)", re.I)]:
            facts = _get_fact_data(j, search_term, "us-gaap")
            for key in facts.keys():
                df = pd.DataFrame(facts[key]).sort_values(by=["fy"]).drop_duplicates(["end", "val"])
                print(f"{key}: {df}")
        # facts1 = _get_fact_data(j, re.compile("(.*)outstanding(.*)", re.I), "us-gaap")
        # facts2 = _get_fact_data(j, re.compile("(.*)outstanding(.*)", re.I), "dei")
        # facts3 = _get_fact_data(j, "PreferredStockValueOutstanding", "us-gaap")
        # facts4 = _get_fact_data(j, "WeightedAverageNumberOfDilutedSharesOutstanding", "us-gaap")
        # keys = _get_fact_data(j, re.compile("(.*)share(.*)", re.I), "us-gaap")
        # for key in keys.keys():
        #     print(key, "\n")
        # # facts3 = _get_fact_data(j, re.compile("(.*)outstanding(.*)"), "cei")
        # df1 = pd.DataFrame(facts3["PreferredStockValueOutstanding"]).sort_values(by=["fy"], axis=0).drop_duplicates(["end"], keep="last")
        # df2 = pd.DataFrame(facts4["WeightedAverageNumberOfDilutedSharesOutstanding"]).sort_values(by=["start"], axis=0).drop_duplicates(["end"], keep="last")

        # print(df1, df2)
            
        # _clean_outstanding_shares(facts)
        # facts = get_outstanding_shares(j)

    # for s in symb:
    #         # j = dl.get_xbrl_companyfacts(s)
    #         # with open((dl.root_path / (s +".json")), "w") as f:
    #         #     json.dump(j, f)
    #         with open(Path(r"C:\Users\Olivi\Testing\sec_scraping_testing\pysec_downloader\companyfacts") / (s + ".json"), "r") as f:
    #             j = json.load(f)
    #             matches = []
    #             for each in j["facts"].keys():
    #                 for possible in j["facts"][each]:
                        
    #                     if re.search(re.compile("ProceedsFromIssuance(.*)", re.I), possible):
    #                         matches.append(possible)
    #             print([j["facts"]["us-gaap"][p] for p in matches])