


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

Unit key I want is USD so a fact i want is accessed by using json["facts"][taxonomy][fact_name][unit]
for issuance of inital public offering take the filing date as the instant of the value
for issuance of 
'''
import re
import pandas as pd


def _clean_outstanding_shares(facts: dict):
    df = pd.DataFrame(facts["CommonStockSharesOutstanding"])
    cleaned = df.drop_duplicates(["end", "val"])
    return cleaned.to_dict("records")

def get_outstanding_shares(companyfacts):
    outstanding_shares = _get_fact_data(companyfacts, "CommonStockSharesOutstanding", "us-gaap")
    if outstanding_shares == {}:
        outstanding_shares = _get_fact_data(companyfacts, "EntityCommonStockSharesOutstanding", "us-gaap")
        if outstanding_shares == {}:
            raise ValueError(f"couldnt get outstanding shares for company, manually find the right name or taxonomy: {companyfacts_file_path}")
    outstanding_shares = _clean_outstanding_shares(outstanding_shares)
    return outstanding_shares

def get_cash_and_equivalents(companyfacts):
    cash = _get_fact_data(companyfacts, re.compile("Cash(.*)"), "us-gaap")
    # cash = _get_fact_data(companyfacts, re.compile("^Cash(?!.*Restrict)(.*)eriodIncreaseDecrease$"), "us-gaap")
    keys = cash.keys()
    if ("CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"
        and "RestrictedCashNoncurrent") in  keys:
        c = pd.DataFrame(cash["CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"]).drop_duplicates(["end", "val"])
        r = pd.DataFrame(cash["RestrictedCashNoncurrent"]).drop_duplicates(["end", "val"])
        df = c.merge(r[["end", "val"]], on="end")
        df["val"] = df["val_x"] - df["val_y"]
        return df[["end", "val", "val_x"]].rename(
            {"val": "val_excluding_restrictednoncurrent", "val_x": "val"}, axis=1).to_dict("records")
    else:
        raise AttributeError(
            (f"unhandled case of cash and equivalents: \n"
             f"facts (keys) found: {keys}"))
    
    
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

    with open(Path(r"C:\Users\Olivi\Testing\sec_scraping\resources\test_set\bulk\companyfacts") / ("CIK0001718405" + ".json"), "r") as f:
        j = json.load(f)
        # facts = _get_fact_data(j, "CommonStockSharesOutstanding", "us-gaap")
        # _clean_outstanding_shares(facts)
        facts = get_cash_and_equivalents(j)

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