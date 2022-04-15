


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
logger = logging.getLogger(__package__)


def _clean_outstanding_shares(facts: dict):
    try:
        df = pd.DataFrame(facts["CommonStockSharesOutstanding"])
    except KeyError:
        df = pd.DataFrame(facts["EntityCommonStockSharesOutstanding"])
    cleaned = df.drop_duplicates(["end", "val"])
    return cleaned.to_dict("records")

def get_outstanding_shares(companyfacts):
    outstanding_shares = _get_fact_data(companyfacts, "CommonStockSharesOutstanding", "us-gaap")
    try:
        df = pd.DataFrame(outstanding_shares["CommonStockSharesOutstanding"])
    except KeyError:
        outstanding_shares = _get_fact_data(companyfacts, "EntityCommonStockSharesOutstanding", "us-gaap")
        if outstanding_shares == {}:
            raise ValueError(f"couldnt get outstanding shares for company, manually find the right name or taxonomy")
    logger.debug(f"outstanding shares according to CommonStockSharesOutstanding: {df}")
    outstanding_shares = _clean_outstanding_shares(outstanding_shares)
    return outstanding_shares

def get_cash_and_equivalents(companyfacts):
    cash = _get_fact_data(companyfacts, re.compile("Cash(.*)"), "us-gaap")
    # cash = _get_fact_data(companyfacts, re.compile("^Cash(?!.*Restrict)(.*)eriodIncreaseDecrease$"), "us-gaap")
    keys = cash.keys()
    logger.debug(keys)
    net_including_restricted_cash_keys = [
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"
        ]
    net_excluding_restricted_cash_keys = [
        "Cash",
        'CashAndCashEquivalentsAtCarryingValue'
        ]

    restricted_cash_keys = [
        "RestrictedCashNoncurrent",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        'RestrictedCashAndCashEquivalentsAtCarryingValue',
        "RestrictedCashAndCashEquivalents"]
    for net_not_restricted_cash_key in net_excluding_restricted_cash_keys:
        if net_not_restricted_cash_key in keys:
            return pd.DataFrame(cash[net_not_restricted_cash_key]).drop_duplicates(["end", "val"]).to_dict("records")
    for net_restricted_cash_key in net_including_restricted_cash_keys:
        if  net_restricted_cash_key in keys:
            for restricted_cash_key in restricted_cash_keys:
                if restricted_cash_key in keys:
                    try:
                        c = pd.DataFrame(cash[net_restricted_cash_key]).drop_duplicates(["end", "val"])
                        r = pd.DataFrame(cash[restricted_cash_key]).drop_duplicates(["end", "val"])
                        df = c.merge(r[["end", "val"]], on="end")
                        df["val"] = df["val_x"] - df["val_y"]
                        logger.debug(f"net_cash_and_equivalents used following keys to get data: {net_restricted_cash_key, restricted_cash_key}")
                        return df[["end", "val", "val_x"]].rename(
                            {"val": "val_excluding_restrictednoncurrent", "val_x": "val"}, axis=1).to_dict("records")
                    except KeyError as  e:
                        logger.debug(f"unhandled parsing of cash and equivalents dataframe: c.columns: {c.columns} \n r.columns: {r.columns} \n df.columns: {df.columns}")
                        raise e
            raise AttributeError(f"unhandled restricted cash key: {keys}")
        else:
            raise AttributeError(f"unhandled cash_key or cash_key not present: {keys}")
    else:
        raise AttributeError(
            (f"unhandled case of cash and equivalents: \n"
             f"facts (keys) found: {keys}"))

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
       


def _get_fact_data(companyfacts, name, taxonomy, unit="USD"):
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
            fname = re.search(re.compile("(.*)("+name+")(.*)", re.I), d)
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